"""Agent API request schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class AgentCreateRequest(BaseModel):
    """Request body for creating an agent."""

    name: str = Field(..., min_length=1, max_length=255, description="Agent name")
    description: Optional[str] = Field(
        None, max_length=2000, description="Agent description"
    )
    default_model_name: Optional[str] = Field(
        None, description="Default model name for regression runs"
    )
    default_system_prompt: Optional[str] = Field(
        None, description="Default system prompt for regression runs"
    )
    default_model_settings: Optional[dict] = Field(
        None, description="Default model settings JSON"
    )


class AgentUpdateRequest(BaseModel):
    """Request body for updating an agent."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    default_model_name: Optional[str] = Field(None)
    default_system_prompt: Optional[str] = Field(None)
    default_model_settings: Optional[dict] = Field(None)


__all__ = ["AgentCreateRequest", "AgentUpdateRequest"]
