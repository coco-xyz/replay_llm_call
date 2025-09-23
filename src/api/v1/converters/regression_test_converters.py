"""Regression test API converters."""

from src.api.v1.schemas.requests import RegressionTestCreateRequest
from src.api.v1.schemas.responses import (
    RegressionTestListItemResponse,
    RegressionTestResponse,
)
from src.services.regression_test_service import (
    RegressionTestCreateData,
    RegressionTestData,
)

from .agent_converters import convert_agent_summary_to_response


def convert_regression_test_create_request(
    request: RegressionTestCreateRequest,
) -> RegressionTestCreateData:
    """Convert API create request to service layer data."""

    return RegressionTestCreateData(
        agent_id=request.agent_id,
        model_name_override=request.model_name_override,
        system_prompt_override=request.system_prompt_override,
        model_settings_override=request.model_settings_override,
    )


def convert_regression_test_data_to_response(
    data: RegressionTestData,
) -> RegressionTestResponse:
    """Convert service data to API response."""

    return RegressionTestResponse(
        id=data.id,
        agent_id=data.agent_id,
        status=data.status,
        model_name_override=data.model_name_override,
        system_prompt_override=data.system_prompt_override,
        model_settings_override=data.model_settings_override,
        total_count=data.total_count,
        success_count=data.success_count,
        failed_count=data.failed_count,
        passed_count=data.passed_count,
        declined_count=data.declined_count,
        unknown_count=data.unknown_count,
        error_message=data.error_message,
        started_at=data.started_at,
        completed_at=data.completed_at,
        created_at=data.created_at,
        updated_at=data.updated_at,
        agent=convert_agent_summary_to_response(data.agent),
    )


def convert_regression_test_data_to_list_item_response(
    data: RegressionTestData,
) -> RegressionTestListItemResponse:
    """Convert regression data to lightweight list response."""

    return RegressionTestListItemResponse(
        id=data.id,
        agent_id=data.agent_id,
        status=data.status,
        model_name_override=data.model_name_override,
        system_prompt_override=data.system_prompt_override,
        model_settings_override=data.model_settings_override,
        total_count=data.total_count,
        passed_count=data.passed_count,
        declined_count=data.declined_count,
        created_at=data.created_at,
        agent=convert_agent_summary_to_response(data.agent),
    )


__all__ = [
    "convert_regression_test_create_request",
    "convert_regression_test_data_to_response",
    "convert_regression_test_data_to_list_item_response",
]
