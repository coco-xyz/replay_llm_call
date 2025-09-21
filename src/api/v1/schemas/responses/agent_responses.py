"""Agent API response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AgentResponse(BaseModel):
    """Full agent response."""

    id: str = Field(..., description="Agent identifier")
    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    default_model_name: Optional[str] = Field(
        None, description="Default model name for regression runs"
    )
    default_system_prompt: Optional[str] = Field(
        None, description="Default system prompt"
    )
    default_model_settings: Optional[dict] = Field(
        None, description="Default model settings JSON"
    )
    is_deleted: bool = Field(False, description="Soft delete flag")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class AgentSummaryResponse(BaseModel):
    """Short agent representation for embedding."""

    id: str = Field(..., description="Agent identifier")
    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")

    model_config = ConfigDict(from_attributes=True)


__all__ = ["AgentResponse", "AgentSummaryResponse"]
