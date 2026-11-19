"""WatermarkService — application service for logo preview, embed, attack, and extract."""
import base64
import time
from typing import Optional

import cv2
import numpy as np

from src.application_contracts.watermark.dtos import (
    AttackInputDto,
    AttackOutputDto,
    EmbedInputDto,
    EmbedOutputDto,
    ExtractInputDto,
    ExtractOutputDto,
    HealthOutputDto,
    LogoPreviewInputDto,
    LogoPreviewOutputDto,
    LogoSpecInputDto,
)
from src.domain.repositories.image_repository import IImageRepository
from src.domain.services import dct_engine, logo_builder
from src.domain_shared.consts import (
    MAX_ALPHA,
    MAX_NULL_TRIALS,
    MAX_SSIM_PIXELS,
    MIN_ALPHA,
    MIN_BLOCKS,
    MIN_LOGO_INK_PIXELS,
)
from src.domain_shared.enums import ExtractMode, WatermarkMethod
from src.domain_shared.errors import BusinessException
from .image_service import ImageService


def _safe_float(val: Optional[float]) -> Optional[float]:
    if val is None or not np.isfinite(val):
        return None
    return float(val)


class WatermarkService:
    def __init__(
        self,
        image_repository: IImageRepository,
        image_service: ImageService,
        max_null_trials: int = MAX_NULL_TRIALS,
    ) -> None:
        self._image_repository = image_repository
        self._image_service = image_service
        self._max_null_trials = max_null_trials

    @staticmethod
    def _validate_common(key: str, alpha: float, method: str) -> None:
        if not key.strip():
            raise BusinessException.invalid_secret_key()
        if method not in (WatermarkMethod.DCT.value, WatermarkMethod.LSB.value):
            raise BusinessException.invalid_method()
        if not MIN_ALPHA <= alpha <= MAX_ALPHA:
            raise BusinessException.invalid_alpha(MIN_ALPHA, MAX_ALPHA)

    @staticmethod
    def _build_logo(spec: LogoSpecInputDto) -> np.ndarray:
        try:
            return logo_builder.build(
                source=spec.source,
                file_bytes=spec.file_bytes,
                text=spec.text,
                threshold=spec.threshold,
                invert=spec.invert,
            )
        except Exception as exc:  # noqa: BLE001
            raise BusinessException.logo_error(str(exc)) from exc

    async def get_health_async(self) -> HealthOutputDto:
        return HealthOutputDto(ok=True, cv2=cv2.__version__, numpy=np.__version__)

    async def build_logo_preview_async(self, input_dto: LogoPreviewInputDto) -> LogoPreviewOutputDto:
        bits = self._build_logo(input_dto.logo)
        clamped_scale = max(1, min(8, input_dto.scale))
        png_bytes = logo_builder.to_png(bits, clamped_scale)
        return LogoPreviewOutputDto(png_bytes=png_bytes, ink_pixels=int(bits.sum()))

    async def embed_async(self, input_dto: EmbedInputDto) -> EmbedOutputDto:
        self._validate_common(input_dto.key, input_dto.alpha, input_dto.method)
        entity = self._image_service.get_entity_or_throw(input_dto.image_id)
        if entity.blocks < MIN_BLOCKS:
            raise BusinessException.image_too_small(entity.blocks, MIN_BLOCKS)

        bits = self._build_logo(input_dto.logo)
        if int(bits.sum()) < MIN_LOGO_INK_PIXELS:
            raise BusinessException.empty_logo()

        img = self._image_service.load_bgr_image(entity)
        started = time.time()
        embed_fn = (
            dct_engine.embed_dct
            if input_dto.method == WatermarkMethod.DCT.value
            else dct_engine.embed_lsb
        )
        out = embed_fn(img, bits, input_dto.key, input_dto.alpha)
        psnr_val = dct_engine.psnr(img, out)
        ssim_val = (
            dct_engine.ssim_y(img, out)
            if img.shape[0] * img.shape[1] <= MAX_SSIM_PIXELS
            else None
        )
        saved = self._image_repository.save(
            data=dct_engine.encode_png(out),
            ext="png",
            name=f"{entity.base_name}_watermarked.png",
            width=int(out.shape[1]),
            height=int(out.shape[0]),
            fmt="PNG",
        )
        return EmbedOutputDto(
            **self._image_service.to_output_dto(saved).model_dump(),
            psnr=_safe_float(psnr_val),
            ssim=_safe_float(ssim_val),
            seconds=round(time.time() - started, 2),
        )

    async def attack_async(self, input_dto: AttackInputDto) -> AttackOutputDto:
        entity = self._image_service.get_entity_or_throw(input_dto.image_id)
        img = self._image_service.load_bgr_image(entity)
        parts: list[str] = []

        crop_vals = (input_dto.crop_x, input_dto.crop_y, input_dto.crop_w, input_dto.crop_h)
        if None not in crop_vals:
            cx, cy, cw, ch = (
                int(input_dto.crop_x),  # type: ignore[arg-type]
                int(input_dto.crop_y),  # type: ignore[arg-type]
                int(input_dto.crop_w),  # type: ignore[arg-type]
                int(input_dto.crop_h),  # type: ignore[arg-type]
            )
            h, w = img.shape[:2]
            if cx < 0 or cy < 0 or cw < 8 or ch < 8 or cx + cw > w or cy + ch > h:
                raise BusinessException.invalid_crop(w, h)
            img = dct_engine.attack_crop(img, cy, cx, ch, cw)
            parts.append(f"crop {cw}x{ch} @({cx},{cy})")

        if input_dto.noise_sigma > 0:
            img = dct_engine.attack_noise(
                img, input_dto.noise_sigma, seed=int(time.time()) & 0xFFFF
            )
            parts.append(f"noise sigma={input_dto.noise_sigma:g}")

        base = entity.base_name
        if input_dto.jpeg_quality:
            if not 1 <= input_dto.jpeg_quality <= 100:
                raise BusinessException.invalid_jpeg_quality()
            jpg_bytes = dct_engine.encode_jpeg(img, quality=input_dto.jpeg_quality)
            parts.append(f"JPEG Q={input_dto.jpeg_quality}")
            saved = self._image_repository.save(
                data=jpg_bytes,
                ext="jpg",
                name=f"{base}_attacked.jpg",
                width=int(img.shape[1]),
                height=int(img.shape[0]),
                fmt="JPEG",
            )
        else:
            saved = self._image_repository.save(
                data=dct_engine.encode_png(img),
                ext="png",
                name=f"{base}_attacked.png",
                width=int(img.shape[1]),
                height=int(img.shape[0]),
                fmt="PNG",
            )

        return AttackOutputDto(
            **self._image_service.to_output_dto(saved).model_dump(),
            desc=" -> ".join(parts) or "no attack",
        )

    async def extract_async(self, input_dto: ExtractInputDto) -> ExtractOutputDto:
        self._validate_common(input_dto.key, input_dto.alpha, input_dto.method)
        if input_dto.mode not in (ExtractMode.SEARCH.value, ExtractMode.ALIGNED.value):
            raise BusinessException.invalid_mode()

        entity = self._image_service.get_entity_or_throw(input_dto.image_id)
        if entity.blocks < 1:
            raise BusinessException.image_has_no_blocks()

        img = self._image_service.load_bgr_image(entity)
        started = time.time()

        extra: dict = {}
        if input_dto.mode == ExtractMode.ALIGNED.value:
            res = dct_engine.extract_aligned(img, input_dto.key, input_dto.method, input_dto.alpha)
        else:
            ref = self._build_logo(input_dto.logo)
            trials = max(0, min(self._max_null_trials, input_dto.null_trials))
            res = dct_engine.extract(
                img, ref, input_dto.key, input_dto.method, input_dto.alpha, null_trials=trials
            )
            extra.update(
                nc=_safe_float(dct_engine.nc(ref, res["logo"])),
                ber=_safe_float(dct_engine.ber(ref, res["logo"])),
                score=_safe_float(res["score"]),
                threshold=_safe_float(res.get("threshold")),
                null_mean=_safe_float(res.get("null_mean")),
                null_max=_safe_float(res.get("null_max")),
                detected=res.get("detected"),
                offset=list(res["offset"]),
                phase=list(res["shift"]),
            )

        logo_b64 = base64.b64encode(logo_builder.to_png(res["logo"], 4)).decode()
        return ExtractOutputDto(
            mode=input_dto.mode,
            blocks=entity.blocks,
            copies=entity.copies,
            structure=_safe_float(res["structure"]),
            structure_baseline=_safe_float(res["structure_baseline"]),
            logo_png=f"data:image/png;base64,{logo_b64}",
            seconds=round(time.time() - started, 2),
            **extra,
        )
