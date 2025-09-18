"""
Test Case Response Schemas

API response models for test case endpoints.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TestCaseResponse(BaseModel):
    """Response model for test case data."""

    id: str = Field(..., description="Test case ID")
    name: str = Field(..., description="Test case name")
    description: Optional[str] = Field(None, description="Test case description")
    raw_data: Dict = Field(..., description="Raw logfire data")
    middle_messages: List[Dict] = Field(..., description="Middle messages for replay")
    tools: Optional[List[Dict]] = Field(None, description="Tools configuration")
    model_name: str = Field(..., description="Model name")
    temperature: Optional[float] = Field(None, description="Temperature parameter")
    system_prompt: str = Field(..., description="System prompt")
    last_user_message: str = Field(..., description="Last user message")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True
