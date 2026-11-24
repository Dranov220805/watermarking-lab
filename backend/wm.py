#!/usr/bin/env python3
"""
DCT-domain image watermarking demo (Computer Security midterm project).

Implements the pseudocode from the report:
  EMBED   : one bit per 8x8 block, forced margin between DCT coefficients
            p=(3,4) and q=(4,3), logo tiled over blocks, keyed permutation.
  EXTRACT : search 8x8 grid offset, then tile phase (FFT cross-correlation
            with the reference tile), soft-vote, inverse permutation.
  BASELINE: LSB embedding with the SAME payload, tiling, voting and search.

Usage:
  python wm.py demo                          # full experiment on a test mosaic
  python wm.py demo --image photo.jpg        # full experiment on your image
  python wm.py sweep                         # alpha vs PSNR/SSIM/JPEG robustness
  python wm.py embed   in.png out.png --key K --alpha 30 [--logo logo.png]
  python wm.py attack  out.png atk.png --jpeg 50 | --crop Y X H W
  python wm.py extract atk.png --key K --alpha 30 [--logo logo.png] [--save rec.png]
"""
import argparse
import csv
import glob
import hashlib
import os
import sys
import time

import cv2
import numpy as np
from skimage.metrics import structural_similarity

B = 8                 # block size (JPEG)
P = (3, 4)            # coefficient p
Q = (4, 3)            # coefficient q
TILE = 64             # logo is 64x64 bits
DEFAULT_ALPHA = 25.0
SEARCH_SIDE = 2048    # max side (px) of the region used for grid/phase search


# --------------------------------------------------------------------------
# DCT helpers (orthonormal 8x8 DCT-II == JPEG DCT)
# --------------------------------------------------------------------------
def _dct_matrix(n=B):
    k = np.arange(n)[:, None]
    x = np.arange(n)[None, :]
    d = np.sqrt(2.0 / n) * np.cos((2 * x + 1) * k * np.pi / (2 * n))
    d[0, :] = np.sqrt(1.0 / n)
    return d


D = _dct_matrix()


def to_blocks(y, oy=0, ox=0):
    """Return (hb, wb, 8, 8) view of full blocks starting at pixel (oy, ox)."""
    h, w = y.shape
    hb, wb = (h - oy) // B, (w - ox) // B
    a = y[oy:oy + hb * B, ox:ox + wb * B]
    return a.reshape(hb, B, wb, B).transpose(0, 2, 1, 3), hb, wb


def from_blocks(blk):
    hb, wb = blk.shape[:2]
    return blk.transpose(0, 2, 1, 3).reshape(hb * B, wb * B)


def dct_blocks(blk):
    return D @ blk @ D.T


def idct_blocks(c):
    return D.T @ c @ D


