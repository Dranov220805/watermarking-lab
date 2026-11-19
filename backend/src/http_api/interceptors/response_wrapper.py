"""ResponseInterceptor equivalent — wraps successful JSON payloads in the standard ApiResponse envelope."""
from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from src.infrastructure.config import get_settings


def success_response(
    data: Any,
    status_code: int = 200,
    message: str = "Operation completed successfully.",
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "success",
            "statusCode": status_code,
            "message": message,
            "error": None,
            "systemName": get_settings().system_name,
            "data": jsonable_encoder(data),
        },
    )
