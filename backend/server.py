"""
FastAPI backend: every algorithm step (decode, logo, embed, attack, extract) runs
in Python via wm.py. The Next.js frontend only draws the UI and calls these endpoints.

    python server.py                      # uses APP_HOST / APP_PORT from .env
    uvicorn server:app --port 8000
"""
import base64
import io
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image

from config import settings
import logos
import wm

app = FastAPI(title=settings.app_title)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Ink-Pixels"],
)

STORE = Path(settings.storage_dir or tempfile.mkdtemp(prefix="wmstore_"))
STORE.mkdir(parents=True, exist_ok=True)
TTL_SECONDS = settings.storage_ttl_seconds
CLEANUP_INTERVAL = settings.cleanup_interval_seconds
MAX_BYTES = settings.max_upload_bytes
MIN_BLOCKS = wm.TILE * wm.TILE
_meta: dict = {}
_lock = threading.Lock()


# ----------------------------------------------------------------- storage
def _put(data: bytes, ext: str, name: str, w: int, h: int, fmt: str) -> dict:
    iid = uuid.uuid4().hex
    path = STORE / f"{iid}.{ext}"
    path.write_bytes(data)
    blocks = (h // wm.B) * (w // wm.B)
    m = dict(id=iid, path=str(path), ext=ext, name=name, width=w, height=h, format=fmt, bytes=len(data),
             blocks=blocks, copies=blocks / MIN_BLOCKS, t=time.time())
    with _lock:
        _meta[iid] = m
    return _public(m)


def _public(m: dict) -> dict:
    return {k: m[k] for k in ("id", "name", "width", "height", "format", "bytes", "blocks", "copies")}


def _get(iid: str) -> dict:
    with _lock:
        m = _meta.get(iid)
    if not m:
        raise HTTPException(404, "image not found or expired; upload it again")
    return m


def _load(iid: str) -> np.ndarray:
    m = _get(iid)
    try:
        return wm.decode_image(Path(m["path"]).read_bytes())
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"cannot decode image: {e}")


def _cleanup_loop():
    while True:
        time.sleep(CLEANUP_INTERVAL)
        cutoff = time.time() - TTL_SECONDS
        with _lock:
            old = [k for k, m in _meta.items() if m["t"] < cutoff]
            for k in old:
                try:
                    os.remove(_meta[k]["path"])
                except OSError:
                    pass
                del _meta[k]


threading.Thread(target=_cleanup_loop, daemon=True).start()


def _base(name: str) -> str:
    return Path(name).stem or "image"


# ----------------------------------------------------------------- helpers
def _logo(source, text, threshold, invert, file: Optional[UploadFile]) -> np.ndarray:
    data = file.file.read() if file is not None else None
    try:
        return logos.build(source, data, text, threshold, invert)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"logo error: {e}")


def _check_common(key: str, alpha: float, method: str):
    if not key.strip():
        raise HTTPException(400, "secret key is empty")
    if method not in ("dct", "lsb"):
        raise HTTPException(400, "method must be dct or lsb")
    if not 5 <= alpha <= 100:
        raise HTTPException(400, "alpha must be between 5 and 100")


def _png_bytes(img) -> bytes:
    ok, buf = cv2.imencode(".png", img, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    return buf.tobytes()


def _f(x):
    return None if x is None or not np.isfinite(x) else float(x)


# ----------------------------------------------------------------- routes
@app.get("/api/health")
def health():
    return {"ok": True, "cv2": cv2.__version__, "numpy": np.__version__}


@app.post("/api/upload")
def upload(file: UploadFile = File(...)):
    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, f"file too large (limit {settings.max_upload_mb} MB)")
    try:
        im = Image.open(io.BytesIO(data))
        fmt = (im.format or "IMG").upper()
        bgr = wm.decode_image(data)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"cannot read this file as an image ({e}). Try PNG, JPEG, WebP, BMP, GIF or TIFF.")
    ext = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "BMP": "bmp", "GIF": "gif", "TIFF": "tif"}.get(fmt, "bin")
    return _put(data, ext, file.filename or f"image.{ext}", bgr.shape[1], bgr.shape[0], fmt)


