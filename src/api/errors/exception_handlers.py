"""
Exception Handlers

Dedicated module for FastAPI-bound exception handling.
"""

import traceback

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.api.schemas.error import ErrorDetail, ErrorResponse
from src.core.error_codes import APIErrorCode, ValidationErrorCode
from src.core.exceptions import ApplicationException
from src.core.logger import get_logger

logger = get_logger(__name__)


def _log_exception(request: Request, exc: Exception, status_code: int) -> None:
    """Log exception with appropriate level based on status code."""
    msg = "Unhandled exception in %s %s: %s"
    args = (request.method, request.url.path, str(exc))

    if status_code >= 500:
        logger.error(msg, *args, exc_info=True)
    elif status_code >= 400:
        logger.warning(msg, *args)
    else:
        logger.info(msg, *args)


def _build_response(
    error: ErrorDetail, request: Request, status_code: int
) -> JSONResponse:
    """Build standardized error response."""
    request_id = getattr(request.state, "request_id", None)

    payload = ErrorResponse(
        error=error,
        request_id=request_id,
        path=request.url.path,
        method=request.method,
    )

    # Add X-Request-ID header for better traceability
    headers = {}
    if request_id:
        headers["X-Request-ID"] = request_id

    return JSONResponse(
        status_code=status_code, content=payload.model_dump(), headers=headers
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for all unhandled exceptions.

    Args:
        request: FastAPI request object
        exc: Exception that was raised

    Returns:
        JSONResponse with standardized error format
    """
    # We'll log after determining the status code for appropriate log level

    # Custom application exceptions
    if isinstance(exc, ApplicationException):
        status_code = exc.http_status  # Use the new http_status property
        _log_exception(request, exc, status_code)

        # Use the enhanced to_dict() method
        exc_dict = exc.to_dict()
        error = ErrorDetail(
            type=exc.__class__.__name__,
            message=exc_dict["message"],
            code=exc_dict["code"],
            details=exc_dict["details"],
            debug=None,
        )
        return _build_response(error, request, status_code)

    # FastAPI HTTP exceptions
    if isinstance(exc, HTTPException):
        _log_exception(request, exc, exc.status_code)
        error = ErrorDetail(
            type="HTTPException",
            message=str(exc.detail),
            code=f"HTTP_{exc.status_code}",
            details=None,
            debug=None,
        )
        return _build_response(error, request, exc.status_code)

    # Validation errors
    if isinstance(exc, RequestValidationError):
        _log_exception(request, exc, 422)
        error = ErrorDetail(
            type="ValidationError",
            message="Request validation failed",
            code=ValidationErrorCode.INVALID_INPUT.value,
            details={"validation_errors": exc.errors()},
            debug=None,
        )
        return _build_response(error, request, 422)

    # All other exceptions
    _log_exception(request, exc, 500)
    error = ErrorDetail(
        type="InternalServerError",
        message="An unexpected error occurred",
        code=APIErrorCode.INTERNAL_ERROR.value,
        details=None,
        debug=None,
    )

    # In debug mode, include more details
    try:
        from src.core.config import settings

        if settings and settings.debug:
            error.debug = {
                "exception_type": exc.__class__.__name__,
                "exception_message": str(exc),
                "traceback": traceback.format_exc(),
            }
    except Exception:
        pass

    return _build_response(error, request, 500)
