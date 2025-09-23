"""
Test Execution Converters

Converters between API layer and service layer schemas for test execution.
"""

from src.api.v1.schemas.requests import TestExecutionRequest
from src.api.v1.schemas.responses import TestExecutionResponse
from src.services.test_execution_service import ExecutionResult, ExecutionData


def convert_test_execution_request(request: TestExecutionRequest) -> ExecutionData:
    """Convert API execution request to service layer data."""
    return ExecutionData(
        test_case_id=request.test_case_id,
        modified_model_name=request.modified_model_name,
        modified_system_prompt=request.modified_system_prompt,
        modified_last_user_message=request.modified_last_user_message,
        modified_tools=request.modified_tools,
        modified_model_settings=request.modified_model_settings,
    )


def convert_test_execution_result_to_response(
    result: ExecutionResult,
) -> TestExecutionResponse:
    """Convert service layer execution result to API response."""
    return TestExecutionResponse(
        status=result.status,
        log_id=result.log_id,
        agent_id=result.agent_id,
        regression_test_id=result.regression_test_id,
        response_time_ms=result.response_time_ms,
        executed_at=result.executed_at,
        error_message=result.error_message,
        llm_response=result.llm_response,
        is_passed=result.is_passed,
        evaluation_feedback=result.evaluation_feedback,
        evaluation_model_name=result.evaluation_model_name,
        evaluation_metadata=result.evaluation_metadata,
        response_expectation=result.response_expectation,
        # Legacy fields for backward compatibility
        test_log=None,  # Can be populated if needed
        error=result.error_message,  # Legacy field mapping
    )
