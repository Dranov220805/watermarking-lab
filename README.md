# DCT Watermarking Lab

Python algorithm (`backend/`) + Next.js interface (`frontend/`).

## Configure with `.env`
Both services include `.env.example` templates:
- **Backend**: edit `backend/.env` or `backend/.env.local` (see `backend/.env.example`) to configure `APP_HOST`, `APP_PORT`, `APP_TITLE`, `CORS_ORIGINS`, `STORAGE_DIR`, `STORAGE_TTL_SECONDS`, `CLEANUP_INTERVAL_SECONDS`, `MAX_UPLOAD_MB`, and watermark defaults (`DEFAULT_ALPHA`, `DEFAULT_NULL_TRIALS`, `MAX_NULL_TRIALS`).
- **Frontend**: edit `frontend/.env.local` (see `frontend/.env.example`) to configure `API_PROXY_TARGET`, `PROXY_TIMEOUT_MS`, `MAX_BODY_SIZE`, `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_APP_TITLE`, `NEXT_PUBLIC_DEFAULT_ALPHA`, `NEXT_PUBLIC_DEFAULT_SECRET_KEY`, `NEXT_PUBLIC_DEFAULT_METHOD`, and `NEXT_PUBLIC_REQUEST_TIMEOUT_MS`.

## Run
    # Quick start (Windows — creates backend/.venv, installs deps, activates .venv, runs npm run start:all):
    .\start.ps1              # or start.bat  (pass -Dev / --dev for dev mode)

    # Or manually:
    # 1) backend
    cd backend && python -m venv .venv && .\.venv\Scripts\Activate.ps1 && pip install -r requirements.txt
    # 2) frontend (in the same activated .venv terminal)
    cd ../frontend && npm install && npm run build
    # 3) both together
    npm run start:all        # UI on http://localhost:3000, Python API on APP_HOST:APP_PORT
    # dev mode: npm run dev:all

## What you can do in the UI
Upload PNG/JPEG/WebP/BMP/GIF/TIFF -> choose standard, uploaded or text logo (binarised to 64x64)
-> embed (DCT robust or LSB baseline) -> attack (crop, overwrite attack, noise, JPEG) -> extract
(search mode with reference logo for cropped images, aligned mode with key only for uncropped images).

## Limits
No resize/rotation support; crop needs >= 4096 blocks (~512x512 px) for one copy of every logo bit;
Q~30 JPEG destroys the logo at alpha=25; key permutation is numpy PCG64 seeded from SHA-256 (demo grade).
