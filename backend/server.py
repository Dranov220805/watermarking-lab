"""FastAPI entry point for WM.WatermarkService.

Run with .env settings:
    python server.py
Or via uvicorn directly:
    uvicorn server:app --port 8000
"""
from src.http_api.app import app, create_app
from src.infrastructure.config import get_settings

__all__ = ["app", "create_app"]


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "server:app",
        host=settings.app_host,
        port=settings.app_port,
    )
