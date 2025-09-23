"""Settings response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EvaluationSettingsResponse(BaseModel):
    """Response payload for evaluation agent settings."""

    model_name: str = Field(..., description="Current evaluation model name")
    provider: str = Field(..., description="Provider configured for evaluation")
    updated_at: Optional[datetime] = Field(
        None, description="Timestamp of the last persisted change"
    )
