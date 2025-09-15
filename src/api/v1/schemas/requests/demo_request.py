"""
Demo Request Schemas

Simple request models for demo endpoints.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DemoChatRequest(BaseModel):
    """Request model for demo chat endpoint."""

    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Optional session ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context data")
