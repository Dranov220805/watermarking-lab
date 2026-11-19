"""Input DTOs for watermarking operations."""
from typing import Optional

from pydantic import BaseModel, ConfigDict

from src.domain_shared.consts import DEFAULT_ALPHA


class LogoSpecInputDto(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    source: str = "standard"
    text: str = ""
    threshold: int = 128
    invert: bool = False
    file_bytes: Optional[bytes] = None


class LogoPreviewInputDto(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    logo: LogoSpecInputDto
    scale: int = 2


class EmbedInputDto(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    image_id: str
    key: str
    alpha: float = DEFAULT_ALPHA
    method: str = "dct"
    logo: LogoSpecInputDto


class AttackInputDto(BaseModel):
    image_id: str
    crop_x: Optional[int] = None
    crop_y: Optional[int] = None
    crop_w: Optional[int] = None
    crop_h: Optional[int] = None
    noise_sigma: float = 0.0
    jpeg_quality: int = 0


class ExtractInputDto(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    image_id: str
    key: str
    alpha: float = DEFAULT_ALPHA
    method: str = "dct"
    mode: str = "search"
    null_trials: int = 40
    logo: LogoSpecInputDto
