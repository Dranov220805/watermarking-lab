# DCT Watermarking Lab

Python algorithm & 6-layer DDD FastAPI backend (`backend/`) + Next.js interface (`frontend/`).

## Configure with `.env`
Both services include `.env.example` templates:
- **Backend**: edit `backend/.env` or `backend/.env.local` (copied from `backend/.env.example`) to configure `APP_HOST`, `APP_PORT`, `CORS_ORIGINS`, `API_PREFIX`, `API_VERSION`, `STORAGE_DIR`, `STORAGE_TTL_SECONDS`, `MAX_UPLOAD_MB`, and watermark defaults.
- **Frontend**: edit `frontend/.env.local` (copied from `frontend/.env.example`) to configure `API_PROXY_TARGET`, `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_API_PREFIX`, `NEXT_PUBLIC_APP_TITLE`, `NEXT_PUBLIC_REQUEST_TIMEOUT_MS`, and UI defaults.

## Run
    # 1) backend
    cd backend && pip install -r requirements.txt
    # 2) frontend
    cd ../frontend && npm install
    # 3) both together
    npm run dev:all          # UI on http://localhost:3000, Python API on APP_HOST:APP_PORT
    # production: npm run build && npm run start:all

## What you can do in the UI
Upload PNG/JPEG/WebP/BMP/GIF/TIFF -> choose standard, uploaded or text logo (binarised to 64x64)
-> embed (DCT robust or LSB baseline) -> attack (crop, noise, JPEG) -> extract
(search mode with reference logo for cropped images, aligned mode with key only for uncropped images).

## Limits
No resize/rotation support; crop needs >= 4096 blocks (~512x512 px) for one copy of every logo bit;
Q~30 JPEG destroys the logo at alpha=25; key permutation is numpy PCG64 seeded from SHA-256 (demo grade).
