"""Composition root / FastAPI dependency injection providers."""
from src.application.watermark import ImageService, WatermarkService
from src.domain.repositories.image_repository import IImageRepository
from src.infrastructure.config import get_settings
from src.infrastructure.storage import LocalImageRepository

_settings = get_settings()
_image_repository = LocalImageRepository(
    store_dir=_settings.storage_dir,
    ttl_seconds=_settings.storage_ttl_seconds,
    cleanup_interval_seconds=_settings.cleanup_interval_seconds,
)
_image_service = ImageService(
    image_repository=_image_repository,
    max_upload_bytes=_settings.max_upload_bytes,
)
_watermark_service = WatermarkService(
    image_repository=_image_repository,
    image_service=_image_service,
    max_null_trials=_settings.max_null_trials,
)


def get_image_repository() -> IImageRepository:
    return _image_repository


def get_local_image_repository() -> LocalImageRepository:
    return _image_repository


def get_image_service() -> ImageService:
    return _image_service


def get_watermark_service() -> WatermarkService:
    return _watermark_service