# --------------------------------------------------------------------------
# Logo + keyed permutation
# --------------------------------------------------------------------------
def make_logo(path=None):
    """64x64 binary logo (0/1). Default: ring with letter 'C' and 'WM'."""
    if path:
        im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if im is None:
            sys.exit(f"cannot read logo: {path}")
        im = cv2.resize(im, (TILE, TILE), interpolation=cv2.INTER_AREA)
        return (im > 127).astype(np.uint8)
    im = np.zeros((TILE, TILE), np.uint8)
    cv2.circle(im, (32, 32), 29, 255, 3)
    cv2.putText(im, "C", (17, 44), cv2.FONT_HERSHEY_SIMPLEX, 1.5, 255, 3, cv2.LINE_AA)
    cv2.putText(im, "WM", (19, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.45, 255, 1, cv2.LINE_AA)
    return (im > 127).astype(np.uint8)


def keyed_perm(key, n=TILE * TILE):
    """Key-dependent permutation. NOTE: numpy PCG64 seeded from SHA-256(key) is
    fine for a demo but is not a cryptographic PRNG (see report, Section 7)."""
    seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")
    return np.random.default_rng(seed).permutation(n)


def make_tile(logo, key):
    """logo (0/1, 64x64) -> scrambled tile (0/1, 64x64)."""
    perm = keyed_perm(key)
    flat = logo.reshape(-1)
    tile = np.empty_like(flat)
    tile[perm] = flat
    return tile.reshape(TILE, TILE)


def untile(tile_bits, key):
    perm = keyed_perm(key)
    return tile_bits.reshape(-1)[perm].reshape(TILE, TILE)


def tile_signs(logo, key):
    return 2.0 * make_tile(logo, key).astype(np.float64) - 1.0


# --------------------------------------------------------------------------
# Embedding
# --------------------------------------------------------------------------
def embed_dct(img_bgr, logo, key, alpha=DEFAULT_ALPHA):
    ycc = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
    y = ycc[..., 0].astype(np.float64)
    blk, hb, wb = to_blocks(y)
    c = dct_blocks(blk)
    s_tile = tile_signs(logo, key)
    S = s_tile[np.ix_(np.arange(hb) % TILE, np.arange(wb) % TILE)]
    d = c[:, :, P[0], P[1]] - c[:, :, Q[0], Q[1]]
    deficit = np.maximum(alpha - S * d, 0.0)      # enforce margin only if needed
    shift = 0.5 * deficit * S
    c[:, :, P[0], P[1]] += shift
    c[:, :, Q[0], Q[1]] -= shift
    y2 = y.copy()
    y2[:hb * B, :wb * B] = from_blocks(idct_blocks(c))
    ycc[..., 0] = np.clip(np.rint(y2), 0, 255).astype(np.uint8)
    return cv2.cvtColor(ycc, cv2.COLOR_YCrCb2BGR)


def embed_lsb(img_bgr, logo, key, alpha=None):
    """Baseline: same tiled/keyed payload, one bit per block, stored in the LSB
    of the top-left luminance pixel of each 8x8 block."""
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
def soft_values(y, oy, ox, method, alpha):
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


def fold(v):
    """Sum soft values into a 64x64 tile by block index modulo 64."""
    hb, wb = v.shape
    vp = np.pad(v, ((0, (-hb) % TILE), (0, (-wb) % TILE)))
    return vp.reshape(vp.shape[0] // TILE, TILE, vp.shape[1] // TILE, TILE).sum((0, 2))


def xcorr_peak(F, S):
    """Circular cross-correlation g[t] = sum_a F[a] S[a+t] of MEAN-CENTRED tiles
    (centring removes the baseline caused by unbalanced ink/background logos);
    return best shift and normalised score."""
    F = F - F.mean()
    S = S - S.mean()
    g = np.fft.ifft2(np.conj(np.fft.fft2(F)) * np.fft.fft2(S)).real
    ti, tj = np.unravel_index(np.argmax(g), g.shape)
    denom = np.linalg.norm(F) * np.linalg.norm(S)
    return (int(ti), int(tj)), (g[ti, tj] / denom if denom > 0 else 0.0)


def search_region(y):
    h, w = y.shape
    sh, sw = min(h, SEARCH_SIDE), min(w, SEARCH_SIDE)
    y0, x0 = (h - sh) // 2, (w - sw) // 2
    return y[y0:y0 + sh, x0:x0 + sw], y0, x0


def grid_folds(y, method, alpha):
    """Pre-compute folded votes for all 64 grid offsets on the search region."""
    ys, _, _ = search_region(y)
    ys = ys.astype(np.float64)
    out = {}
    for oy in range(B):
        for ox in range(B):
            out[(oy, ox)] = fold(soft_values(ys, oy, ox, method, alpha))
    return out


def best_alignment(folds, S):
    best = (-1.0, None, None)
    for off, F in folds.items():
        shift, score = xcorr_peak(F, S)
        if score > best[0]:
            best = (score, off, shift)
    return best  # score, (oy, ox), (ti, tj)


def structure_score(bits):
    """Fraction of adjacent (h/v) equal pixels in a 64x64 bit image."""
    b = np.asarray(bits, np.uint8)
    eq = (b[:, :-1] == b[:, 1:]).sum() + (b[:-1, :] == b[1:, :]).sum()
    return float(eq) / (b[:, :-1].size + b[:-1, :].size)


def structure_baseline(bits):
    """Expected structure_score of a random scramble of the same pixels."""
    p = float(np.asarray(bits).mean())
    return p * p + (1 - p) * (1 - p)


def extract(img_bgr, logo_ref, key, method="dct", alpha=DEFAULT_ALPHA, null_trials=0):
    """Hypothesis-guided extraction: the verifier supplies key + reference logo
    (needed to resolve grid offset and tile phase after cropping).
    null_trials > 0 also estimates the false-positive level with wrong keys."""
    y = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)[..., 0]
    S = tile_signs(logo_ref, key)
    folds = grid_folds(y, method, alpha)
    score, (oy_r, ox_r), _ = best_alignment(folds, S)
    # offsets were found inside the search region: map back to full-image pixel grid
    _, ry0, rx0 = search_region(y)
    oy, ox = (oy_r + ry0) % B, (ox_r + rx0) % B
    # full-image votes at best grid offset, then re-estimate phase on full fold
    F = fold(soft_values(y.astype(np.float64), oy, ox, method, alpha))
    (ti, tj), _ = xcorr_peak(F, S)
    F_al = np.roll(F, (ti, tj), axis=(0, 1))
    tile_bits = (F_al > 0).astype(np.uint8)
    logo_est = untile(tile_bits, key)
    out = dict(logo=logo_est, score=float(score), offset=(ox, oy), shift=(ti, tj),
               structure=structure_score(logo_est), structure_baseline=structure_baseline(logo_est))
    if null_trials:
        nulls = np.array([best_alignment(folds, tile_signs(logo_ref, f"{key}#null{k}"))[0]
                          for k in range(null_trials)])
        thr = float(nulls.mean() + 6 * nulls.std())
        out.update(null_mean=float(nulls.mean()), null_max=float(nulls.max()),
                   threshold=thr, detected=bool(score > thr))
    return out


def extract_aligned(img_bgr, key, method="dct", alpha=DEFAULT_ALPHA):
    """Key-only extraction for an UNCROPPED image: grid offset (0,0), tile phase 0."""
    y = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)[..., 0].astype(np.float64)
    F = fold(soft_values(y, 0, 0, method, alpha))
    logo = untile((F > 0).astype(np.uint8), key)
    return dict(logo=logo, structure=structure_score(logo), structure_baseline=structure_baseline(logo))


