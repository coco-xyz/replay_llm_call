"""Service for managing evaluation agent configuration."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from src.core.config import settings
from src.core.logger import get_logger
from src.models import AppSetting
from src.stores.app_settings_store import AppSettingsStore

logger = get_logger(__name__)

EVALUATION_SETTINGS_KEY = "evaluation_agent"


class EvaluationSettingsData(BaseModel):
    """Pydantic representation of evaluation agent configuration."""

    model_name: str = Field(..., description="Model identifier for the evaluation agent")
    provider: str = Field(..., description="Provider responsible for the evaluation model")
    updated_at: Optional[datetime] = Field(
        None, description="Timestamp of the last persisted change"
    )


class EvaluationSettingsUpdate(BaseModel):
    """Payload for updating evaluation agent configuration."""

    model_name: str = Field(..., min_length=1, description="New model identifier")


class EvaluationSettingsService:
    """Read/write access layer for evaluation agent configuration."""

    def __init__(self, store: Optional[AppSettingsStore] = None) -> None:
        self.store = store or AppSettingsStore()

    def get_settings(self) -> EvaluationSettingsData:
        """Return current evaluation settings falling back to defaults."""
        record: Optional[AppSetting] = self.store.get_setting(EVALUATION_SETTINGS_KEY)
        payload = record.value if record and record.value is not None else {}
        model_name = payload.get("model_name") or settings.ai__eval_agent__model_name
        provider = payload.get("provider") or settings.ai__eval_agent__provider
        return EvaluationSettingsData(
            model_name=model_name,
            provider=provider,
            updated_at=record.updated_at if record else None,
        )

    def update_settings(
        self, update: EvaluationSettingsUpdate
    ) -> EvaluationSettingsData:
        """Persist a new evaluation model name."""
        model_name = update.model_name.strip()
        if not model_name:
            raise ValueError("Model name cannot be empty.")

        payload = {"model_name": model_name, "provider": settings.ai__eval_agent__provider}
        record = self.store.upsert_setting(EVALUATION_SETTINGS_KEY, payload)
        logger.info("Evaluation model updated to '%s'", model_name)
        return EvaluationSettingsData(
            model_name=model_name,
            provider=settings.ai__eval_agent__provider,
            updated_at=record.updated_at,
        )


__all__ = [
    "EvaluationSettingsData",
    "EvaluationSettingsUpdate",
    "EvaluationSettingsService",
]
