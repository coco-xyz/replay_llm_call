"""
V1 API Request Schemas

Request schemas for all API v1 endpoints.
"""

from .agent_requests import AgentCreateRequest, AgentUpdateRequest
from .regression_test_requests import RegressionTestCreateRequest
from .test_case_requests import TestCaseCreateRequest, TestCaseUpdateRequest
from .test_execution_requests import TestExecutionRequest

__all__ = [
    "AgentCreateRequest",
    "AgentUpdateRequest",
    "TestCaseCreateRequest",
    "TestCaseUpdateRequest",
    "TestExecutionRequest",
    "RegressionTestCreateRequest",
]
