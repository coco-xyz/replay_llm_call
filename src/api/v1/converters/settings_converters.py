"""Settings converters."""

from src.api.v1.schemas.responses import EvaluationSettingsResponse
from src.services.evaluation_settings_service import EvaluationSettingsData


def convert_evaluation_settings_to_response(
    data: EvaluationSettingsData,
) -> EvaluationSettingsResponse:
    """Convert service layer evaluation settings to API response."""

    return EvaluationSettingsResponse(
        model_name=data.model_name,
        provider=data.provider,
        updated_at=data.updated_at,
    )
