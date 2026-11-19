"""Shared enumerations for WM.WatermarkService."""
from enum import Enum


class WatermarkMethod(str, Enum):
    DCT = "dct"
    LSB = "lsb"


class ExtractMode(str, Enum):
    SEARCH = "search"
    ALIGNED = "aligned"


class LogoSource(str, Enum):
    STANDARD = "standard"
    UPLOAD = "upload"
    TEXT = "text"


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    IMAGE_NOT_FOUND = "IMAGE_NOT_FOUND"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_IMAGE = "INVALID_IMAGE"
    IMAGE_TOO_SMALL = "IMAGE_TOO_SMALL"
    INVALID_SECRET_KEY = "INVALID_SECRET_KEY"
    INVALID_METHOD = "INVALID_METHOD"
    INVALID_ALPHA = "INVALID_ALPHA"
    INVALID_MODE = "INVALID_MODE"
    INVALID_CROP = "INVALID_CROP"
    INVALID_JPEG_QUALITY = "INVALID_JPEG_QUALITY"
    LOGO_ERROR = "LOGO_ERROR"
    EMPTY_LOGO = "EMPTY_LOGO"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
