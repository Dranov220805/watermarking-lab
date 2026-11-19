"""Self-contained unittest suite for the 6-layer DDD backend (no httpx required)."""
import asyncio
import json
import tempfile
import unittest

import cv2
import numpy as np

import server
from src.application.watermark import ImageService, WatermarkService
from src.application_contracts.watermark.dtos import (
    AttackInputDto,
    EmbedInputDto,
    ExtractInputDto,
    LogoPreviewInputDto,
    LogoSpecInputDto,
)
from src.domain_shared.enums import ErrorCode
from src.domain_shared.errors import BusinessException
from src.infrastructure.storage import LocalImageRepository


def _make_cover_png(width: int = 560, height: int = 560) -> bytes:
    rng = np.random.default_rng(42)
    img = rng.integers(30, 225, size=(height, width, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


class BackendDDDTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = LocalImageRepository(store_dir=self._tmp.name)
        self.image_service = ImageService(image_repository=self.repo)
        self.wm_service = WatermarkService(
            image_repository=self.repo,
            image_service=self.image_service,
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_health_and_routes_registered(self) -> None:
        health = asyncio.run(self.wm_service.get_health_async())
        self.assertTrue(health.ok)
        paths = set(server.app.openapi()["paths"].keys())
        expected = {
            "/api/v1/health",
            "/api/v1/images/upload",
            "/api/v1/images/{image_id}/preview",
            "/api/v1/images/{image_id}/download",
            "/api/v1/watermark/logo/preview",
            "/api/v1/watermark/embed",
            "/api/v1/watermark/attack",
            "/api/v1/watermark/extract",
        }
        self.assertTrue(expected.issubset(paths), f"Missing routes: {expected - paths}")

    def test_upload_embed_attack_extract_roundtrip(self) -> None:
        uploaded = asyncio.run(self.image_service.upload_async(_make_cover_png(), "cover.png"))
        self.assertEqual(uploaded.width, 560)
        self.assertEqual(uploaded.height, 560)
        self.assertGreaterEqual(uploaded.copies, 1.0)

        emb = asyncio.run(
            self.wm_service.embed_async(
                EmbedInputDto(
                    image_id=uploaded.id,
                    key="secret-k1",
                    alpha=25.0,
                    method="dct",
                    logo=LogoSpecInputDto(source="standard"),
                )
            )
        )
        self.assertIsNotNone(emb.psnr)
        self.assertGreater(emb.psnr or 0.0, 30.0)

        atk = asyncio.run(
            self.wm_service.attack_async(
                AttackInputDto(image_id=emb.id, jpeg_quality=75, noise_sigma=1.0)
            )
        )
        self.assertEqual(atk.format, "JPEG")
        self.assertIn("JPEG Q=75", atk.desc)

        ext = asyncio.run(
            self.wm_service.extract_async(
                ExtractInputDto(
                    image_id=atk.id,
                    key="secret-k1",
                    alpha=25.0,
                    method="dct",
                    mode="search",
                    null_trials=10,
                    logo=LogoSpecInputDto(source="standard"),
                )
            )
        )
        self.assertTrue(ext.detected)
        self.assertLess(ext.ber or 1.0, 0.05)
        self.assertTrue(ext.logo_png.startswith("data:image/png;base64,"))

        aligned = asyncio.run(
            self.wm_service.extract_async(
                ExtractInputDto(
                    image_id=emb.id,
                    key="secret-k1",
                    alpha=25.0,
                    method="dct",
                    mode="aligned",
                    logo=LogoSpecInputDto(source="standard"),
                )
            )
        )
        self.assertGreater((aligned.structure or 0) - (aligned.structure_baseline or 0), 0.12)

    def test_logo_preview_and_business_exceptions(self) -> None:
        preview = asyncio.run(
            self.wm_service.build_logo_preview_async(
                LogoPreviewInputDto(logo=LogoSpecInputDto(source="text", text="SEC"), scale=2)
            )
        )
        self.assertTrue(preview.png_bytes.startswith(b"\x89PNG"))
        self.assertGreater(preview.ink_pixels, 50)

        with self.assertRaises(BusinessException) as ctx:
            asyncio.run(self.image_service.upload_async(b"not-an-image", "bad.txt"))
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_IMAGE)

        with self.assertRaises(BusinessException) as ctx2:
            self.image_service.get_entity_or_throw("nonexistent-id")
        self.assertEqual(ctx2.exception.code, ErrorCode.IMAGE_NOT_FOUND)

    def test_response_envelope_shape(self) -> None:
        from src.http_api.interceptors import success_response

        resp = success_response({"ok": True})
        body = json.loads(resp.body)
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["statusCode"], 200)
        self.assertEqual(body["systemName"], "WM.WatermarkService")
        self.assertIsNone(body["error"])
        self.assertEqual(body["data"], {"ok": True})

    def test_settings_load_from_env_file(self) -> None:
        import os
        from pathlib import Path
        from unittest.mock import patch
        from src.infrastructure.config import load_settings

        with tempfile.TemporaryDirectory() as td:
            env_dir = Path(td)
            (env_dir / ".env").write_text(
                "APP_PORT=9100\nSYSTEM_NAME=Custom.WM\nCORS_ORIGINS=http://a.test,http://b.test\nMAX_UPLOAD_MB=50\n",
                encoding="utf-8",
            )
            (env_dir / ".env.local").write_text("APP_PORT=9200\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                s = load_settings(env_dir=env_dir)
                self.assertEqual(s.app_port, 9200)
                self.assertEqual(s.system_name, "Custom.WM")
                self.assertEqual(s.cors_origins, ("http://a.test", "http://b.test"))
                self.assertEqual(s.max_upload_bytes, 50 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
