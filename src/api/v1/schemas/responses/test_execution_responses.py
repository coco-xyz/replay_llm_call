"""
Test Execution Response Schemas

API response models for test execution endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TestExecutionResponse(BaseModel):
    """Response model for test execution results."""

    status: str = Field(..., description="Execution status (success/failed)")
    log_id: Optional[str] = Field(
        None, description="Test log ID if execution completed"
    )
    agent_id: Optional[str] = Field(None, description="Agent used for execution")
    regression_test_id: Optional[str] = Field(
        None, description="Regression test context for the execution"
    )
    response_time_ms: Optional[int] = Field(
        None, description="Response time in milliseconds"
    )
    executed_at: Optional[datetime] = Field(None, description="Execution timestamp")
    error_message: Optional[str] = Field(
        None, description="Error message if execution failed"
    )
    llm_response: Optional[str] = Field(None, description="LLM response text")
    similarity_score: Optional[float] = Field(None, description="Similarity score between response and example")
    is_passed: Optional[bool] = Field(None, description="Whether the test passed based on similarity threshold")

    # Legacy fields for backward compatibility
    test_log: Optional[dict] = Field(None, description="Legacy test log data")
    error: Optional[str] = Field(None, description="Legacy error field")
