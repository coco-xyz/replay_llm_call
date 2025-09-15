"""
API Error Handling

FastAPI-specific error handling and response schemas.
"""

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from .exception_handlers import global_exception_handler


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers for the FastAPI application.

    This provides a single entry point for exception handling registration,
    ensuring consistent error responses across all exception types.

    Args:
        app: FastAPI application instance
    """
    # Register handlers for all exception types
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(HTTPException, global_exception_handler)
    app.add_exception_handler(RequestValidationError, global_exception_handler)


__all__ = ["global_exception_handler", "register_exception_handlers"]
