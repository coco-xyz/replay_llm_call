"""Regression test API response schemas."""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from .agent_responses import AgentSummaryResponse


class RegressionTestResponse(BaseModel):
    """Response model representing a regression test run."""

    id: str = Field(..., description="Regression test identifier")
    agent_id: str = Field(..., description="Agent identifier")
    status: str = Field(..., description="Regression status")
    model_name_override: str = Field(..., description="Model name override")
    system_prompt_override: str = Field(..., description="System prompt override")
    model_settings_override: Dict = Field(..., description="Model settings override")
    total_count: int = Field(..., description="Total number of executed test cases")
    success_count: int = Field(..., description="Number of successful executions")
    failed_count: int = Field(..., description="Number of failed executions")
    passed_count: int = Field(..., description="Number of test logs evaluated as passed")
    declined_count: int = Field(..., description="Number of test logs evaluated as declined")
    unknown_count: int = Field(..., description="Number of test logs without an evaluation outcome")
    error_message: Optional[str] = Field(
        None, description="Aggregated error message if the regression failed"
    )
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")
    agent: Optional[AgentSummaryResponse] = Field(
        None, description="Summary information about the agent"
    )

    model_config = ConfigDict(from_attributes=True)


__all__ = ["RegressionTestResponse"]