def decode_image(data):
    """Decode PNG/JPEG/WebP/BMP/GIF/TIFF bytes -> BGR uint8. EXIF orientation is
    applied; transparency is flattened onto white."""
    import io
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS = 64_000_000
    im = Image.open(io.BytesIO(data))
    im.load()
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im)
    rgb = np.asarray(im.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


# --------------------------------------------------------------------------
# Attacks
# --------------------------------------------------------------------------
def attack_jpeg(img, q):
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, int(q)])
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


def attack_crop(img, y, x, h, w):
    return img[y:y + h, x:x + w].copy()


def attack_noise(img, sigma, seed=0):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, sigma, img.shape)
    return np.clip(img.astype(np.float64) + n, 0, 255).astype(np.uint8)


def attack_overwrite(img_bgr, alpha=DEFAULT_ALPHA, seed=0):
    """Attacker knows the DCT embedding rule and alpha: re-embeds independent
    random bits in every 8x8 block to erase the owner's watermark."""
    ycc = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
    y = ycc[..., 0].astype(np.float64)
    blk, hb, wb = to_blocks(y)
    c = dct_blocks(blk)
    rng = np.random.default_rng(seed)
    S = 2.0 * rng.integers(0, 2, size=(hb, wb)).astype(np.float64) - 1.0
    d = c[:, :, P[0], P[1]] - c[:, :, Q[0], Q[1]]
    deficit = np.maximum(alpha - S * d, 0.0)
    shift = 0.5 * deficit * S
    c[:, :, P[0], P[1]] += shift
    c[:, :, Q[0], Q[1]] -= shift
    y2 = y.copy()
    y2[:hb * B, :wb * B] = from_blocks(idct_blocks(c))
    ycc[..., 0] = np.clip(np.rint(y2), 0, 255).astype(np.uint8)
    return cv2.cvtColor(ycc, cv2.COLOR_YCrCb2BGR)


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------
def psnr(a, b):
    return float(cv2.PSNR(a, b))


