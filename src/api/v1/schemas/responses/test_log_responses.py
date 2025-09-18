"""
Test Log Response Schemas

API response models for test log endpoints.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TestLogResponse(BaseModel):
    """Response model for test log data."""

    id: str = Field(..., description="Test log ID")
    test_case_id: str = Field(..., description="Associated test case ID")
    model_name: str = Field(..., description="Model used for execution")
    temperature: Optional[float] = Field(None, description="Temperature parameter used")
    system_prompt: str = Field(..., description="System prompt used")
    user_message: str = Field(..., description="User message used")
    tools: Optional[List[Dict]] = Field(None, description="Tools configuration used")
    llm_response: Optional[str] = Field(None, description="LLM response text")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")
    status: str = Field(..., description="Execution status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True
