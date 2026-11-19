"""ImageService — handles image upload, preview generation, download lookup, and decoding."""
import io
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from src.application_contracts.watermark.dtos import (
    ImageAssetOutputDto,
    ImageDownloadOutputDto,
)
from src.domain.entities.image_asset import ImageAssetEntity
from src.domain.repositories.image_repository import IImageRepository
from src.domain.services import dct_engine
from src.domain_shared.consts import (
    EXT_TO_MEDIA_TYPE,
    FORMAT_TO_EXT,
    MAX_UPLOAD_BYTES,
)
from src.domain_shared.errors import BusinessException


class ImageService:
    def __init__(
        self,
        image_repository: IImageRepository,
        max_upload_bytes: int = MAX_UPLOAD_BYTES,
    ) -> None:
        self._image_repository = image_repository
        self._max_upload_bytes = max_upload_bytes

    @staticmethod
    def to_output_dto(entity: ImageAssetEntity) -> ImageAssetOutputDto:
        return ImageAssetOutputDto(
            id=entity.id,
            name=entity.name,
            width=entity.width,
            height=entity.height,
            format=entity.format,
            bytes=entity.bytes,
            blocks=entity.blocks,
            copies=entity.copies,
        )

    def get_entity_or_throw(self, image_id: str) -> ImageAssetEntity:
        entity = self._image_repository.get_by_id(image_id)
        if entity is None:
            raise BusinessException.image_not_found()
        return entity

    def load_bgr_image(self, entity: ImageAssetEntity) -> np.ndarray:
        try:
            raw = self._image_repository.read_bytes(entity)
            return dct_engine.decode_image(raw)
        except Exception as exc:  # noqa: BLE001
            raise BusinessException.decode_failed(str(exc)) from exc

    async def upload_async(self, data: bytes, filename: Optional[str]) -> ImageAssetOutputDto:
        if len(data) > self._max_upload_bytes:
            raise BusinessException.file_too_large(self._max_upload_bytes // (1024 * 1024))
        try:
            im = Image.open(io.BytesIO(data))
            fmt = (im.format or "IMG").upper()
            bgr = dct_engine.decode_image(data)
        except Exception as exc:  # noqa: BLE001
            raise BusinessException.invalid_image(str(exc)) from exc

        ext = FORMAT_TO_EXT.get(fmt, "bin")
        safe_name = filename or f"image.{ext}"
        entity = self._image_repository.save(
            data=data,
            ext=ext,
            name=safe_name,
            width=int(bgr.shape[1]),
            height=int(bgr.shape[0]),
            fmt=fmt,
        )
        return self.to_output_dto(entity)

    async def get_preview_async(self, image_id: str, max_width: int = 900) -> bytes:
        entity = self.get_entity_or_throw(image_id)
        img = self.load_bgr_image(entity)
        scale = min(1.0, max_width / img.shape[1]) if max_width > 0 else 1.0
        if scale < 1.0:
            img = cv2.resize(
                img,
                (max(1, int(img.shape[1] * scale)), max(1, int(img.shape[0] * scale))),
                interpolation=cv2.INTER_AREA,
            )
        return dct_engine.encode_jpeg(img, quality=88)

    async def get_download_info_async(self, image_id: str) -> ImageDownloadOutputDto:
        entity = self.get_entity_or_throw(image_id)
        media_type = EXT_TO_MEDIA_TYPE.get(entity.ext, "application/octet-stream")
        return ImageDownloadOutputDto(
            path=entity.path,
            media_type=media_type,
            filename=entity.name,
        )
