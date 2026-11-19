"""LocalImageRepository — concrete IImageRepository storing image files on local disk with TTL cleanup."""
import logging
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from src.domain.entities.image_asset import ImageAssetEntity
from src.domain.repositories.image_repository import IImageRepository
from src.domain_shared.consts import (
    BLOCK_SIZE,
    CLEANUP_INTERVAL_SECONDS,
    MIN_BLOCKS,
    TTL_SECONDS,
)

logger = logging.getLogger(__name__)


class LocalImageRepository(IImageRepository):
    def __init__(
        self,
        store_dir: Optional[str] = None,
        ttl_seconds: int = TTL_SECONDS,
        cleanup_interval_seconds: int = CLEANUP_INTERVAL_SECONDS,
    ) -> None:
        resolved = store_dir or os.environ.get("WM_STORE") or tempfile.mkdtemp(prefix="wmstore_")
        self._store = Path(resolved)
        self._store.mkdir(parents=True, exist_ok=True)
        self._ttl_seconds = ttl_seconds
        self._cleanup_interval = cleanup_interval_seconds
        self._records: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._cleanup_thread: Optional[threading.Thread] = None

    @staticmethod
    def _map_to_entity(record: dict) -> ImageAssetEntity:
        """Map internal storage record to Domain ImageAssetEntity."""
        return ImageAssetEntity(
            id=record["id"],
            path=record["path"],
            ext=record["ext"],
            name=record["name"],
            width=record["width"],
            height=record["height"],
            format=record["format"],
            bytes=record["bytes"],
            blocks=record["blocks"],
            copies=record["copies"],
            created_at=record["created_at"],
        )

    def start_cleanup(self) -> None:
        if self._cleanup_thread is not None and self._cleanup_thread.is_alive():
            return
        self._stop_event.clear()
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.info("LocalImageRepository initialized at %s", self._store)

    def stop_cleanup(self) -> None:
        self._stop_event.set()

    def _cleanup_loop(self) -> None:
        while not self._stop_event.wait(self._cleanup_interval):
            removed = self.cleanup_expired(time.time() - self._ttl_seconds)
            if removed:
                logger.info("Cleaned up %d expired image(s)", removed)

    def save(
        self,
        data: bytes,
        ext: str,
        name: str,
        width: int,
        height: int,
        fmt: str,
    ) -> ImageAssetEntity:
        image_id = uuid.uuid4().hex
        path = self._store / f"{image_id}.{ext}"
        path.write_bytes(data)
        blocks = (height // BLOCK_SIZE) * (width // BLOCK_SIZE)
        record = {
            "id": image_id,
            "path": str(path),
            "ext": ext,
            "name": name,
            "width": width,
            "height": height,
            "format": fmt,
            "bytes": len(data),
            "blocks": blocks,
            "copies": blocks / MIN_BLOCKS,
            "created_at": time.time(),
        }
        with self._lock:
            self._records[image_id] = record
        return self._map_to_entity(record)

    def get_by_id(self, image_id: str) -> Optional[ImageAssetEntity]:
        with self._lock:
            record = self._records.get(image_id)
        return self._map_to_entity(record) if record is not None else None

    def read_bytes(self, entity: ImageAssetEntity) -> bytes:
        return Path(entity.path).read_bytes()

    def cleanup_expired(self, cutoff_timestamp: float) -> int:
        removed = 0
        with self._lock:
            expired_ids = [
                key for key, rec in self._records.items() if rec["created_at"] < cutoff_timestamp
            ]
            for key in expired_ids:
                try:
                    os.remove(self._records[key]["path"])
                except OSError:
                    pass
                del self._records[key]
                removed += 1
        return removed
