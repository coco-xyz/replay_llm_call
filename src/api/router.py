"""
FastAPI router for the replay-llm-call API.

This module defines the main FastAPI router, including the version 1 router.
"""

from fastapi import APIRouter

from src.api.pages import router as pages_router
from src.api.v1 import router as v1_router

router = APIRouter()
router.include_router(pages_router)  # Pages at root level
router.include_router(v1_router, prefix="/v1")

__all__ = ["router"]
