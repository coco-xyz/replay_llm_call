"""
V1 API Request Schemas

Request schemas for all API v1 endpoints.
"""

from .test_case_requests import TestCaseCreateRequest, TestCaseUpdateRequest
from .test_execution_requests import TestExecutionRequest

__all__ = [
    "TestCaseCreateRequest",
    "TestCaseUpdateRequest",
    "TestExecutionRequest"
]
