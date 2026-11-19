"""WatermarkController — logo preview, embed, attack, and extract endpoints under /api/v1/watermark."""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from fastapi.responses import JSONResponse

from src.application.watermark import WatermarkService
from src.application_contracts.watermark.dtos import (
    AttackInputDto,
    EmbedInputDto,
    ExtractInputDto,
    LogoPreviewInputDto,
    LogoSpecInputDto,
)
from src.http_api.dependencies import get_watermark_service
from src.http_api.interceptors import success_response
from src.infrastructure.config import get_settings

_settings = get_settings()
router = APIRouter(prefix=f"{_settings.api_base_path}/watermark", tags=["Watermark"])


def _build_logo_spec_dto(
    logo_source: str,
    logo_text: str,
    logo_threshold: int,
    logo_invert: bool,
    logo_file: Optional[UploadFile],
) -> LogoSpecInputDto:
    file_bytes = logo_file.file.read() if logo_file is not None else None
    return LogoSpecInputDto(
        source=logo_source,
        text=logo_text,
        threshold=logo_threshold,
        invert=logo_invert,
        file_bytes=file_bytes,
    )


@router.post("/logo/preview")
async def preview_logo(
    logo_source: str = Form("standard"),
    logo_text: str = Form(""),
    logo_threshold: int = Form(128),
    logo_invert: bool = Form(False),
    scale: int = Form(2),
    logo_file: Optional[UploadFile] = File(None),
    watermark_service: WatermarkService = Depends(get_watermark_service),
) -> Response:
    input_dto = LogoPreviewInputDto(
        logo=_build_logo_spec_dto(logo_source, logo_text, logo_threshold, logo_invert, logo_file),
        scale=scale,
    )
    result = await watermark_service.build_logo_preview_async(input_dto)
    return Response(
        content=result.png_bytes,
        media_type="image/png",
        headers={"X-Ink-Pixels": str(result.ink_pixels)},
    )


@router.post("/embed")
async def embed_watermark(
    image_id: str = Form(...),
    key: str = Form(...),
    alpha: float = Form(_settings.default_alpha),
    method: str = Form("dct"),
    logo_source: str = Form("standard"),
    logo_text: str = Form(""),
    logo_threshold: int = Form(128),
    logo_invert: bool = Form(False),
    logo_file: Optional[UploadFile] = File(None),
    watermark_service: WatermarkService = Depends(get_watermark_service),
) -> JSONResponse:
    input_dto = EmbedInputDto(
        image_id=image_id,
        key=key,
        alpha=alpha,
        method=method,
        logo=_build_logo_spec_dto(logo_source, logo_text, logo_threshold, logo_invert, logo_file),
    )
    result = await watermark_service.embed_async(input_dto)
    return success_response(result.model_dump())


@router.post("/attack")
async def attack_image(
    image_id: str = Form(...),
    crop_x: Optional[int] = Form(None),
    crop_y: Optional[int] = Form(None),
    crop_w: Optional[int] = Form(None),
    crop_h: Optional[int] = Form(None),
    noise_sigma: float = Form(0.0),
    jpeg_quality: int = Form(0),
    watermark_service: WatermarkService = Depends(get_watermark_service),
) -> JSONResponse:
    input_dto = AttackInputDto(
        image_id=image_id,
        crop_x=crop_x,
        crop_y=crop_y,
        crop_w=crop_w,
        crop_h=crop_h,
        noise_sigma=noise_sigma,
        jpeg_quality=jpeg_quality,
    )
    result = await watermark_service.attack_async(input_dto)
    return success_response(result.model_dump())


@router.post("/extract")
async def extract_watermark(
    image_id: str = Form(...),
    key: str = Form(...),
    alpha: float = Form(_settings.default_alpha),
    method: str = Form("dct"),
    mode: str = Form("search"),
    null_trials: int = Form(_settings.default_null_trials),
    logo_source: str = Form("standard"),
    logo_text: str = Form(""),
    logo_threshold: int = Form(128),
    logo_invert: bool = Form(False),
    logo_file: Optional[UploadFile] = File(None),
    watermark_service: WatermarkService = Depends(get_watermark_service),
) -> JSONResponse:
    input_dto = ExtractInputDto(
        image_id=image_id,
        key=key,
        alpha=alpha,
        method=method,
        mode=mode,
        null_trials=null_trials,
        logo=_build_logo_spec_dto(logo_source, logo_text, logo_threshold, logo_invert, logo_file),
    )
    result = await watermark_service.extract_async(input_dto)
    return success_response(result.model_dump())
