"""
FastAPI Middleware

Simple middleware for request logging.
"""

import time
import uuid
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logger import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Simple middleware to log API requests and responses.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process request and log basic information.

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain

        Returns:
            Response: HTTP response
        """

        start_time = time.time()
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        request_id = getattr(request.state, "request_id", "unknown")

        # Log request start (debug level)
        logger.debug("Request: %s %s from %s [%s]", method, path, client_ip, request_id)

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Log request completion
            if response.status_code >= 500:
                logger.error(
                    "%s %s - %d (%.3fs) [%s]",
                    method,
                    path,
                    response.status_code,
                    duration,
                    request_id,
                )
            elif response.status_code >= 400:
                logger.warning(
                    "%s %s - %d (%.3fs) [%s]",
                    method,
                    path,
                    response.status_code,
                    duration,
                    request_id,
                )
            else:
                logger.info(
                    "%s %s - %d (%.3fs) [%s]",
                    method,
                    path,
                    response.status_code,
                    duration,
                    request_id,
                )

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Request failed: %s %s - %s (%.3fs) [%s]",
                method,
                path,
                str(e),
                duration,
                request_id,
                exc_info=True,
            )
            raise


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle request ID generation and propagation.

    Reads X-Request-ID from request headers or generates a new UUID.
    Stores the request ID in request.state.request_id and adds it to response headers.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process request and ensure request ID is available.

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain

        Returns:
            Response: HTTP response with X-Request-ID header
        """
        # Get request ID from header or generate new one
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in request state for use by handlers and logging
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers for traceability
        response.headers["X-Request-ID"] = request_id

        return response
