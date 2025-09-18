"""
Test Execution Converters

Converters between API layer and service layer schemas for test execution.
"""

from src.api.v1.schemas.requests import TestExecutionRequest
from src.api.v1.schemas.responses import TestExecutionResponse
from src.services.test_execution_service import TestExecutionData, TestExecutionResult


def convert_test_execution_request(request: TestExecutionRequest) -> TestExecutionData:
    """Convert API execution request to service layer data."""
    return TestExecutionData(
        test_case_id=request.test_case_id,
        modified_model_name=request.modified_model_name,
        modified_system_prompt=request.modified_system_prompt,
        modified_last_user_message=request.modified_last_user_message,
        modified_tools=request.modified_tools,
        modified_temperature=request.modified_temperature
    )


def convert_test_execution_result_to_response(result: TestExecutionResult) -> TestExecutionResponse:
    """Convert service layer execution result to API response."""
    return TestExecutionResponse(
        status=result.status,
        log_id=result.log_id,
        response_time_ms=result.response_time_ms,
        executed_at=result.executed_at,
        error_message=result.error_message,
        llm_response=result.llm_response,
        # Legacy fields for backward compatibility
        test_log=None,  # Can be populated if needed
        error=result.error_message  # Legacy field mapping
    )
