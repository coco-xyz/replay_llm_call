"""
Test Log Response Schemas

API response models for test log endpoints.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TestLogResponse(BaseModel):
    """Response model for test log data."""

    id: str = Field(..., description="Test log ID")
    test_case_id: str = Field(..., description="Associated test case ID")
    agent_id: str = Field(..., description="Associated agent ID")
    regression_test_id: Optional[str] = Field(
        None, description="Regression test identifier if applicable"
    )
    model_name: str = Field(..., description="Model used for execution")
    model_settings: Optional[Dict] = Field(
        None, description="Model settings JSON used for execution"
    )
    system_prompt: str = Field(..., description="System prompt used")
    user_message: str = Field(..., description="User message used")
    tools: Optional[List[Dict]] = Field(None, description="Tools configuration used")
    llm_response: Optional[str] = Field(None, description="LLM response text")
    response_example: Optional[str] = Field(
        None, description="Response example captured with the log"
    )
    response_example_vector: Optional[List[float]] = Field(
        None, description="Embedding captured from the response example"
    )
    response_expectation_snapshot: Optional[str] = Field(
        None, description="Acceptance criteria captured when the log was created"
    )
    response_time_ms: Optional[int] = Field(
        None, description="Response time in milliseconds"
    )
    similarity_score: float = Field(
        0.0, description="Cosine similarity vs. the test case example"
    )
    is_passed: bool = Field(
        False, description="Indicates whether the evaluation marked the log as passed"
    )
    evaluation_feedback: Optional[str] = Field(
        None, description="Summary returned by the evaluation agent"
    )
    evaluation_model_name: Optional[str] = Field(
        None, description="Model used by the evaluation agent"
    )
    evaluation_metadata: Optional[Dict] = Field(
        None, description="Structured payload from the evaluation agent"
    )
    status: str = Field(..., description="Execution status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)
