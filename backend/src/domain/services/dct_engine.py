"""Pure domain service for DCT/LSB watermarking, attacks, metrics, and image decoding.

Zero web-framework or storage-layer dependencies.
"""
import hashlib
import io
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageOps
from skimage.metrics import structural_similarity

from src.domain_shared.consts import (
    BLOCK_SIZE,
    DCT_COEFF_P,
    DCT_COEFF_Q,
    DEFAULT_ALPHA,
    MAX_IMAGE_PIXELS,
    SEARCH_SIDE,
    TILE_SIZE,
)

B = BLOCK_SIZE
P = DCT_COEFF_P
Q = DCT_COEFF_Q
TILE = TILE_SIZE


# --------------------------------------------------------------------------
# DCT helpers (orthonormal 8x8 DCT-II == JPEG DCT)
# --------------------------------------------------------------------------
def _dct_matrix(n: int = B) -> np.ndarray:
    k = np.arange(n)[:, None]
    x = np.arange(n)[None, :]
    d = np.sqrt(2.0 / n) * np.cos((2 * x + 1) * k * np.pi / (2 * n))
    d[0, :] = np.sqrt(1.0 / n)
    return d


D = _dct_matrix()


def to_blocks(y: np.ndarray, oy: int = 0, ox: int = 0) -> tuple[np.ndarray, int, int]:
    """Return (hb, wb, 8, 8) view of full blocks starting at pixel (oy, ox)."""
    h, w = y.shape
    hb, wb = (h - oy) // B, (w - ox) // B
    a = y[oy:oy + hb * B, ox:ox + wb * B]
    return a.reshape(hb, B, wb, B).transpose(0, 2, 1, 3), hb, wb


def from_blocks(blk: np.ndarray) -> np.ndarray:
    hb, wb = blk.shape[:2]
    return blk.transpose(0, 2, 1, 3).reshape(hb * B, wb * B)


def dct_blocks(blk: np.ndarray) -> np.ndarray:
    return D @ blk @ D.T


def idct_blocks(c: np.ndarray) -> np.ndarray:
    return D.T @ c @ D


