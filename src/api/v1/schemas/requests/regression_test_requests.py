"""Regression test API request schemas."""

from typing import Dict

from pydantic import BaseModel, Field


class RegressionTestCreateRequest(BaseModel):
    """Request body to start a regression test."""

    agent_id: str = Field(..., description="Agent identifier")
    model_name: str = Field(..., description="Model name override")
    system_prompt: str = Field(..., description="System prompt override")
    model_settings: Dict = Field(
        default_factory=dict, description="Model settings override JSON"
    )


__all__ = ["RegressionTestCreateRequest"]
