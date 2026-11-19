# Backend (Python / FastAPI — 6-Layer DDD)

All watermarking algorithm work and HTTP endpoints live here, structured after `code_template`:

    src/
      domain_shared/         constants, enums, BusinessException (zero external deps)
      domain/                ImageAssetEntity, IImageRepository, dct_engine, logo_builder
      application_contracts/ Pydantic input/output DTOs & ApiResponseDto envelope
      application/           ImageService, WatermarkService (*_async use cases)
      infrastructure/        LocalImageRepository (disk storage + TTL cleanup)
      http_api/              versioned FastAPI controllers, exception handlers, response wrapper, DI
    server.py                FastAPI entry point (`uvicorn server:app --port 8000`)
    wm.py                    CLI (`demo`, `sweep`, `embed`, `attack`, `extract`) + domain facade
    logos.py                 Backward-compatible logo builder facade
    test_ddd_backend.py      Unit test suite (`python -m unittest test_ddd_backend.py -v`)
    test_api.py              End-to-end API test (`python test_api.py <cover_dir>`)

## Install and run
    pip install -r requirements.txt
    python -m uvicorn server:app --port 8000

## CLI (no UI)
    python wm.py demo                       # full experiment on a mosaic of real photos
    python wm.py sweep                      # alpha vs PSNR/SSIM/JPEG robustness
    python wm.py embed in.jpg out.png --key K --alpha 25 [--logo logo.png]
    python wm.py attack out.png atk.png --crop Y X H W --jpeg 60
    python wm.py extract atk.png --key K [--logo logo.png | --aligned]

## API (`/api/v1/*`)
All JSON endpoints return the standard `{ status, statusCode, message, error, systemName, data }` envelope:
- `GET /api/v1/health`
- `POST /api/v1/images/upload`
- `GET /api/v1/images/{image_id}/preview`
- `GET /api/v1/images/{image_id}/download`
- `POST /api/v1/watermark/logo/preview`
- `POST /api/v1/watermark/embed`
- `POST /api/v1/watermark/attack`
- `POST /api/v1/watermark/extract`
