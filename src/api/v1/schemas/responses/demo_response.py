"""
Demo Response Schemas

Simple response models for demo endpoints.
"""

from typing import Optional

from pydantic import BaseModel, Field


class DemoChatResponse(BaseModel):
    """Response model for demo chat endpoint."""

    response: str = Field(..., description="Agent response")
    session_id: Optional[str] = Field(None, description="Session ID")
    status: str = Field(default="success", description="Response status")
