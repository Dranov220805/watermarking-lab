#!/usr/bin/env python3
"""
DCT-domain image watermarking CLI & backward-compatible domain facade.

Core algorithms live in `src.domain.services.dct_engine`.

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
import os
import sys
import time

import cv2
import numpy as np

from src.domain.services.dct_engine import (  # noqa: F401
    B,
    D,
    DEFAULT_ALPHA,
    P,
    Q,
    SEARCH_SIDE,
    TILE,
    attack_crop,
    attack_jpeg,
    attack_noise,
    ber,
    best_alignment,
    dct_blocks,
    decode_image,
    embed_dct,
    embed_lsb,
    extract,
    extract_aligned,
    fold,
    from_blocks,
    grid_folds,
    idct_blocks,
    keyed_perm,
    make_logo,
    make_tile,
    nc,
    psnr,
    search_region,
    soft_values,
    ssim_y,
    structure_baseline,
    structure_score,
    tile_signs,
    to_blocks,
    untile,
    xcorr_peak,
)


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

    diff = np.abs(marked["dct"].astype(np.int16) - img.astype(np.int16)).max(axis=2)
    cv2.imwrite(os.path.join(args.out, "diff_dct_x10.png"), np.clip(diff * 10, 0, 255).astype(np.uint8))

    rng = np.random.default_rng(7)
    attacks = [("none", lambda im: im)]
    for q in (90, 70, 50, 30):
        attacks.append((f"JPEG Q={q}", lambda im, q=q: attack_jpeg(im, q)))
    attacks.append(("noise s=3", lambda im: attack_noise(im, 3.0)))
    for side in (2048, 1024, 640, 512, 384):
        side_h, side_w = min(side, h), min(side, w)
        cy = int(rng.integers(0, h - side_h + 1)) | 3
        cx = int(rng.integers(0, w - side_w + 1)) | 5
        cy, cx = min(cy, h - side_h), min(cx, w - side_w)
        nb = (side_h // B) * (side_w // B)
        attacks.append((f"crop {side_w}x{side_h} (~{nb} blk)",
                        lambda im, cy=cy, cx=cx, hh=side_h, ww=side_w: attack_crop(im, cy, cx, hh, ww)))
        if side in (1024, 640):
            attacks.append((f"crop {side_w}x{side_h} + JPEG70",
                            lambda im, cy=cy, cx=cx, hh=side_h, ww=side_w:
                            attack_jpeg(attack_crop(im, cy, cx, hh, ww), 70)))

    print("estimating null distribution (wrong keys / unwatermarked) ...")
    y_wm = cv2.cvtColor(marked["dct"], cv2.COLOR_BGR2YCrCb)[..., 0]
    folds_wm = grid_folds(y_wm, "dct", alpha)
    null_wrong = [best_alignment(folds_wm, tile_signs(logo, f"wrong-key-{i}"))[0] for i in range(args.null_keys)]
    y_orig = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)[..., 0]
    folds_orig = grid_folds(y_orig, "dct", alpha)
    null_unmarked = [best_alignment(folds_orig, tile_signs(logo, key))[0]]
    for i in range(args.null_keys // 4):
        null_unmarked.append(best_alignment(folds_orig, tile_signs(logo, f"other-{i}"))[0])
    null_all = np.array(null_wrong + null_unmarked)
    thr = float(null_all.mean() + 6 * null_all.std())
    print(f"null score: mean={null_all.mean():.4f} std={null_all.std():.4f} max={null_all.max():.4f}  threshold(mean+6sd)={thr:.4f}")

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

    r_wrong = extract(attacks[3][1](marked["dct"]), logo, "WRONG-KEY", "dct", alpha)

    with open(os.path.join(args.out, "results.csv"), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)

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
    with open(os.path.join(args.out, "results.md"), "w") as f:
        f.write("\n".join(md) + "\n")

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
