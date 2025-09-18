"""
Test Execution Request Schemas

API request models for test execution endpoints.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TestExecutionRequest(BaseModel):
    """Request model for test execution."""

    test_case_id: str = Field(..., description="ID of the test case to execute")
    # User may modify these parameters (if None, use original values)
    modified_model_name: Optional[str] = Field(None, description="Override model name")
    modified_system_prompt: Optional[str] = Field(None, description="Override system prompt")
    modified_last_user_message: Optional[str] = Field(None, description="Override user message")
    modified_tools: Optional[List[Dict]] = Field(None, description="Override tools configuration")
    modified_model_settings: Optional[Dict] = Field(None, description="Override model settings JSON")
