"""Pure domain service to build 64x64 binary watermark logos (1 = ink)."""
import io
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from src.domain_shared.consts import TILE_SIZE
from src.domain_shared.enums import LogoSource
from . import dct_engine

T = TILE_SIZE
_FONTS = [
    "DejaVuSans-Bold.ttf",
    "arialbd.ttf",
    "Arial Bold.ttf",
    "LiberationSans-Bold.ttf",
    "Helvetica.ttc",
]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in _FONTS:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _flatten(im: Image.Image) -> Image.Image:
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    return im.convert("L")


def _bits(gray64: Image.Image, threshold: int, invert: bool) -> np.ndarray:
    ink = np.asarray(gray64, np.uint8) < int(threshold)
    return (~ink if invert else ink).astype(np.uint8)


def standard() -> np.ndarray:
    return dct_engine.make_logo(None)


def from_upload(data: bytes, threshold: int = 128, invert: bool = False) -> np.ndarray:
    im = Image.open(io.BytesIO(data))
    im.load()
    g = _flatten(im)
    if g.size == (T, T):
        return _bits(g, threshold, invert)
    s = min(60 / g.width, 60 / g.height)
    g = g.resize((max(1, round(g.width * s)), max(1, round(g.height * s))), Image.LANCZOS)
    canvas = Image.new("L", (T, T), 255)
    canvas.paste(g, ((T - g.width) // 2, (T - g.height) // 2))
    return _bits(canvas, threshold, invert)


def from_text(text: str, threshold: int = 128, invert: bool = False) -> np.ndarray:
    text = (text or "").strip()[:10]
    canvas = Image.new("L", (T, T), 255)
    if text:
        probe = ImageDraw.Draw(canvas)
        bb = probe.textbbox((0, 0), text, font=_font(100))
        w, h = max(1, bb[2] - bb[0]), max(1, bb[3] - bb[1])
        size = max(6, int(100 * min(60 / w, 56 / h)))
        font = _font(size)
        draw = ImageDraw.Draw(canvas)
        bb = draw.textbbox((0, 0), text, font=font)
        x = (T - (bb[2] - bb[0])) / 2 - bb[0]
        y = (T - (bb[3] - bb[1])) / 2 - bb[1]
        draw.text((x, y), text, fill=0, font=font)
    return _bits(canvas, threshold, invert)


def build(
    source: str,
    file_bytes: Optional[bytes] = None,
    text: str = "",
    threshold: int = 128,
    invert: bool = False,
) -> np.ndarray:
    if source == LogoSource.STANDARD.value:
        return standard()
    if source == LogoSource.UPLOAD.value:
        if not file_bytes:
            raise ValueError("choose a logo image first")
        return from_upload(file_bytes, threshold, invert)
    if source == LogoSource.TEXT.value:
        return from_text(text, threshold, invert)
    raise ValueError(f"unknown logo source: {source}")


def to_png(bits: np.ndarray, scale: int = 1) -> bytes:
    """Ink (1) as black on white, nearest-neighbour scaled."""
    g = np.where(np.asarray(bits) > 0, 0, 255).astype(np.uint8)
    im = Image.fromarray(g, "L").resize((T * scale, T * scale), Image.NEAREST)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()
