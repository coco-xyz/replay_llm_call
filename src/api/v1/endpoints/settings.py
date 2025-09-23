"""Settings endpoints."""

from fastapi import APIRouter, HTTPException

from src.api.v1.converters import convert_evaluation_settings_to_response
from src.api.v1.schemas.requests import EvaluationSettingsUpdateRequest
from src.api.v1.schemas.responses import EvaluationSettingsResponse
from src.services.evaluation_settings_service import (
    EvaluationSettingsService,
    EvaluationSettingsUpdate,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])
settings_service = EvaluationSettingsService()


@router.get("/evaluation", response_model=EvaluationSettingsResponse)
async def get_evaluation_settings() -> EvaluationSettingsResponse:
    """Return current evaluation agent configuration."""

    settings = settings_service.get_settings()
    return convert_evaluation_settings_to_response(settings)


@router.put("/evaluation", response_model=EvaluationSettingsResponse)
async def update_evaluation_settings(
    request: EvaluationSettingsUpdateRequest,
) -> EvaluationSettingsResponse:
    """Update evaluation agent configuration."""

    try:
        update = EvaluationSettingsUpdate(model_name=request.model_name)
        settings = settings_service.update_settings(update)
        return convert_evaluation_settings_to_response(settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive API guard
        raise HTTPException(status_code=500, detail="Internal server error") from exc


__all__ = ["router"]
