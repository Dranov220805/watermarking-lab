"""Repository interface for image asset persistence (DDD Domain layer contract)."""
from abc import ABC, abstractmethod
from typing import Optional

from ..entities.image_asset import ImageAssetEntity


class IImageRepository(ABC):
    @abstractmethod
    def save(
        self,
        data: bytes,
        ext: str,
        name: str,
        width: int,
        height: int,
        fmt: str,
    ) -> ImageAssetEntity:
        """Persist image bytes and return the created domain entity."""

    @abstractmethod
    def get_by_id(self, image_id: str) -> Optional[ImageAssetEntity]:
        """Find an image asset by its identifier, or return None if missing/expired."""

    @abstractmethod
    def read_bytes(self, entity: ImageAssetEntity) -> bytes:
        """Read the raw bytes for a stored image asset."""

    @abstractmethod
    def cleanup_expired(self, cutoff_timestamp: float) -> int:
        """Remove image assets created before cutoff_timestamp; return count removed."""
