"""Build the 64x64 binary watermark (1 = ink) from: standard logo, uploaded image, or text."""
import io

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import wm

T = wm.TILE
_FONTS = ["DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf", "LiberationSans-Bold.ttf", "Helvetica.ttc"]


def _font(size):
    for name in _FONTS:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)  # Pillow >= 10.1


def _flatten(im):
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    return im.convert("L")


def _bits(gray64, threshold, invert):
    ink = np.asarray(gray64, np.uint8) < int(threshold)
    return (~ink if invert else ink).astype(np.uint8)


def standard():
    return wm.make_logo(None)


def from_upload(data, threshold=128, invert=False):
    im = Image.open(io.BytesIO(data))
    im.load()
    g = _flatten(im)
    if g.size == (T, T):            # exact 64x64 (e.g. a downloaded reference logo): use as is
        return _bits(g, threshold, invert)
    s = min(60 / g.width, 60 / g.height)
    g = g.resize((max(1, round(g.width * s)), max(1, round(g.height * s))), Image.LANCZOS)
    canvas = Image.new("L", (T, T), 255)
    canvas.paste(g, ((T - g.width) // 2, (T - g.height) // 2))
    return _bits(canvas, threshold, invert)


def from_text(text, threshold=128, invert=False):
    text = (text or "").strip()[:10]
    canvas = Image.new("L", (T, T), 255)
    if text:
        probe = ImageDraw.Draw(canvas)
        bb = probe.textbbox((0, 0), text, font=_font(100))
        w, h = max(1, bb[2] - bb[0]), max(1, bb[3] - bb[1])
        size = max(6, int(100 * min(60 / w, 56 / h)))
        font = _font(size)
        d = ImageDraw.Draw(canvas)
        bb = d.textbbox((0, 0), text, font=font)
        x = (T - (bb[2] - bb[0])) / 2 - bb[0]
        y = (T - (bb[3] - bb[1])) / 2 - bb[1]
        d.text((x, y), text, fill=0, font=font)
    return _bits(canvas, threshold, invert)


def build(source, file_bytes=None, text="", threshold=128, invert=False):
    if source == "standard":
        return standard()
    if source == "upload":
        if not file_bytes:
            raise ValueError("choose a logo image first")
        return from_upload(file_bytes, threshold, invert)
    if source == "text":
        return from_text(text, threshold, invert)
    raise ValueError(f"unknown logo source: {source}")


def to_png(bits, scale=1):
    """Ink (1) as black on white, nearest-neighbour scaled."""
    g = np.where(np.asarray(bits) > 0, 0, 255).astype(np.uint8)
    im = Image.fromarray(g, "L").resize((T * scale, T * scale), Image.NEAREST)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()
