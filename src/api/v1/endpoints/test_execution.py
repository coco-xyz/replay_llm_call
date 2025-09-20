"""
Test Execution API

REST API endpoints for test execution.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException

from src.api.v1.converters import (
    convert_test_execution_request,
    convert_test_execution_result_to_response,
)
from src.api.v1.schemas.requests import TestExecutionRequest
from src.api.v1.schemas.responses import TestExecutionResponse
from src.core.logger import get_logger
from src.services.test_execution_service import TestExecutionService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/test-execution", tags=["test-execution"])
test_execution_service = TestExecutionService()


@router.post("/execute", response_model=TestExecutionResponse)
async def execute_test(request: TestExecutionRequest):
    """
    Execute a test case synchronously.

    Args:
        request: Test execution request

    Returns:
        TestExecutionResponse: Execution results

    Raises:
        HTTPException: If execution fails or test case not found
    """
    try:
        logger.info(f"API: Executing test for case: {request.test_case_id}")
        # Convert API request to service layer data
        service_data = convert_test_execution_request(request)
        result = await test_execution_service.execute_test(service_data)
        logger.info(f"API: Test execution completed: {result.status}")
        # Convert service layer result to API response
        return convert_test_execution_result_to_response(result)

    except ValueError as e:
        logger.error(f"API: Invalid test execution request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"API: Test execution failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/execute/{test_case_id}", response_model=TestExecutionResponse)
async def execute_test_by_id(
    test_case_id: str,
    model_name: Optional[str] = None,
    system_prompt: Optional[str] = None,
    user_message: Optional[str] = None,
):
    """
    Execute a test case by ID with optional parameter overrides.

    Args:
        test_case_id: Test case ID to execute
        model_name: Optional model name override
        system_prompt: Optional system prompt override
        user_message: Optional user message override

    Returns:
        TestExecutionResponse: Execution results

    Raises:
        HTTPException: If execution fails or test case not found
    """
    try:
        logger.info(f"API: Executing test case by ID: {test_case_id}")

        # Create execution request from parameters
        request = TestExecutionRequest(
            test_case_id=test_case_id,
            model_name=model_name,
            system_prompt=system_prompt,
            user_message=user_message,
        )

        # Convert API request to service layer data
        service_data = convert_test_execution_request(request)
        result = await test_execution_service.execute_test(service_data)
        logger.info(f"API: Test execution completed: {result.status}")
        # Convert service layer result to API response
        return convert_test_execution_result_to_response(result)

    except ValueError as e:
        logger.error(f"API: Invalid test execution request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"API: Test execution failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


__all__ = ["router"]
