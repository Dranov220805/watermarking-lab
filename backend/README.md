# Backend (Python)

All algorithm work lives here.

    wm.py      core: embed_dct / embed_lsb, extract (search, grid+phase), extract_aligned, attacks, metrics, CLI
    logos.py   64x64 binary watermark from standard logo / uploaded image / text
    server.py  FastAPI wrapper used by the Next.js UI
    test_api.py  end-to-end API test (python test_api.py <dir with cover.png/jpg/webp/bmp + mylogo.png>)

## Install and run
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8000

## CLI (no UI)
    python wm.py demo                       # full experiment on a mosaic of real photos
    python wm.py sweep                      # alpha vs PSNR/SSIM/JPEG robustness
    python wm.py embed in.jpg out.png --key K --alpha 25 [--logo logo.png]
    python wm.py attack out.png atk.png --crop Y X H W --jpeg 60
    python wm.py extract atk.png --key K [--logo logo.png | --aligned]

API: POST /api/upload, /api/logo/preview, /api/embed, /api/attack, /api/extract;
GET /api/image/{id}/preview|download, /api/health. Uploads live in a temp folder for 2 hours.