def ssim_y(a, b):
    ya = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
    yb = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)
    return float(structural_similarity(ya, yb, data_range=255))


def nc(w, w2):
    a = 2.0 * w.astype(np.float64) - 1.0
    b = 2.0 * w2.astype(np.float64) - 1.0
    return float((a * b).sum() / (np.linalg.norm(a) * np.linalg.norm(b)))


def ber(w, w2):
    return float((w != w2).mean())


# --------------------------------------------------------------------------
# Test image: mosaic of real photos at native resolution (no upscaling)
# --------------------------------------------------------------------------
def make_mosaic(h=2000, w=3000, seed=1, sample_dir=None):
    sample_dir = sample_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
    files = sorted(glob.glob(os.path.join(sample_dir, "*.jpg")))
    if not files:
        sys.exit("no sample photos found; pass --image yourphoto.jpg")
    imgs = [cv2.imread(f) for f in files]
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w, 3), np.uint8)
    t = 250
    for y in range(0, h, t):
        for x in range(0, w, t):
            im = imgs[rng.integers(len(imgs))]
            iy = rng.integers(0, im.shape[0] - t + 1)
            ix = rng.integers(0, im.shape[1] - t + 1)
            tile = im[iy:iy + t, ix:ix + t]
            if rng.random() < 0.5:
                tile = tile[:, ::-1]
            hh, ww = min(t, h - y), min(t, w - x)
            out[y:y + hh, x:x + ww] = tile[:hh, :ww]
    return out


# --------------------------------------------------------------------------
# Demo experiment
# --------------------------------------------------------------------------
def label(img, text):
    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) if img.ndim == 2 else img.copy()
    cv2.rectangle(img, (0, 0), (img.shape[1], 14), (255, 255, 255), -1)
    cv2.putText(img, text, (2, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 0, 0), 1, cv2.LINE_AA)
    return img


def logo_thumb(bits, text, scale=3):
    g = (bits * 255).astype(np.uint8)
    g = cv2.resize(g, (TILE * scale, TILE * scale), interpolation=cv2.INTER_NEAREST)
    g = cv2.copyMakeBorder(g, 0, 0, 0, 0, cv2.BORDER_CONSTANT)
    return label(g, text)


