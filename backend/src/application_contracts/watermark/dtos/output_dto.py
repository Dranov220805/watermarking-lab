"""Output DTOs for watermarking operations."""
from typing import Optional

from pydantic import BaseModel


class HealthOutputDto(BaseModel):
    ok: bool
    cv2: str
    numpy: str


class ImageAssetOutputDto(BaseModel):
    id: str
    name: str
    width: int
    height: int
    format: str
    bytes: int
    blocks: int
    copies: float


class ImageDownloadOutputDto(BaseModel):
    path: str
    media_type: str
    filename: str


class LogoPreviewOutputDto(BaseModel):
    png_bytes: bytes
    ink_pixels: int


class EmbedOutputDto(ImageAssetOutputDto):
    psnr: Optional[float] = None
    ssim: Optional[float] = None
    seconds: float


class AttackOutputDto(ImageAssetOutputDto):
    desc: str


class ExtractOutputDto(BaseModel):
    mode: str
    blocks: int
    copies: float
    structure: Optional[float] = None
    structure_baseline: Optional[float] = None
    logo_png: str
    seconds: float
    nc: Optional[float] = None
    ber: Optional[float] = None
    score: Optional[float] = None
    threshold: Optional[float] = None
    null_mean: Optional[float] = None
    null_max: Optional[float] = None
    detected: Optional[bool] = None
    offset: Optional[list[int]] = None
    phase: Optional[list[int]] = None
