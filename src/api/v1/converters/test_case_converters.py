"""
Test Case Converters

Converters between API layer and service layer schemas for test cases.
"""

from src.api.v1.schemas.requests import TestCaseCreateRequest, TestCaseUpdateRequest
from src.api.v1.schemas.responses import TestCaseResponse
from src.services.test_case_service import TestCaseCreateData, TestCaseUpdateData, TestCaseData


def convert_test_case_create_request(request: TestCaseCreateRequest) -> TestCaseCreateData:
    """Convert API create request to service layer data."""
    return TestCaseCreateData(
        name=request.name,
        raw_data=request.raw_data,
        description=request.description
    )


def convert_test_case_update_request(request: TestCaseUpdateRequest) -> TestCaseUpdateData:
    """Convert API update request to service layer data."""
    return TestCaseUpdateData(
        name=request.name,
        raw_data=request.raw_data,
        description=request.description,
        system_prompt=request.system_prompt,
        last_user_message=request.last_user_message
    )


def convert_test_case_data_to_response(data: TestCaseData) -> TestCaseResponse:
    """Convert service layer data to API response."""
    return TestCaseResponse(
        id=data.id,
        name=data.name,
        description=data.description,
        raw_data=data.raw_data,
        middle_messages=data.middle_messages,
        tools=data.tools,
        model_name=data.model_name,
        temperature=data.temperature,
        system_prompt=data.system_prompt,
        last_user_message=data.last_user_message,
        created_at=data.created_at,
        updated_at=data.updated_at
    )
