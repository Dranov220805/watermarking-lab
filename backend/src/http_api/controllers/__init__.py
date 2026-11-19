from .health_controller import router as health_router
from .image_controller import router as image_router
from .watermark_controller import router as watermark_router

__all__ = ["health_router", "image_router", "watermark_router"]
