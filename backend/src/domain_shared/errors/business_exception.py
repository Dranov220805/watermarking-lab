"""Structured domain/application exception following the code_template BusinessException pattern.

Caught by the global exception handler in http_api/filters/exception_handlers.py to produce a
consistent JSON error envelope. Always construct via static factory methods.
"""
from typing import Any, Optional

from ..enums import ErrorCode


class BusinessException(Exception):
    def __init__(self, code: ErrorCode, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    @staticmethod
    def image_not_found() -> "BusinessException":
        return BusinessException(
            ErrorCode.IMAGE_NOT_FOUND,
            "Image not found or expired; please upload it again.",
        )

    @staticmethod
    def file_too_large(max_mb: int = 100) -> "BusinessException":
        return BusinessException(
            ErrorCode.FILE_TOO_LARGE,
            f"File too large (limit {max_mb} MB).",
        )

    @staticmethod
    def invalid_image(reason: str) -> "BusinessException":
        return BusinessException(
            ErrorCode.INVALID_IMAGE,
            f"Cannot read this file as an image ({reason}). Try PNG, JPEG, WebP, BMP, GIF or TIFF.",
        )

    @staticmethod
    def decode_failed(reason: str) -> "BusinessException":
        return BusinessException(
            ErrorCode.INVALID_IMAGE,
            f"Cannot decode image: {reason}",
        )

    @staticmethod
    def image_too_small(blocks: int, min_blocks: int) -> "BusinessException":
        return BusinessException(
            ErrorCode.IMAGE_TOO_SMALL,
            f"Image too small: {blocks} blocks, need at least {min_blocks} (about 512x512 px).",
        )

    @staticmethod
    def image_has_no_blocks() -> "BusinessException":
        return BusinessException(
            ErrorCode.IMAGE_TOO_SMALL,
            "Image is too small.",
        )

    @staticmethod
    def invalid_secret_key() -> "BusinessException":
        return BusinessException(
            ErrorCode.INVALID_SECRET_KEY,
            "Secret key is empty.",
        )

    @staticmethod
    def invalid_method() -> "BusinessException":
        return BusinessException(
            ErrorCode.INVALID_METHOD,
            "Method must be 'dct' or 'lsb'.",
        )

    @staticmethod
    def invalid_alpha(min_alpha: float = 5.0, max_alpha: float = 100.0) -> "BusinessException":
        return BusinessException(
            ErrorCode.INVALID_ALPHA,
            f"Alpha must be between {min_alpha:g} and {max_alpha:g}.",
        )

    @staticmethod
    def invalid_mode() -> "BusinessException":
        return BusinessException(
            ErrorCode.INVALID_MODE,
            "Mode must be 'search' or 'aligned'.",
        )

    @staticmethod
    def invalid_crop(width: int, height: int) -> "BusinessException":
        return BusinessException(
            ErrorCode.INVALID_CROP,
            f"Crop must stay inside the image ({width}x{height}) and be at least 8x8.",
        )

    @staticmethod
    def invalid_jpeg_quality() -> "BusinessException":
        return BusinessException(
            ErrorCode.INVALID_JPEG_QUALITY,
            "JPEG quality must be between 1 and 100.",
        )

    @staticmethod
    def logo_error(reason: str) -> "BusinessException":
        return BusinessException(
            ErrorCode.LOGO_ERROR,
            f"Logo error: {reason}",
        )

    @staticmethod
    def empty_logo() -> "BusinessException":
        return BusinessException(
            ErrorCode.EMPTY_LOGO,
            "Logo is nearly empty; adjust the threshold or choose another logo.",
        )

    @staticmethod
    def internal_error(message: str = "Internal server error.") -> "BusinessException":
        return BusinessException(ErrorCode.INTERNAL_SERVER_ERROR, message)
