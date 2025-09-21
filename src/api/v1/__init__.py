"""
API Version 1 Package

Version 1 of the replay-llm-call API endpoints.
"""

from fastapi import APIRouter

from .endpoints import health_router
from .endpoints.agents import router as agents_router
from .endpoints.regression_tests import router as regression_tests_router
from .endpoints.test_cases import router as test_cases_router
from .endpoints.test_execution import router as test_execution_router
from .endpoints.test_logs import router as test_logs_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(agents_router)
router.include_router(test_cases_router)
router.include_router(test_execution_router)
router.include_router(test_logs_router)
router.include_router(regression_tests_router)

__all__ = ["router"]
