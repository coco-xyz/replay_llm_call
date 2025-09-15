"""
API Version 1 Package

Version 1 of the replay-llm-call API endpoints.
"""

from fastapi import APIRouter

from .endpoints import demo_router, health_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(demo_router, prefix="/demo", tags=["demo"])

__all__ = ["router"]