# --------------------------------------------------------------------------
# Logo + keyed permutation
# --------------------------------------------------------------------------
def make_logo(path: Optional[str] = None) -> np.ndarray:
    """64x64 binary logo (0/1). Default: ring with letter 'C' and 'WM'."""
    if path:
        im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if im is None:
            raise ValueError(f"cannot read logo: {path}")
        im = cv2.resize(im, (TILE, TILE), interpolation=cv2.INTER_AREA)
        return (im > 127).astype(np.uint8)
    im = np.zeros((TILE, TILE), np.uint8)
    cv2.circle(im, (32, 32), 29, 255, 3)
    cv2.putText(im, "C", (17, 44), cv2.FONT_HERSHEY_SIMPLEX, 1.5, 255, 3, cv2.LINE_AA)
    cv2.putText(im, "WM", (19, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.45, 255, 1, cv2.LINE_AA)
    return (im > 127).astype(np.uint8)


def keyed_perm(key: str, n: int = TILE * TILE) -> np.ndarray:
    """Key-dependent permutation seeded from SHA-256(key)."""
    seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")
    return np.random.default_rng(seed).permutation(n)


def make_tile(logo: np.ndarray, key: str) -> np.ndarray:
    """logo (0/1, 64x64) -> scrambled tile (0/1, 64x64)."""
    perm = keyed_perm(key)
    flat = logo.reshape(-1)
    tile = np.empty_like(flat)
    tile[perm] = flat
    return tile.reshape(TILE, TILE)


def untile(tile_bits: np.ndarray, key: str) -> np.ndarray:
    perm = keyed_perm(key)
    return tile_bits.reshape(-1)[perm].reshape(TILE, TILE)


def tile_signs(logo: np.ndarray, key: str) -> np.ndarray:
    return 2.0 * make_tile(logo, key).astype(np.float64) - 1.0


# --------------------------------------------------------------------------
# Embedding
# --------------------------------------------------------------------------
def embed_dct(img_bgr: np.ndarray, logo: np.ndarray, key: str, alpha: float = DEFAULT_ALPHA) -> np.ndarray:
    ycc = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
    y = ycc[..., 0].astype(np.float64)
    blk, hb, wb = to_blocks(y)
    c = dct_blocks(blk)
    s_tile = tile_signs(logo, key)
    s_grid = s_tile[np.ix_(np.arange(hb) % TILE, np.arange(wb) % TILE)]
    d = c[:, :, P[0], P[1]] - c[:, :, Q[0], Q[1]]
    deficit = np.maximum(alpha - s_grid * d, 0.0)
    shift = 0.5 * deficit * s_grid
    c[:, :, P[0], P[1]] += shift
    c[:, :, Q[0], Q[1]] -= shift
    y2 = y.copy()
    y2[:hb * B, :wb * B] = from_blocks(idct_blocks(c))
    ycc[..., 0] = np.clip(np.rint(y2), 0, 255).astype(np.uint8)
    return cv2.cvtColor(ycc, cv2.COLOR_YCrCb2BGR)


def embed_lsb(img_bgr: np.ndarray, logo: np.ndarray, key: str, alpha: Optional[float] = None) -> np.ndarray:
    """Baseline: same tiled/keyed payload, one bit per block in top-left luminance LSB."""
    ycc = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
    y = ycc[..., 0].copy()
    h, w = y.shape
    hb, wb = h // B, w // B
    bits = make_tile(logo, key)[np.ix_(np.arange(hb) % TILE, np.arange(wb) % TILE)]
    sub = y[0:hb * B:B, 0:wb * B:B]
    y[0:hb * B:B, 0:wb * B:B] = (sub & 0xFE) | bits.astype(np.uint8)
    ycc[..., 0] = y
    return cv2.cvtColor(ycc, cv2.COLOR_YCrCb2BGR)


# --------------------------------------------------------------------------
# Extraction: grid offset search + tile phase search
# --------------------------------------------------------------------------
def soft_values(y: np.ndarray, oy: int, ox: int, method: str, alpha: float) -> np.ndarray:
    """Per-block soft value (hb, wb); sign carries the bit (+1 -> bit 1)."""
    if method == "dct":
        blk, _, _ = to_blocks(y, oy, ox)
        c = dct_blocks(blk)
        d = c[:, :, P[0], P[1]] - c[:, :, Q[0], Q[1]]
        return np.clip(d, -2.0 * alpha, 2.0 * alpha)
    h, w = y.shape
    hb, wb = (h - oy) // B, (w - ox) // B
    sub = y[oy:oy + hb * B:B, ox:ox + wb * B:B].astype(np.int64)
    return 2.0 * (sub & 1).astype(np.float64) - 1.0


def fold(v: np.ndarray) -> np.ndarray:
    """Sum soft values into a 64x64 tile by block index modulo 64."""
    hb, wb = v.shape
    vp = np.pad(v, ((0, (-hb) % TILE), (0, (-wb) % TILE)))
    return vp.reshape(vp.shape[0] // TILE, TILE, vp.shape[1] // TILE, TILE).sum((0, 2))


def xcorr_peak(f_tile: np.ndarray, s_tile: np.ndarray) -> tuple[tuple[int, int], float]:
    """Circular cross-correlation of mean-centred tiles; return best shift and normalised score."""
    f_centered = f_tile - f_tile.mean()
    s_centered = s_tile - s_tile.mean()
    g = np.fft.ifft2(np.conj(np.fft.fft2(f_centered)) * np.fft.fft2(s_centered)).real
    ti, tj = np.unravel_index(np.argmax(g), g.shape)
    denom = np.linalg.norm(f_centered) * np.linalg.norm(s_centered)
    return (int(ti), int(tj)), (float(g[ti, tj] / denom) if denom > 0 else 0.0)


def search_region(y: np.ndarray) -> tuple[np.ndarray, int, int]:
    h, w = y.shape
    sh, sw = min(h, SEARCH_SIDE), min(w, SEARCH_SIDE)
    y0, x0 = (h - sh) // 2, (w - sw) // 2
    return y[y0:y0 + sh, x0:x0 + sw], y0, x0


def grid_folds(y: np.ndarray, method: str, alpha: float) -> dict[tuple[int, int], np.ndarray]:
    """Pre-compute folded votes for all 64 grid offsets on the search region."""
    ys, _, _ = search_region(y)
    ys = ys.astype(np.float64)
    out: dict[tuple[int, int], np.ndarray] = {}
    for oy in range(B):
        for ox in range(B):
            out[(oy, ox)] = fold(soft_values(ys, oy, ox, method, alpha))
    return out


def best_alignment(
    folds: dict[tuple[int, int], np.ndarray], s_tile: np.ndarray
) -> tuple[float, Optional[tuple[int, int]], Optional[tuple[int, int]]]:
    best: tuple[float, Optional[tuple[int, int]], Optional[tuple[int, int]]] = (-1.0, None, None)
    for off, f_tile in folds.items():
        shift, score = xcorr_peak(f_tile, s_tile)
        if score > best[0]:
            best = (score, off, shift)
    return best


def structure_score(bits: np.ndarray) -> float:
    """Fraction of adjacent (h/v) equal pixels in a 64x64 bit image."""
    b = np.asarray(bits, np.uint8)
    eq = (b[:, :-1] == b[:, 1:]).sum() + (b[:-1, :] == b[1:, :]).sum()
    return float(eq) / (b[:, :-1].size + b[:-1, :].size)


def structure_baseline(bits: np.ndarray) -> float:
    """Expected structure_score of a random scramble of the same pixels."""
    p = float(np.asarray(bits).mean())
    return p * p + (1.0 - p) * (1.0 - p)


def extract(
    img_bgr: np.ndarray,
    logo_ref: np.ndarray,
    key: str,
    method: str = "dct",
    alpha: float = DEFAULT_ALPHA,
    null_trials: int = 0,
) -> dict:
    """Hypothesis-guided extraction using key + reference logo."""
    y = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)[..., 0]
    s_tile = tile_signs(logo_ref, key)
    folds = grid_folds(y, method, alpha)
    score, off_r, _ = best_alignment(folds, s_tile)
    assert off_r is not None
    oy_r, ox_r = off_r
    _, ry0, rx0 = search_region(y)
    oy, ox = (oy_r + ry0) % B, (ox_r + rx0) % B
    f_full = fold(soft_values(y.astype(np.float64), oy, ox, method, alpha))
    (ti, tj), _ = xcorr_peak(f_full, s_tile)
    f_aligned = np.roll(f_full, (ti, tj), axis=(0, 1))
    tile_bits = (f_aligned > 0).astype(np.uint8)
    logo_est = untile(tile_bits, key)
    out: dict = dict(
        logo=logo_est,
        score=float(score),
        offset=(ox, oy),
        shift=(ti, tj),
        structure=structure_score(logo_est),
        structure_baseline=structure_baseline(logo_est),
    )
    if null_trials:
        nulls = np.array(
            [
                best_alignment(folds, tile_signs(logo_ref, f"{key}#null{k}"))[0]
                for k in range(null_trials)
            ]
        )
        thr = float(nulls.mean() + 6 * nulls.std())
        out.update(
            null_mean=float(nulls.mean()),
            null_max=float(nulls.max()),
            threshold=thr,
            detected=bool(score > thr),
        )
    return out


def extract_aligned(
    img_bgr: np.ndarray,
    key: str,
    method: str = "dct",
    alpha: float = DEFAULT_ALPHA,
) -> dict:
    """Key-only extraction for an UNCROPPED image: grid offset (0,0), tile phase 0."""
    y = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)[..., 0].astype(np.float64)
    f_tile = fold(soft_values(y, 0, 0, method, alpha))
    logo = untile((f_tile > 0).astype(np.uint8), key)
    return dict(
        logo=logo,
        structure=structure_score(logo),
        structure_baseline=structure_baseline(logo),
    )


