"""
API Health Check Endpoint

Comprehensive health check for the replay-llm-call API.
"""

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter

from src.api.schemas.error import ErrorResponse
from src.api.v1.schemas.responses import HealthResponse
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


async def check_database_health() -> Dict[str, Any]:
    """Check database connection health."""
    try:
        from src.stores.database import test_connection

        status = test_connection()
        return {"status": "healthy", "details": status}
    except ImportError:
        # Database module not available
        return {"status": "disabled", "reason": "Database module not available"}
    except Exception as e:
        logger.warning("Database health check failed: %s", str(e))
        return {"status": "unhealthy", "error": str(e)}


async def check_redis_health() -> Dict[str, Any]:
    """Check Redis connection health."""
    try:
        from src.stores.redis_client import get_redis_client_async

        redis_client = await get_redis_client_async()
        health = await redis_client.health_check()
        return {"status": health.get("status", "unknown"), "details": health}
    except ImportError:
        # Redis module not available
        return {"status": "disabled", "reason": "Redis module not available"}
    except Exception as e:
        logger.warning("Redis health check failed: %s", str(e))
        return {"status": "unhealthy", "error": str(e)}


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="API Health Check",
    description="Check the overall health of the API and its dependencies",
    tags=["health"],
    responses={
        200: {"model": HealthResponse, "description": "Health check results"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
)
async def health_check() -> HealthResponse:
    """
    Comprehensive health check endpoint for the API.

    Checks the status of:
    - API service itself
    - Database connection (if enabled and configured)
    - Redis connection (if enabled and configured)

    Returns:
        HealthResponse: Overall health status and component details
    """
    components = {}
    overall_healthy = True

    # Check database health (only if enabled in configuration)
    if settings.health__check_database:
        try:
            db_health = await check_database_health()
            components["database"] = db_health
            # Only consider it unhealthy if it's actually unhealthy (not disabled)
            if db_health["status"] == "unhealthy":
                overall_healthy = False
        except Exception as e:
            components["database"] = {"status": "error", "error": str(e)}
            overall_healthy = False

    # Check Redis health (only if enabled in configuration)
    if settings.health__check_redis:
        try:
            redis_health = await check_redis_health()
            components["redis"] = redis_health
            # Only consider it unhealthy if it's actually unhealthy (not disabled)
            if redis_health["status"] == "unhealthy":
                overall_healthy = False
        except Exception as e:
            components["redis"] = {"status": "error", "error": str(e)}
            overall_healthy = False

    # API service is healthy if we can respond
    components["api"] = {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.environment,
    }

    return HealthResponse(
        status="healthy" if overall_healthy else "unhealthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        environment=settings.environment,
        components=components,
    )