@app.get("/api/image/{iid}/preview")
def preview(iid: str, max: int = 900):
    img = _load(iid)
    s = min(1.0, max / img.shape[1])
    if s < 1:
        img = cv2.resize(img, (int(img.shape[1] * s), int(img.shape[0] * s)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return Response(buf.tobytes(), media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.get("/api/image/{iid}/download")
def download(iid: str):
    m = _get(iid)
    mt = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp", "bmp": "image/bmp"}.get(m["ext"], "application/octet-stream")
    return FileResponse(m["path"], media_type=mt, filename=m["name"])


@app.post("/api/logo/preview")
def logo_preview(logo_source: str = Form("standard"), logo_text: str = Form(""), logo_threshold: int = Form(128),
                 logo_invert: bool = Form(False), scale: int = Form(2),
                 logo_file: Optional[UploadFile] = File(None)):
    bits = _logo(logo_source, logo_text, logo_threshold, logo_invert, logo_file)
    return Response(logos.to_png(bits, max(1, min(8, scale))), media_type="image/png", headers={"X-Ink-Pixels": str(int(bits.sum()))})


@app.post("/api/embed")
def api_embed(image_id: str = Form(...), key: str = Form(...), alpha: float = Form(settings.default_alpha),
              method: str = Form("dct"), logo_source: str = Form("standard"), logo_text: str = Form(""),
              logo_threshold: int = Form(128), logo_invert: bool = Form(False),
              logo_file: Optional[UploadFile] = File(None)):
    _check_common(key, alpha, method)
    m = _get(image_id)
    if m["blocks"] < MIN_BLOCKS:
        raise HTTPException(400, f"image too small: {m['blocks']} blocks, need at least {MIN_BLOCKS} (about 512x512 px)")
    bits = _logo(logo_source, logo_text, logo_threshold, logo_invert, logo_file)
    if int(bits.sum()) < 20:
        raise HTTPException(400, "logo is nearly empty; adjust the threshold or choose another logo")
    img = _load(image_id)
    t = time.time()
    out = (wm.embed_dct if method == "dct" else wm.embed_lsb)(img, bits, key, alpha)
    psnr = wm.psnr(img, out)
    ssim = wm.ssim_y(img, out) if img.shape[0] * img.shape[1] <= 12_000_000 else None
    info = _put(_png_bytes(out), "png", f"{_base(m['name'])}_watermarked.png", out.shape[1], out.shape[0], "PNG")
    return dict(info, psnr=_f(psnr), ssim=_f(ssim), seconds=round(time.time() - t, 2))


@app.post("/api/attack")
def api_attack(image_id: str = Form(...), crop_x: Optional[int] = Form(None), crop_y: Optional[int] = Form(None),
               crop_w: Optional[int] = Form(None), crop_h: Optional[int] = Form(None),
               overwrite: bool = Form(False), overwrite_alpha: float = Form(settings.default_alpha),
               noise_sigma: float = Form(0.0), jpeg_quality: int = Form(0)):
    m = _get(image_id)
    orig = _load(image_id)
    img = orig
    parts = []
    if None not in (crop_x, crop_y, crop_w, crop_h):
        h, w = img.shape[:2]
        if crop_x < 0 or crop_y < 0 or crop_w < 8 or crop_h < 8 or crop_x + crop_w > w or crop_y + crop_h > h:
            raise HTTPException(400, f"crop must stay inside the image ({w}x{h}) and be at least 8x8")
        img = wm.attack_crop(img, crop_y, crop_x, crop_h, crop_w)
        parts.append(f"crop {crop_w}x{crop_h} @({crop_x},{crop_y})")
    if overwrite:
        if not 5 <= overwrite_alpha <= 100:
            raise HTTPException(400, "overwrite alpha must be between 5 and 100")
        img = wm.attack_overwrite(img, overwrite_alpha, seed=int(time.time()) & 0xFFFF)
        parts.append(f"overwrite attack (random bits, alpha={overwrite_alpha:g})")
    if noise_sigma > 0:
        img = wm.attack_noise(img, noise_sigma, seed=int(time.time()) & 0xFFFF)
        parts.append(f"noise sigma={noise_sigma:g}")
    base = _base(m["name"])
    if jpeg_quality:
        if not 1 <= jpeg_quality <= 100:
            raise HTTPException(400, "jpeg quality must be 1-100")
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, int(jpeg_quality)])
        parts.append(f"JPEG Q={jpeg_quality}")
        final_img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        info = _put(buf.tobytes(), "jpg", f"{base}_attacked.jpg", img.shape[1], img.shape[0], "JPEG")
    else:
        final_img = img
        info = _put(_png_bytes(img), "png", f"{base}_attacked.png", img.shape[1], img.shape[0], "PNG")
    atk_psnr = wm.psnr(orig, final_img) if (parts and final_img.shape == orig.shape) else None
    return dict(info, desc=" -> ".join(parts) or "no attack", psnr=_f(atk_psnr))


@app.post("/api/extract")
def api_extract(image_id: str = Form(...), key: str = Form(...), alpha: float = Form(settings.default_alpha),
                method: str = Form("dct"), mode: str = Form("search"),
                null_trials: int = Form(settings.default_null_trials),
                logo_source: str = Form("standard"), logo_text: str = Form(""),
                logo_threshold: int = Form(128), logo_invert: bool = Form(False),
                logo_file: Optional[UploadFile] = File(None)):
    _check_common(key, alpha, method)
    if mode not in ("search", "aligned"):
        raise HTTPException(400, "mode must be search or aligned")
    m = _get(image_id)
    if m["blocks"] < 1:
        raise HTTPException(400, "image is too small")
    img = _load(image_id)
    t = time.time()
    res = dict(mode=mode, blocks=m["blocks"], copies=m["copies"])
    if mode == "aligned":
        r = wm.extract_aligned(img, key, method, alpha)
    else:
        ref = _logo(logo_source, logo_text, logo_threshold, logo_invert, logo_file)
        r = wm.extract(img, ref, key, method, alpha, null_trials=max(0, min(settings.max_null_trials, null_trials)))
        res.update(nc=_f(wm.nc(ref, r["logo"])), ber=_f(wm.ber(ref, r["logo"])), score=_f(r["score"]),
                   threshold=_f(r["threshold"]), null_mean=_f(r["null_mean"]), null_max=_f(r["null_max"]),
                   detected=r["detected"], offset=list(r["offset"]), phase=list(r["shift"]))
    res.update(structure=_f(r["structure"]), structure_baseline=_f(r["structure_baseline"]),
               logo_png="data:image/png;base64," + base64.b64encode(logos.to_png(r["logo"], 4)).decode(),
               seconds=round(time.time() - t, 2))
    return res


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host=settings.app_host, port=settings.app_port)
