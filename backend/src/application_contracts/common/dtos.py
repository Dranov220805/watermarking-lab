"""Common API response envelope DTOs matching code_template ResponseInterceptor / HttpExceptionFilter."""
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorResultDto(BaseModel):
    code: Optional[str] = None
    message: str
    details: Optional[Any] = None


class ApiResponseDto(BaseModel, Generic[T]):
    status: str
    statusCode: int
    message: str
    error: Optional[ErrorResultDto] = None
    systemName: str
    data: Optional[T] = None
