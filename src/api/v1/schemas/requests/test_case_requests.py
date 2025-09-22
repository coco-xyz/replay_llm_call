"""
Test Case Request Schemas

API request models for test case endpoints.
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class TestCaseCreateRequest(BaseModel):
    """Request model for creating a new test case."""

    name: str = Field(..., min_length=1, max_length=255, description="Test case name")
    raw_data: Dict = Field(..., description="Raw logfire data")
    description: Optional[str] = Field(
        None, max_length=1000, description="Test case description"
    )
    agent_id: str = Field(..., description="Agent that owns the new test case")
    response_example: Optional[str] = Field(
        None,
        description="Example LLM response for this test case",
    )


class TestCaseUpdateRequest(BaseModel):
    """Request model for updating a test case."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Updated test case name"
    )
    raw_data: Optional[Dict] = Field(None, description="Updated raw logfire data")
    description: Optional[str] = Field(
        None, max_length=1000, description="Updated test case description"
    )
    system_prompt: Optional[str] = Field(None, description="Updated system prompt")
    last_user_message: Optional[str] = Field(None, description="Updated user message")
    agent_id: Optional[str] = Field(None, description="Updated owning agent")
    response_example: Optional[str] = Field(
        None, description="Updated example LLM response"
    )
