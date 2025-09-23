"""Settings request schemas."""

from pydantic import BaseModel, Field


class EvaluationSettingsUpdateRequest(BaseModel):
    """Request payload for updating evaluation agent configuration."""

    model_name: str = Field(
        ..., min_length=1, description="Model identifier to use for evaluation"
    )
