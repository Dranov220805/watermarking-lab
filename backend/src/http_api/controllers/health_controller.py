"""HealthController — GET /api/v1/health."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.application.watermark import WatermarkService
from src.http_api.dependencies import get_watermark_service
from src.http_api.interceptors import success_response
from src.infrastructure.config import get_settings

router = APIRouter(prefix=get_settings().api_base_path, tags=["Health"])


@router.get("/health")
async def get_health(
    watermark_service: WatermarkService = Depends(get_watermark_service),
) -> JSONResponse:
    result = await watermark_service.get_health_async()
    return success_response(result.model_dump())
