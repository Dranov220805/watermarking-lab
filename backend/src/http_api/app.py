"""FastAPI application factory for WM.WatermarkService."""
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.http_api.controllers import health_router, image_router, watermark_router
from src.http_api.dependencies import get_local_image_repository
from src.http_api.filters import register_exception_handlers
from src.infrastructure.config import get_settings


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    repo = get_local_image_repository()
    repo.start_cleanup()
    try:
        yield
    finally:
        repo.stop_cleanup()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=f"{settings.system_name} API",
        version="1.0.0",
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Ink-Pixels"],
    )

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(image_router)
    app.include_router(watermark_router)

    return app


app = create_app()
