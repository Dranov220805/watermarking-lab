"""Backward-compatible facade re-exporting logo builder functions from the Domain layer."""
from src.domain.services.logo_builder import (
    T,
    build,
    from_text,
    from_upload,
    standard,
    to_png,
)

__all__ = ["T", "standard", "from_upload", "from_text", "build", "to_png"]
