"""
Test Log Converters

Converters between API layer and service layer schemas for test logs.
"""

from src.api.v1.schemas.responses import TestLogListItemResponse, TestLogResponse
from src.services.test_log_service import LogData


def convert_test_log_data_to_response(data: LogData) -> TestLogResponse:
    """Convert service layer test log data to API response."""
    return TestLogResponse(
        id=data.id,
        test_case_id=data.test_case_id,
        agent_id=data.agent_id,
        regression_test_id=data.regression_test_id,
        model_name=data.model_name,
        model_settings=data.model_settings,
        system_prompt=data.system_prompt,
        user_message=data.user_message,
        tools=data.tools,
        llm_response=data.llm_response,
        response_example=data.response_example,
        response_expectation_snapshot=data.response_expectation_snapshot,
        response_time_ms=data.response_time_ms,
        is_passed=data.is_passed,
        evaluation_feedback=data.evaluation_feedback,
        evaluation_model_name=data.evaluation_model_name,
        evaluation_metadata=data.evaluation_metadata,
        status=data.status,
        error_message=data.error_message,
        created_at=data.created_at,
    )


def convert_test_log_data_to_list_item_response(
    data: LogData,
) -> TestLogListItemResponse:
    """Convert service layer log data to lightweight list response."""

    return TestLogListItemResponse(
        id=data.id,
        test_case_id=data.test_case_id,
        agent_id=data.agent_id,
        regression_test_id=data.regression_test_id,
        model_name=data.model_name,
        user_message=data.user_message,
        llm_response=data.llm_response,
        response_expectation_snapshot=data.response_expectation_snapshot,
        response_time_ms=data.response_time_ms,
        is_passed=data.is_passed,
        evaluation_feedback=data.evaluation_feedback,
        evaluation_model_name=data.evaluation_model_name,
        evaluation_metadata=data.evaluation_metadata,
        status=data.status,
        error_message=data.error_message,
        created_at=data.created_at,
    )


__all__ = [
    "convert_test_log_data_to_response",
    "convert_test_log_data_to_list_item_response",
]