def decode_image(data: bytes) -> np.ndarray:
    """Decode PNG/JPEG/WebP/BMP/GIF/TIFF bytes -> BGR uint8 with EXIF orientation & white flatten."""
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    im = Image.open(io.BytesIO(data))
    im.load()
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    rgb = np.asarray(im.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def encode_png(img_bgr: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", img_bgr, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    if not ok:
        raise ValueError("Failed to encode PNG image.")
    return buf.tobytes()


def encode_jpeg(img_bgr: np.ndarray, quality: int = 88) -> bytes:
    ok, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
    if not ok:
        raise ValueError("Failed to encode JPEG image.")
    return buf.tobytes()


# --------------------------------------------------------------------------
# Attacks
# --------------------------------------------------------------------------
def attack_jpeg(img: np.ndarray, q: int) -> np.ndarray:
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, int(q)])
    if not ok:
        raise ValueError("Failed to encode JPEG attack.")
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


def attack_crop(img: np.ndarray, y: int, x: int, h: int, w: int) -> np.ndarray:
    return img[y:y + h, x:x + w].copy()


def attack_noise(img: np.ndarray, sigma: float, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = rng.normal(0, sigma, img.shape)
    return np.clip(img.astype(np.float64) + n, 0, 255).astype(np.uint8)


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------
def psnr(a: np.ndarray, b: np.ndarray) -> float:
    return float(cv2.PSNR(a, b))


def ssim_y(a: np.ndarray, b: np.ndarray) -> float:
    ya = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
    yb = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)
    return float(structural_similarity(ya, yb, data_range=255))


def nc(w: np.ndarray, w2: np.ndarray) -> float:
    a = 2.0 * w.astype(np.float64) - 1.0
    b = 2.0 * w2.astype(np.float64) - 1.0
    return float((a * b).sum() / (np.linalg.norm(a) * np.linalg.norm(b)))


def ber(w: np.ndarray, w2: np.ndarray) -> float:
    return float((w != w2).mean())
