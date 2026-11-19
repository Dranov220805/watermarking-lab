"""Shared constants across all layers of WM.WatermarkService."""

SYSTEM_NAME = "WM.WatermarkService"
API_PREFIX = "/api"
API_VERSION = "v1"

# Watermarking algorithm constants
BLOCK_SIZE = 8
DCT_COEFF_P = (3, 4)
DCT_COEFF_Q = (4, 3)
TILE_SIZE = 64
MIN_BLOCKS = TILE_SIZE * TILE_SIZE
DEFAULT_ALPHA = 25.0
MIN_ALPHA = 5.0
MAX_ALPHA = 100.0
SEARCH_SIDE = 2048
MIN_LOGO_INK_PIXELS = 20
MAX_SSIM_PIXELS = 12_000_000
MAX_IMAGE_PIXELS = 64_000_000
MAX_NULL_TRIALS = 200

# Storage & upload limits
TTL_SECONDS = 2 * 3600
CLEANUP_INTERVAL_SECONDS = 600
MAX_UPLOAD_BYTES = 100 * 1024 * 1024

FORMAT_TO_EXT: dict[str, str] = {
    "JPEG": "jpg",
    "PNG": "png",
    "WEBP": "webp",
    "BMP": "bmp",
    "GIF": "gif",
    "TIFF": "tif",
}

EXT_TO_MEDIA_TYPE: dict[str, str] = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "webp": "image/webp",
    "bmp": "image/bmp",
    "gif": "image/gif",
    "tif": "image/tiff",
}
