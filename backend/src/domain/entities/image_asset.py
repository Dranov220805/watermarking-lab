"""Domain entity representing an uploaded or generated image asset."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ImageAssetEntity:
    id: str
    path: str
    ext: str
    name: str
    width: int
    height: int
    format: str
    bytes: int
    blocks: int
    copies: float
    created_at: float

    @property
    def base_name(self) -> str:
        return Path(self.name).stem or "image"
