"""ImageController — upload, preview, and download endpoints under /api/v1/images."""
from fastapi import APIRouter, Depends, File, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from src.application.watermark import ImageService
from src.http_api.dependencies import get_image_service
from src.http_api.interceptors import success_response
from src.infrastructure.config import get_settings

_settings = get_settings()
router = APIRouter(prefix=f"{_settings.api_base_path}/images", tags=["Images"])


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    image_service: ImageService = Depends(get_image_service),
) -> JSONResponse:
    data = file.file.read(_settings.max_upload_bytes + 1)
    result = await image_service.upload_async(data=data, filename=file.filename)
    return success_response(result.model_dump())


@router.get("/{image_id}/preview")
async def preview_image(
    image_id: str,
    max: int = 900,
    image_service: ImageService = Depends(get_image_service),
) -> Response:
    jpeg_bytes = await image_service.get_preview_async(image_id=image_id, max_width=max)
    return Response(
        content=jpeg_bytes,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/{image_id}/download")
async def download_image(
    image_id: str,
    image_service: ImageService = Depends(get_image_service),
) -> FileResponse:
    info = await image_service.get_download_info_async(image_id=image_id)
    return FileResponse(
        path=info.path,
        media_type=info.media_type,
        filename=info.filename,
    )
