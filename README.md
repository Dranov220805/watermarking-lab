# DCT Watermarking Lab

Python algorithm (backend/) + Next.js interface (frontend/).

## Run
    # 1) backend
    cd backend && pip install -r requirements.txt
    # 2) frontend
    cd ../frontend && npm install
    # 3) both together
    npm run dev:all          # UI on http://localhost:3000, Python API on :8000
    # production: npm run build && npm run start:all

If the API runs elsewhere: `WM_API_URL=http://host:8000 npm run dev`.

## What you can do in the UI
Upload PNG/JPEG/WebP/BMP/GIF/TIFF -> choose standard, uploaded or text logo (binarised to 64x64)
-> embed (DCT robust or LSB baseline) -> attack (crop, noise, JPEG) -> extract
(search mode with reference logo for cropped images, aligned mode with key only for uncropped images).

## Limits
No resize/rotation support; crop needs >= 4096 blocks (~512x512 px) for one copy of every logo bit;
Q~30 JPEG destroys the logo at alpha=25; key permutation is numpy PCG64 seeded from SHA-256 (demo grade).
