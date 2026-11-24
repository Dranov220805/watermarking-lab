"""End-to-end API test: 35 checks against the real FastAPI backend.

Usage:
    python test_api.py              # auto-generates 3000x2000 test covers + logo in a temp folder
    python test_api.py <cover_dir>  # uses existing cover.png/.jpg/.webp/.bmp + mylogo.png
"""
import json
import os
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid

import cv2
import numpy as np
from PIL import Image

import logos
import server
import wm


class _SimpleResponse:
    def __init__(self, status_code: int, content: bytes, headers: dict[str, str]):
        self.status_code = status_code
        self.content = content
        self.headers = {k.lower(): v for k, v in headers.items()}

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.content.decode("utf-8"))


class _LiveHttpClient:
    """Fallback HTTP client (no httpx required) backed by an in-process uvicorn server."""

    def __init__(self, app):
        import uvicorn

        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()

        self._base = f"http://127.0.0.1:{port}"
        self._config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
        self._server = uvicorn.Server(self._config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        for _ in range(60):
            try:
                urllib.request.urlopen(f"{self._base}/api/health", timeout=1).close()
                break
            except Exception:
                time.sleep(0.1)
        else:
            raise RuntimeError("Local test server failed to start")

    def close(self):
        self._server.should_exit = True
        self._thread.join(timeout=3)

    def get(self, path: str) -> _SimpleResponse:
        req = urllib.request.Request(f"{self._base}{path}", method="GET")
        return self._send(req)

    def post(self, path: str, data=None, files=None) -> _SimpleResponse:
        boundary = f"----wmtest{uuid.uuid4().hex}"
        chunks: list[bytes] = []
        if data:
            for k, v in data.items():
                if v is None:
                    continue
                val = "true" if v is True else "false" if v is False else str(v)
                chunks.append(
                    f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{val}\r\n".encode()
                )
        if files:
            for k, spec in files.items():
                fname, fobj = spec[0], spec[1]
                raw = fobj.read() if hasattr(fobj, "read") else bytes(fobj)
                chunks.append(
                    f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{fname}\"\r\n"
                    f"Content-Type: application/octet-stream\r\n\r\n".encode()
                )
                chunks.append(raw)
                chunks.append(b"\r\n")
        chunks.append(f"--{boundary}--\r\n".encode())
        body = b"".join(chunks)
        req = urllib.request.Request(
            f"{self._base}{path}",
            data=body,
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        return self._send(req)

    @staticmethod
    def _send(req: urllib.request.Request) -> _SimpleResponse:
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return _SimpleResponse(resp.status, resp.read(), dict(resp.headers.items()))
        except urllib.error.HTTPError as e:
            return _SimpleResponse(e.code, e.read(), dict(e.headers.items()))


def _make_client():
    try:
        from fastapi.testclient import TestClient

        return TestClient(server.app), None
    except RuntimeError:
        live = _LiveHttpClient(server.app)
        return live, live.close


def _prepare_test_assets(target_dir: str) -> None:
    mosaic_bgr = wm.make_mosaic(2000, 3000, seed=1)
    mosaic_rgb = cv2.cvtColor(mosaic_bgr, cv2.COLOR_BGR2RGB)
    pil_im = Image.fromarray(mosaic_rgb)
    pil_im.save(os.path.join(target_dir, "cover.png"), "PNG")
    pil_im.save(os.path.join(target_dir, "cover.jpg"), "JPEG", quality=95)
    pil_im.save(os.path.join(target_dir, "cover.webp"), "WEBP", quality=95)
    pil_im.save(os.path.join(target_dir, "cover.bmp"), "BMP")
    # Build a realistic high-contrast custom badge logo (~35% ink) for upload tests
    canvas = np.full((256, 256), 255, dtype=np.uint8)
    cv2.rectangle(canvas, (18, 18), (238, 238), 0, 18)
    cv2.circle(canvas, (128, 112), 54, 0, -1)
    cv2.circle(canvas, (128, 112), 26, 255, -1)
    cv2.putText(canvas, "G08", (54, 214), cv2.FONT_HERSHEY_SIMPLEX, 2.0, 0, 10, cv2.LINE_AA)
    cv2.imwrite(os.path.join(target_dir, "mylogo.png"), canvas)


def main() -> int:
    tmp_ctx = None
    if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
        d = sys.argv[1]
    else:
        tmp_ctx = tempfile.TemporaryDirectory(prefix="wm_api_test_")
        d = tmp_ctx.name
        _prepare_test_assets(d)

    c, closer = _make_client()
    total = 0
    fails = 0

    def ok(cond, msg):
        nonlocal total, fails
        total += 1
        print(("PASS " if cond else "FAIL ") + f"[{total:02d}] {msg}")
        fails += not cond

    def up(name):
        with open(os.path.join(d, name), "rb") as f:
            r = c.post("/api/upload", files={"file": (name, f)})
        assert r.status_code == 200, r.text
        return r.json()

    def embed(iid, key="k1", method="dct", src="upload"):
        data = dict(image_id=iid, key=key, alpha=25, method=method, logo_source=src, logo_text="UNI")
        if src == "upload":
            with open(os.path.join(d, "mylogo.png"), "rb") as f:
                return c.post("/api/embed", data=data, files={"logo_file": ("l.png", f)})
        return c.post("/api/embed", data=data)

    def extract(iid, key="k1", method="dct", mode="search", src="upload"):
        data = dict(image_id=iid, key=key, alpha=25, method=method, mode=mode, logo_source=src, logo_text="UNI", null_trials=30)
        if src == "upload":
            with open(os.path.join(d, "mylogo.png"), "rb") as f:
                r = c.post("/api/extract", data=data, files={"logo_file": ("l.png", f)})
        else:
            r = c.post("/api/extract", data=data)
        assert r.status_code == 200, r.text
        return r.json()

    def attack(iid, **kw):
        r = c.post("/api/attack", data=dict(image_id=iid, **kw))
        assert r.status_code == 200, r.text
        return r.json()

    try:
        assert c.get("/api/health").json()["ok"]

        # 1) Upload, decoding and rejection of non-images (5 checks)
        infos = {n: up(n) for n in ["cover.png", "cover.jpg", "cover.webp", "cover.bmp"]}
        for n, i in infos.items():
            ok(i["width"] == 3000 and i["height"] == 2000, f"upload {n}: {i['format']} {i['width']}x{i['height']} copies {i['copies']:.1f}")
        r = c.post("/api/upload", files={"file": ("x.txt", b"not an image")})
        ok(r.status_code == 400, "non-image rejected")

        # 2) Logo creation (3 checks)
        for src, extra in [("standard", {}), ("text", {"logo_text": "UNI"}), ("upload", {})]:
            if src == "upload":
                with open(os.path.join(d, "mylogo.png"), "rb") as f:
                    r = c.post("/api/logo/preview", data={"logo_source": src, **extra}, files={"logo_file": ("l.png", f)})
            else:
                r = c.post("/api/logo/preview", data={"logo_source": src, **extra})
            ok(r.status_code == 200 and r.headers["content-type"] == "image/png" and int(r.headers["x-ink-pixels"]) > 100,
               f"logo preview {src}: ink {r.headers.get('x-ink-pixels')}")

        # 3) Embedding into four input formats (4 checks)
        wm_ids = {}
        for n in ["cover.jpg", "cover.webp", "cover.bmp", "cover.png"]:
            r = embed(infos[n]["id"])
            assert r.status_code == 200, r.text
            j = r.json()
            wm_ids[n] = j["id"]
            ok(j["psnr"] > 38 and j["ssim"] > 0.96, f"embed into {n}: PSNR {j['psnr']:.2f} SSIM {j['ssim']:.4f} in {j['seconds']}s")

        # 4) Extraction and key checks (4 checks)
        wid = wm_ids["cover.png"]
        e = extract(wid)
        ok(e["ber"] == 0 and e["detected"], f"search, no attack: NC {e['nc']:.3f} BER {e['ber']:.3f} score {e['score']:.3f} thr {e['threshold']:.3f}")
        e = extract(wid, mode="aligned", src="standard")
        ok(e["structure"] - e["structure_baseline"] > 0.12, f"aligned (no logo needed): structure {e['structure']:.2f} vs baseline {e['structure_baseline']:.2f}")
        e = extract(wid, key="wrong", mode="aligned", src="standard")
        ok(e["structure"] - e["structure_baseline"] < 0.05, f"aligned wrong key looks like noise: excess {e['structure'] - e['structure_baseline']:.3f}")
        e = extract(wid, key="wrong")
        ok(not e["detected"], f"search wrong key not detected: score {e['score']:.3f} thr {e['threshold']:.3f}")

        # 5) Attacks and their validation (8 checks)
        a = attack(wid, jpeg_quality=70)
        ok(a["format"] == "JPEG" and a["psnr"] is not None, f"attack {a['desc']} -> {a['format']} (PSNR {a['psnr']:.2f} dB)")
        e = extract(a["id"])
        ok(e["ber"] < 0.02, f"JPEG70: NC {e['nc']:.3f} BER {e['ber']:.3f}")
        a = attack(wid, jpeg_quality=50)
        e = extract(a["id"])
        ok(e["nc"] > 0.85, f"JPEG50: NC {e['nc']:.3f} BER {e['ber']:.3f}")
        a = attack(wid, crop_x=753, crop_y=505, crop_w=1500, crop_h=1000, jpeg_quality=70)
        e = extract(a["id"])
        ok(e["ber"] < 0.02, f"crop 1500x1000 + JPEG70: NC {e['nc']:.3f} BER {e['ber']:.3f} offset {e['offset']} phase {e['phase']}")
        a = attack(wid, crop_x=301, crop_y=417, crop_w=512, crop_h=512)
        e = extract(a["id"])
        ok(e["nc"] > 0.9, f"crop 512x512: NC {e['nc']:.3f}")
        a = attack(wid, crop_x=301, crop_y=417, crop_w=384, crop_h=384)
        e = extract(a["id"])
        print(f"INFO crop 384x384 (< 1 copy of every bit): NC {e['nc']:.3f} BER {e['ber']:.3f}")
        a = attack(wid, noise_sigma=3)
        e = extract(a["id"])
        ok(e["ber"] < 0.02, f"noise sigma=3: BER {e['ber']:.3f}")
        a = attack(wid, overwrite=True, overwrite_alpha=25)
        e = extract(a["id"])
        ok(a["psnr"] is not None and a["psnr"] > 35 and not e["detected"] and e["ber"] > 0.35,
           f"overwrite attack erases mark: PSNR {a['psnr']:.2f} dB NC {e['nc']:.3f} BER {e['ber']:.3f}")
        r = c.post("/api/attack", data=dict(image_id=wid, crop_x=2900, crop_y=0, crop_w=500, crop_h=500))
        ok(r.status_code == 400, "crop outside image rejected: " + r.json()["detail"][:60])

        # 6) Round trip from every input format (4 checks)
        for n, i in wm_ids.items():
            e = extract(i)
            ok(e["ber"] == 0, f"extract from watermarked version of {n}: BER {e['ber']:.3f}")

        # 7) Text and standard logo after JPEG 70 (2 checks)
        for src in ("text", "standard"):
            j = embed(infos["cover.png"]["id"], src=src).json()
            a = attack(j["id"], jpeg_quality=70)
            e = extract(a["id"], src=src)
            ok(e["ber"] < 0.02, f"{src} logo, JPEG70: NC {e['nc']:.3f}")

        # 8) LSB baseline (2 checks)
        j = embed(infos["cover.png"]["id"], method="lsb").json()
        a = attack(j["id"], jpeg_quality=90)
        e = extract(a["id"], method="lsb")
        ok(e["ber"] > 0.3 and not e["detected"], f"LSB dies under JPEG90: BER {e['ber']:.3f}")
        e = extract(j["id"], method="lsb")
        ok(e["ber"] == 0, f"LSB fine without attack: BER {e['ber']:.3f}")

        # 9) Download, preview and input validation (3 checks)
        r = c.get(f"/api/image/{wid}/download")
        ok(r.status_code == 200 and r.content[:4] == b"\x89PNG", "download returns PNG")
        r = c.get(f"/api/image/{wid}/preview?max=600")
        ok(r.status_code == 200 and r.content[:2] == b"\xff\xd8", "preview returns JPEG")
        _, buf = cv2.imencode(".png", np.zeros((300, 300, 3), np.uint8) + 100)
        s = c.post("/api/upload", files={"file": ("small.png", buf.tobytes())}).json()
        r = embed(s["id"], src="standard")
        ok(r.status_code == 400, "too-small image rejected: " + r.json()["detail"][:50])

        print(f"\nALL {total} PASSED" if not fails else f"\n{fails}/{total} FAILED")
        return 1 if fails else 0
    finally:
        if closer:
            closer()
        if tmp_ctx:
            tmp_ctx.cleanup()


if __name__ == "__main__":
    sys.exit(main())
