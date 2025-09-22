"""
Test Log Converters

Converters between API layer and service layer schemas for test logs.
"""

from src.api.v1.schemas.responses import TestLogResponse
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
        response_example_vector=data.response_example_vector,
        response_time_ms=data.response_time_ms,
        similarity_score=data.similarity_score,
        is_passed=data.is_passed,
        status=data.status,
        error_message=data.error_message,
        created_at=data.created_at,
    )
