"""
Test Cases API

REST API endpoints for test case management.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from src.core.logger import get_logger
from src.api.v1.schemas.requests import TestCaseCreateRequest, TestCaseUpdateRequest
from src.api.v1.schemas.responses import TestCaseResponse
from src.api.v1.converters import (
    convert_test_case_create_request,
    convert_test_case_update_request,
    convert_test_case_data_to_response
)
from src.services.test_case_service import TestCaseService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/test-cases", tags=["test-cases"])
test_case_service = TestCaseService()


@router.post("/", response_model=TestCaseResponse)
async def create_test_case(request: TestCaseCreateRequest):
    """
    Create a new test case with automatic parsing of raw data.
    
    Args:
        request: Test case creation request
        
    Returns:
        TestCaseResponse: Created test case data
        
    Raises:
        HTTPException: If creation fails or data is invalid
    """
    try:
        logger.info(f"API: Creating test case '{request.name}'")
        # Convert API request to service layer data
        service_data = convert_test_case_create_request(request)
        result = test_case_service.create_test_case(service_data)
        logger.info(f"API: Test case created successfully: {result.id}")
        # Convert service layer data to API response
        return convert_test_case_data_to_response(result)

    except ValueError as e:
        logger.error(f"API: Invalid test case data: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"API: Failed to create test case: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=List[TestCaseResponse])
async def get_test_cases(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Get all test cases with pagination.
    
    Args:
        limit: Maximum number of results
        offset: Number of results to skip
        
    Returns:
        List of test cases
        
    Raises:
        HTTPException: If retrieval fails
    """
    try:
        logger.debug(f"API: Getting test cases (limit={limit}, offset={offset})")
        result = test_case_service.get_all_test_cases(limit=limit, offset=offset)
        logger.debug(f"API: Retrieved {len(result)} test cases")
        return result

    except Exception as e:
        logger.error(f"API: Failed to get test cases: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/search", response_model=List[TestCaseResponse])
async def search_test_cases(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=500)
):
    """
    Search test cases by name.
    
    Args:
        q: Search query string
        limit: Maximum number of results
        
    Returns:
        List of matching test cases
        
    Raises:
        HTTPException: If search fails
    """
    try:
        logger.debug(f"API: Searching test cases with query: '{q}'")
        result = test_case_service.search_test_cases(q, limit=limit)
        logger.debug(f"API: Found {len(result)} test cases matching '{q}'")
        return result

    except Exception as e:
        logger.error(f"API: Failed to search test cases: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{test_case_id}", response_model=TestCaseResponse)
async def get_test_case(test_case_id: str):
    """
    Get a test case by ID.
    
    Args:
        test_case_id: Test case ID
        
    Returns:
        TestCaseResponse: Test case data
        
    Raises:
        HTTPException: If test case not found or retrieval fails
    """
    try:
        logger.debug(f"API: Getting test case: {test_case_id}")
        result = test_case_service.get_test_case(test_case_id)

        if not result:
            logger.debug(f"API: Test case not found: {test_case_id}")
            raise HTTPException(status_code=404, detail="Test case not found")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Failed to get test case {test_case_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{test_case_id}", response_model=TestCaseResponse)
async def update_test_case(test_case_id: str, request: TestCaseUpdateRequest):
    """
    Update an existing test case.
    
    Args:
        test_case_id: Test case ID to update
        request: Update request data
        
    Returns:
        TestCaseResponse: Updated test case data
        
    Raises:
        HTTPException: If test case not found or update fails
    """
    try:
        logger.info(f"API: Updating test case: {test_case_id}")
        # Convert API request to service layer data
        service_data = convert_test_case_update_request(request)
        result = test_case_service.update_test_case(test_case_id, service_data)

        if not result:
            logger.debug(f"API: Test case not found for update: {test_case_id}")
            raise HTTPException(status_code=404, detail="Test case not found")

        logger.info(f"API: Test case updated successfully: {test_case_id}")
        # Convert service layer data to API response
        return convert_test_case_data_to_response(result)

    except ValueError as e:
        logger.error(f"API: Invalid test case update data: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Failed to update test case {test_case_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{test_case_id}")
async def delete_test_case(test_case_id: str):
    """
    Delete a test case by ID.
    
    Args:
        test_case_id: Test case ID to delete
        
    Returns:
        Dict with success message
        
    Raises:
        HTTPException: If test case not found or deletion fails
    """
    try:
        logger.info(f"API: Deleting test case: {test_case_id}")
        deleted = test_case_service.delete_test_case(test_case_id)

        if not deleted:
            logger.debug(f"API: Test case not found for deletion: {test_case_id}")
            raise HTTPException(status_code=404, detail="Test case not found")

        logger.info(f"API: Test case deleted successfully: {test_case_id}")
        return {"message": "Test case deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Failed to delete test case {test_case_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


__all__ = ["router"]
