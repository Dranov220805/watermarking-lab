"""HttpExceptionFilter equivalent — maps BusinessException, HTTPException, validation errors,
and unexpected exceptions to the unified error response envelope.
"""
import logging
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.domain_shared.enums import ErrorCode
from src.domain_shared.errors import BusinessException
from src.infrastructure.config import get_settings

logger = logging.getLogger(__name__)

ERROR_CODE_TO_HTTP_STATUS: dict[ErrorCode, int] = {
    ErrorCode.IMAGE_NOT_FOUND: 404,
    ErrorCode.FILE_TOO_LARGE: 413,
    ErrorCode.INVALID_IMAGE: 400,
    ErrorCode.IMAGE_TOO_SMALL: 400,
    ErrorCode.INVALID_SECRET_KEY: 400,
    ErrorCode.INVALID_METHOD: 400,
    ErrorCode.INVALID_ALPHA: 400,
    ErrorCode.INVALID_MODE: 400,
    ErrorCode.INVALID_CROP: 400,
    ErrorCode.INVALID_JPEG_QUALITY: 400,
    ErrorCode.LOGO_ERROR: 400,
    ErrorCode.EMPTY_LOGO: 400,
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.INTERNAL_SERVER_ERROR: 500,
}


def _error_envelope(
    status_code: int,
    message: str,
    code: Optional[str] = None,
    details: Optional[Any] = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "statusCode": status_code,
            "message": message,
            "error": {
                "code": code,
                "message": message,
                "details": details,
            },
            "systemName": get_settings().system_name,
            "data": None,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessException)
    async def business_exception_handler(_request: Request, exc: BusinessException) -> JSONResponse:
        status_code = ERROR_CODE_TO_HTTP_STATUS.get(exc.code, 400)
        return _error_envelope(
            status_code=status_code,
            message=exc.message,
            code=exc.code.value,
            details=exc.details,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return _error_envelope(status_code=exc.status_code, message=message)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        first_msg = errors[0].get("msg", "Validation error.") if errors else "Validation error."
        return _error_envelope(
            status_code=400,
            message=first_msg,
            code=ErrorCode.VALIDATION_ERROR.value,
            details=errors,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return _error_envelope(
            status_code=500,
            message="Internal server error, please try again later.",
            code=ErrorCode.INTERNAL_SERVER_ERROR.value,
        )
