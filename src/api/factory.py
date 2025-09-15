"""
API Factory

Centralized API setup with middleware, CORS, and monitoring configuration.
"""

from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from src.api.errors import register_exception_handlers
from src.api.middleware import (
    RequestIDMiddleware,
    RequestLoggingMiddleware,
)
from src.api.router import router
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)


def setup_cors(app: FastAPI) -> None:
    """
    Setup CORS middleware with configurable origins.

    Args:
        app: FastAPI application instance
    """
    # Use configured CORS settings from config.py
    cors_origins = settings.cors_allow_origins_list
    cors_credentials = settings.cors__allow_credentials
    cors_methods = settings.cors_allow_methods_list
    cors_headers = settings.cors_allow_headers_list

    # Only add CORS middleware if origins are configured
    if cors_origins and cors_origins != [""]:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=cors_credentials,
            allow_methods=cors_methods,
            allow_headers=cors_headers,
        )
        logger.info("CORS middleware configured:")
        logger.info("  Origins: %s", cors_origins)
        logger.info("  Credentials: %s", cors_credentials)
        logger.info("  Methods: %s", cors_methods)
        logger.info("  Headers: %s", cors_headers)
    else:
        logger.info("CORS middleware skipped (no origins configured)")


def setup_security_middleware(app: FastAPI) -> None:
    """
    Setup security-related middleware.

    Args:
        app: FastAPI application instance
    """
    # Trusted hosts (production safety)
    trusted_hosts = getattr(settings, "trusted_hosts", None)
    if trusted_hosts and not settings.debug:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)
        logger.info("TrustedHost middleware configured with hosts: %s", trusted_hosts)


def setup_compression(app: FastAPI) -> None:
    """
    Setup response compression middleware.

    Args:
        app: FastAPI application instance
    """
    # Enable GZip compression for responses > 1KB
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    logger.info("GZip compression middleware configured")


def setup_logging_middleware(app: FastAPI) -> None:
    """
    Setup request logging and ID middleware.

    Args:
        app: FastAPI application instance
    """
    # Request ID middleware (should be first to ensure all requests have IDs)
    app.add_middleware(RequestIDMiddleware)

    # Request logging middleware
    app.add_middleware(RequestLoggingMiddleware)

    logger.info("Request logging and ID middleware configured")


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Setup global exception handlers.

    Args:
        app: FastAPI application instance
    """
    register_exception_handlers(app)
    logger.info("Global exception handlers configured")


def setup_logfire_instrumentation(app: FastAPI) -> None:
    """
    Setup complete Logfire instrumentation including configuration and all libraries.

    Args:
        app: FastAPI application instance
    """
    try:
        from src.core.logfire_config import initialize_logfire

        results = initialize_logfire(app)

        if results["configured"]:
            logger.info("Logfire initialized successfully")

            # Log instrumentation results
            instrumentation = results["instrumentation"]
            enabled_instruments = [
                name for name, enabled in instrumentation.items() if enabled
            ]
            if enabled_instruments:
                logger.info(
                    "Logfire instrumentation enabled for: %s",
                    ", ".join(enabled_instruments),
                )
            else:
                logger.debug("No Logfire instrumentation enabled")
        else:
            logger.debug("Logfire initialization skipped (disabled or not available)")

    except ImportError:
        logger.debug("Logfire not available for instrumentation")
    except Exception as e:
        logger.warning("Failed to initialize Logfire: %s", e)


def setup_metrics_hooks(app: FastAPI) -> None:
    """
    Setup optional metrics collection hooks.

    Args:
        app: FastAPI application instance
    """
    # Placeholder for metrics integration
    # Can be extended with Prometheus, OpenTelemetry, etc.

    @app.middleware("http")
    async def metrics_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Simple metrics collection middleware."""
        import time

        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # Add processing time header for debugging
        response.headers["X-Process-Time"] = str(process_time)

        # TODO: Send metrics to monitoring system
        # metrics.record_request(
        #     method=request.method,
        #     path=request.url.path,
        #     status_code=response.status_code,
        #     duration=process_time
        # )

        return response

    logger.info("Basic metrics hooks configured")


def create_api(
    title: str = "replay-llm-call API",
    description: str = "API for AI replay-llm-call",
    version: str = "1.0.0",
    docs_url: str = "/docs",
    redoc_url: str = "/redoc",
    enable_cors: bool = True,
    enable_compression: bool = True,
    enable_security: bool = True,
    enable_metrics: bool = True,
    mount_prefix: str = "/api",
) -> FastAPI:
    """
    Create and configure FastAPI application with all middleware.

    Args:
        title: API title
        description: API description
        version: API version
        docs_url: URL path for API documentation (Swagger UI)
        redoc_url: URL path for ReDoc documentation
        enable_cors: Whether to enable CORS middleware
        enable_compression: Whether to enable GZip compression
        enable_security: Whether to enable security middleware
        enable_metrics: Whether to enable metrics collection
        mount_prefix: Prefix for mounting the API router

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        docs_url=docs_url,
        redoc_url=redoc_url,
        debug=settings.debug,
    )

    # Setup middleware in reverse order (last added = first executed)

    if enable_metrics:
        setup_metrics_hooks(app)

    if enable_compression:
        setup_compression(app)

    if enable_cors:
        setup_cors(app)

    if enable_security:
        setup_security_middleware(app)

    # Logging middleware should be early in the chain
    setup_logging_middleware(app)

    # Exception handlers
    setup_exception_handlers(app)

    # Logfire instrumentation (should be after middleware setup)
    setup_logfire_instrumentation(app)

    # Mount API router
    app.include_router(router, prefix=mount_prefix)

    logger.info("API factory created: %s v%s", title, version)
    return app


def mount_api(
    app: FastAPI,
    prefix: str = "/api",
    enable_cors: bool = True,
    enable_compression: bool = True,
    enable_security: bool = True,
    enable_metrics: bool = True,
) -> None:
    """
    Mount API components to an existing FastAPI app.

    Args:
        app: Existing FastAPI application
        prefix: Prefix for mounting the API router
        enable_cors: Whether to enable CORS middleware
        enable_compression: Whether to enable GZip compression
        enable_security: Whether to enable security middleware
        enable_metrics: Whether to enable metrics collection
    """
    # Setup middleware
    if enable_metrics:
        setup_metrics_hooks(app)

    if enable_compression:
        setup_compression(app)

    if enable_cors:
        setup_cors(app)

    if enable_security:
        setup_security_middleware(app)

    setup_logging_middleware(app)
    setup_exception_handlers(app)

    # Logfire instrumentation
    setup_logfire_instrumentation(app)

    # Mount router
    app.include_router(router, prefix=prefix)

    logger.info("API components mounted to existing app with prefix: %s", prefix)
