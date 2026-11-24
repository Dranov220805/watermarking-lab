# Backend (Python)

All algorithm work lives here.

    wm.py        core: embed_dct / embed_lsb, extract (search, grid+phase), extract_aligned, attacks (crop, overwrite, noise, JPEG), metrics, CLI
    logos.py     64x64 binary watermark from standard logo / uploaded image / text
    config.py    .env / .env.local settings loader (APP_HOST, APP_PORT, CORS_ORIGINS, storage, defaults)
    server.py    FastAPI wrapper used by the Next.js UI (Swagger UI at /docs)
    test_api.py  end-to-end API test (35 checks; auto-generates test images if no dir is given)

## Install and run
    pip install -r requirements.txt
    python server.py                          # reads APP_HOST/APP_PORT from .env
    # or: python -m uvicorn server:app --port 8000

## CLI (no UI)
    python wm.py demo                         # full experiment on a mosaic of real photos
    python wm.py sweep                        # alpha vs PSNR/SSIM/JPEG robustness
    python wm.py embed in.jpg out.png --key K --alpha 25 [--logo logo.png]
    python wm.py attack out.png atk.png --crop Y X H W --overwrite --alpha 25 --jpeg 60
    python wm.py extract atk.png --key K [--logo logo.png | --aligned]

API: POST /api/upload, /api/logo/preview, /api/embed, /api/attack, /api/extract;
GET /api/image/{id}/preview|download, /api/health; Swagger UI at /docs.
Uploads live in a temp folder for 2 hours (configurable via STORAGE_TTL_SECONDS in .env).