def run_demo(args):
    t0 = time.time()
    os.makedirs(args.out, exist_ok=True)
    key, alpha = args.key, args.alpha
    logo = make_logo(args.logo)

    if args.image:
        img = cv2.imread(args.image)
        if img is None:
            sys.exit(f"cannot read image: {args.image}")
    else:
        img = make_mosaic(args.height, args.width)
    h, w = img.shape[:2]
    hb, wb = h // B, w // B
    print(f"image {w}x{h}  blocks {wb}x{hb}  copies per logo bit ~ {hb * wb / (TILE * TILE):.1f}")
    cv2.imwrite(os.path.join(args.out, "original.png"), img)

    methods = {"dct": embed_dct, "lsb": embed_lsb}
    marked = {m: f(img, logo, key, alpha) for m, f in methods.items()}
    for m, im in marked.items():
        cv2.imwrite(os.path.join(args.out, f"watermarked_{m}.png"), im)

    # amplified difference map (DCT)
    diff = np.abs(marked["dct"].astype(np.int16) - img.astype(np.int16)).max(axis=2)
    cv2.imwrite(os.path.join(args.out, "diff_dct_x10.png"), np.clip(diff * 10, 0, 255).astype(np.uint8))

    # ---- attack list ----
    rng = np.random.default_rng(7)
    attacks = [("none", lambda im: im)]
    for q in (90, 70, 50, 30):
        attacks.append((f"JPEG Q={q}", lambda im, q=q: attack_jpeg(im, q)))
    attacks.append(("noise s=3", lambda im: attack_noise(im, 3.0)))
    for side in (2048, 1024, 640, 512, 384):
        side_h, side_w = min(side, h), min(side, w)
        cy = int(rng.integers(0, h - side_h + 1)) | 3   # unaligned on purpose
        cx = int(rng.integers(0, w - side_w + 1)) | 5
        cy, cx = min(cy, h - side_h), min(cx, w - side_w)
        nb = (side_h // B) * (side_w // B)
        attacks.append((f"crop {side_w}x{side_h} (~{nb} blk)",
                        lambda im, cy=cy, cx=cx, hh=side_h, ww=side_w: attack_crop(im, cy, cx, hh, ww)))
        if side in (1024, 640):
            attacks.append((f"crop {side_w}x{side_h} + JPEG70",
                            lambda im, cy=cy, cx=cx, hh=side_h, ww=side_w:
                            attack_jpeg(attack_crop(im, cy, cx, hh, ww), 70)))

    # ---- null distribution (false positives) for DCT detector ----
    print("estimating null distribution (wrong keys / unwatermarked) ...")
    y_wm = cv2.cvtColor(marked["dct"], cv2.COLOR_BGR2YCrCb)[..., 0]
    folds_wm = grid_folds(y_wm, "dct", alpha)
    null_wrong = []
    for i in range(args.null_keys):
        S_wrong = tile_signs(logo, f"wrong-key-{i}")
        null_wrong.append(best_alignment(folds_wm, S_wrong)[0])
    y_orig = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)[..., 0]
    folds_orig = grid_folds(y_orig, "dct", alpha)
    S_true = tile_signs(logo, key)
    null_unmarked = [best_alignment(folds_orig, S_true)[0]]
    for i in range(args.null_keys // 4):
        null_unmarked.append(best_alignment(folds_orig, tile_signs(logo, f"other-{i}"))[0])
    null_all = np.array(null_wrong + null_unmarked)
    thr = float(null_all.mean() + 6 * null_all.std())
    print(f"null score: mean={null_all.mean():.4f} std={null_all.std():.4f} max={null_all.max():.4f}  threshold(mean+6sd)={thr:.4f}")

    # ---- run ----
    rows, thumbs = [], {"dct": [], "lsb": []}
    for name, atk in attacks:
        for m in ("dct", "lsb"):
            atk_img = atk(marked[m])
            r = extract(atk_img, logo, key, m, alpha)
            rows.append(dict(
                attack=name, method=m,
                PSNR_wm=psnr(img, marked[m]) if name == "none" else "",
                SSIM_wm=ssim_y(img, marked[m]) if name == "none" else "",
                NC=nc(logo, r["logo"]), BER=ber(logo, r["logo"]),
                score=r["score"], detected=r["score"] > thr,
                grid=f"{r['offset']}", phase=f"{r['shift']}"))
            thumbs[m].append(logo_thumb(r["logo"], f"{name} NC={rows[-1]['NC']:.2f}"))
        print(f"  done: {name}")

    # wrong-key extraction example (on JPEG Q=90) and overwrite attack
    r_wrong = extract(attacks[1][1](marked["dct"]), logo, "WRONG-KEY", "dct", alpha)
    ow_img = attack_overwrite(marked["dct"], alpha=alpha, seed=42)
    ow_psnr = psnr(marked["dct"], ow_img)
    r_ow = extract(ow_img, logo, key, "dct", alpha)

    # ---- outputs ----
    with open(os.path.join(args.out, "results.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)

    def fmt(v, p=3):
        return f"{v:.{p}f}" if isinstance(v, float) else str(v)
    md = [f"# Results  (alpha={alpha}, key='{key}', image {w}x{h}, ~{hb * wb / 4096:.1f} copies/bit)\n",
          f"Null-score threshold (mean+6sd over {len(null_all)} trials): {thr:.4f}  (null max {null_all.max():.4f})\n",
          "| Attack | Method | NC | BER | score | detected | grid(x,y) | phase |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['attack']} | {r['method']} | {r['NC']:.3f} | {r['BER']:.3f} | {r['score']:.3f} | "
                  f"{'yes' if r['detected'] else 'no'} | {r['grid']} | {r['phase']} |")
    p0 = [r for r in rows if r["attack"] == "none"]
    md.append("\nImage quality of watermarked image vs original:\n")
    for r in p0:
        md.append(f"- {r['method']}: PSNR = {r['PSNR_wm']:.2f} dB, SSIM = {r['SSIM_wm']:.4f}")
    md.append(f"\nWrong key on JPEG Q=90 image: NC = {nc(logo, r_wrong['logo']):.3f}, "
              f"BER = {ber(logo, r_wrong['logo']):.3f}, score = {r_wrong['score']:.4f}")
    md.append(f"\nOverwrite attack (random bits, alpha={alpha:g}): PSNR vs watermarked = {ow_psnr:.2f} dB, "
              f"NC = {nc(logo, r_ow['logo']):.3f}, BER = {ber(logo, r_ow['logo']):.3f}, "
              f"score = {r_ow['score']:.4f}, detected = {'yes' if r_ow['score'] > thr else 'no'}")
    with open(os.path.join(args.out, "results.md"), "w") as f:
        f.write("\n".join(md) + "\n")

    # figure: extracted logos
    def grid(imgs, cols=5):
        hh, ww = imgs[0].shape[:2]
        rows_ = [imgs[i:i + cols] for i in range(0, len(imgs), cols)]
        rows_ = [r + [np.full((hh, ww, 3), 255, np.uint8)] * (cols - len(r)) for r in rows_]
        return np.vstack([np.hstack(r) for r in rows_])
    ref = logo_thumb(logo, "original logo")
    cv2.imwrite(os.path.join(args.out, "extracted_dct.png"), grid([ref] + thumbs["dct"]))
    cv2.imwrite(os.path.join(args.out, "extracted_lsb.png"), grid([ref] + thumbs["lsb"]))
    print(f"\nwrote results to {args.out}/  ({time.time() - t0:.0f}s)")
    print("\n".join(md))



def run_sweep(args):
    """Trade-off table: embedding strength alpha vs quality and JPEG robustness."""
    os.makedirs(args.out, exist_ok=True)
    logo = make_logo(args.logo)
    img = cv2.imread(args.image) if args.image else make_mosaic(args.height, args.width)
    qs = (90, 70, 50, 30)
    lines = ["| alpha | PSNR (dB) | SSIM | " + " | ".join(f"BER Q={q}" for q in qs) + " | " +
             " | ".join(f"NC Q={q}" for q in qs) + " |",
             "|" + "---|" * (3 + 2 * len(qs))]
    for alpha in args.alphas:
        m = embed_dct(img, logo, args.key, alpha)
        bers, ncs = [], []
        for q in qs:
            r = extract(attack_jpeg(m, q), logo, args.key, "dct", alpha)
            bers.append(f"{ber(logo, r['logo']):.3f}")
            ncs.append(f"{nc(logo, r['logo']):.3f}")
        lines.append(f"| {alpha:g} | {psnr(img, m):.2f} | {ssim_y(img, m):.4f} | " + " | ".join(bers) + " | " + " | ".join(ncs) + " |")
        print(lines[-1])
    with open(os.path.join(args.out, "sweep.md"), "w") as f:
        f.write("\n".join(lines) + "\n")

# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--key", default="demo-secret-key")
        p.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
        p.add_argument("--logo", default=None, help="logo image (default: built-in)")

    e = sub.add_parser("embed"); e.add_argument("inp"); e.add_argument("out"); common(e)
    e.add_argument("--method", choices=["dct", "lsb"], default="dct")
    a = sub.add_parser("attack"); a.add_argument("inp"); a.add_argument("out")
    a.add_argument("--jpeg", type=int); a.add_argument("--crop", type=int, nargs=4, metavar=("Y", "X", "H", "W"))
    a.add_argument("--overwrite", action="store_true"); a.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    a.add_argument("--noise", type=float)
    x = sub.add_parser("extract"); x.add_argument("inp"); common(x)
    x.add_argument("--method", choices=["dct", "lsb"], default="dct")
    x.add_argument("--save", default=None, help="save extracted logo PNG")
    x.add_argument("--aligned", action="store_true", help="key-only extraction for an uncropped image")
    x.add_argument("--null-trials", type=int, default=40)
    d = sub.add_parser("demo"); common(d)
    d.add_argument("--image", default=None); d.add_argument("--out", default="results")
    d.add_argument("--width", type=int, default=3000); d.add_argument("--height", type=int, default=2000)
    d.add_argument("--null-keys", type=int, default=100)
    sw = sub.add_parser("sweep"); common(sw)
    sw.add_argument("--image", default=None); sw.add_argument("--out", default="results")
    sw.add_argument("--width", type=int, default=3000); sw.add_argument("--height", type=int, default=2000)
    sw.add_argument("--alphas", type=float, nargs="+", default=[15, 20, 25, 30, 40, 50, 60])
    args = ap.parse_args()

    if args.cmd == "embed":
        img = decode_image(open(args.inp, "rb").read())
        f = embed_dct if args.method == "dct" else embed_lsb
        out = f(img, make_logo(args.logo), args.key, args.alpha)
        cv2.imwrite(args.out, out)
        print(f"saved {args.out}  PSNR={psnr(img, out):.2f} dB  SSIM={ssim_y(img, out):.4f}")
    elif args.cmd == "attack":
        img = cv2.imread(args.inp)
        if args.crop:
            img = attack_crop(img, *args.crop)
        if args.overwrite:
            img = attack_overwrite(img, alpha=args.alpha)
        if args.noise:
            img = attack_noise(img, args.noise)
        if args.jpeg:
            img = attack_jpeg(img, args.jpeg)
        cv2.imwrite(args.out, img)
        print(f"saved {args.out} ({img.shape[1]}x{img.shape[0]})")
    elif args.cmd == "extract":
        img = decode_image(open(args.inp, "rb").read())
        if args.aligned:
            r = extract_aligned(img, args.key, args.method, args.alpha)
            print(f"structure={r['structure']:.3f} (random scramble ~{r['structure_baseline']:.3f})")
        else:
            logo = make_logo(args.logo)
            r = extract(img, logo, args.key, args.method, args.alpha, null_trials=args.null_trials)
            print(f"NC={nc(logo, r['logo']):.3f}  BER={ber(logo, r['logo']):.3f}  score={r['score']:.4f}  "
                  f"grid(x,y)={r['offset']}  phase={r['shift']}"
                  + (f"  threshold={r['threshold']:.4f} detected={r['detected']}" if "threshold" in r else ""))
        if args.save:
            cv2.imwrite(args.save, r["logo"] * 255)
    elif args.cmd == "sweep":
        run_sweep(args)
    else:
        run_demo(args)


if __name__ == "__main__":
    main()
