"""
Test Case Response Schemas

API response models for test case endpoints.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .agent_responses import AgentSummaryResponse


class TestCaseResponse(BaseModel):
    """Response model for test case data."""

    id: str = Field(..., description="Test case ID")
    name: str = Field(..., description="Test case name")
    description: Optional[str] = Field(None, description="Test case description")
    raw_data: Dict = Field(..., description="Raw logfire data")
    middle_messages: List[Dict] = Field(..., description="Middle messages for replay")
    tools: Optional[List[Dict]] = Field(None, description="Tools configuration")
    model_name: str = Field(..., description="Model name")
    model_settings: Optional[Dict] = Field(
        None, description="Model settings JSON (temperature, max_tokens, etc.)"
    )
    system_prompt: str = Field(..., description="System prompt")
    last_user_message: str = Field(..., description="Last user message")
    agent_id: str = Field(..., description="Owning agent ID")
    agent: Optional[AgentSummaryResponse] = Field(
        None, description="Owning agent summary"
    )
    is_deleted: bool = Field(
        False, description="Indicates whether the test case is soft deleted"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)
