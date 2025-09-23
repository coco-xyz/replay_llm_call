"""
Test Logs API

REST API endpoints for test log management and viewing.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from src.api.v1.converters import convert_test_log_data_to_response
from src.api.v1.schemas.responses.test_log_responses import TestLogResponse
from src.core.logger import get_logger
from src.services.test_log_service import LogService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/test-logs", tags=["test-logs"])
test_log_service = LogService()


@router.get("/", response_model=List[TestLogResponse])
async def get_test_logs(
    limit: int = Query(20, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    regression_test_id: Optional[str] = Query(
        None, description="Filter by regression test ID"
    ),
):
    """
    Get all test logs with pagination.

    Args:
        limit: Maximum number of results (1-1000)
        offset: Number of results to skip

    Returns:
        List of test log responses

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        logger.debug(f"API: Getting test logs (limit={limit}, offset={offset})")
        result = test_log_service.get_logs_filtered(
            limit=limit,
            offset=offset,
            agent_id=agent_id,
            regression_test_id=regression_test_id,
        )
        logger.debug(f"API: Retrieved {len(result)} test logs")
        return [convert_test_log_data_to_response(log) for log in result]

    except Exception as e:
        logger.error(f"API: Failed to get test logs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{log_id}", response_model=TestLogResponse)
async def get_test_log(log_id: str):
    """
    Get a test log by ID.

    Args:
        log_id: Test log ID

    Returns:
        TestLogResponse: Test log data

    Raises:
        HTTPException: If test log not found or retrieval fails
    """
    try:
        logger.debug(f"API: Getting test log: {log_id}")
        result = test_log_service.get_test_log(log_id)

        if not result:
            logger.debug(f"API: Test log not found: {log_id}")
            raise HTTPException(status_code=404, detail="Test log not found")

        return convert_test_log_data_to_response(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Failed to get test log {log_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/test-case/{test_case_id}", response_model=List[TestLogResponse])
async def get_logs_by_test_case(
    test_case_id: str,
    limit: int = Query(20, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    Get test logs for a specific test case.

    Args:
        test_case_id: Test case ID
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        List of test logs for the test case

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        logger.debug(f"API: Getting logs for test case: {test_case_id}")
        result = test_log_service.get_logs_by_test_case(
            test_case_id, limit=limit, offset=offset
        )
        logger.debug(f"API: Retrieved {len(result)} logs for test case {test_case_id}")
        return [convert_test_log_data_to_response(log) for log in result]

    except Exception as e:
        logger.error(f"API: Failed to get logs for test case {test_case_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/filter/status/{status}", response_model=List[TestLogResponse])
async def get_logs_by_status(
    status: str,
    limit: int = Query(20, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    regression_test_id: Optional[str] = Query(
        None, description="Filter by regression test ID"
    ),
):
    """
    Get test logs filtered by status.

    Args:
        status: Status to filter by (success, failed)
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        List of test logs with the specified status

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        logger.debug(f"API: Getting logs with status: {status}")
        result = test_log_service.get_logs_by_status(
            status,
            limit=limit,
            offset=offset,
            agent_id=agent_id,
            regression_test_id=regression_test_id,
        )
        logger.debug(f"API: Retrieved {len(result)} logs with status {status}")
        return [convert_test_log_data_to_response(log) for log in result]

    except Exception as e:
        logger.error(f"API: Failed to get logs by status {status}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/filter/combined", response_model=List[TestLogResponse])
async def get_logs_filtered(
    status: Optional[str] = Query(None, description="Filter by status"),
    test_case_id: Optional[str] = Query(None, description="Filter by test case ID"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    regression_test_id: Optional[str] = Query(
        None, description="Filter by regression test ID"
    ),
    limit: int = Query(20, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    Get test logs with combined filters.

    Args:
        status: Optional status filter
        test_case_id: Optional test case ID filter
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        List of filtered test logs

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        logger.debug(
            f"API: Getting filtered logs (status={status}, test_case_id={test_case_id})"
        )
        result = test_log_service.get_logs_filtered(
            status=status,
            test_case_id=test_case_id,
            agent_id=agent_id,
            regression_test_id=regression_test_id,
            limit=limit,
            offset=offset,
        )
        logger.debug(f"API: Retrieved {len(result)} filtered logs")
        return [convert_test_log_data_to_response(log) for log in result]

    except Exception as e:
        logger.error(f"API: Failed to get filtered logs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{log_id}")
async def delete_test_log(log_id: str):
    """
    Delete a test log by ID.

    Args:
        log_id: Test log ID to delete

    Returns:
        Dict with success message

    Raises:
        HTTPException: If test log not found or deletion fails
    """
    try:
        logger.info(f"API: Deleting test log: {log_id}")
        deleted = test_log_service.delete_test_log(log_id)

        if not deleted:
            logger.debug(f"API: Test log not found for deletion: {log_id}")
            raise HTTPException(status_code=404, detail="Test log not found")

        logger.info(f"API: Test log deleted successfully: {log_id}")
        return {"message": "Test log deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Failed to delete test log {log_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/test-case/{test_case_id}")
async def delete_logs_by_test_case(test_case_id: str):
    """
    Delete all test logs for a test case.

    Args:
        test_case_id: Test case ID

    Returns:
        Dict with deletion count

    Raises:
        HTTPException: If deletion fails
    """
    try:
        logger.info(f"API: Deleting logs for test case: {test_case_id}")
        deleted_count = test_log_service.delete_logs_by_test_case(test_case_id)

        logger.info(f"API: Deleted {deleted_count} logs for test case {test_case_id}")
        return {
            "message": f"Deleted {deleted_count} test logs",
            "deleted_count": deleted_count,
        }

    except Exception as e:
        logger.error(f"API: Failed to delete logs for test case {test_case_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


__all__ = ["router"]


@router.get("/regression/{regression_test_id}", response_model=List[TestLogResponse])
async def get_logs_by_regression_test(
    regression_test_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Get logs for a specific regression test."""

    try:
        logger.debug("API: Getting logs for regression test: %s", regression_test_id)
        result = test_log_service.get_logs_by_regression_test(
            regression_test_id, limit=limit, offset=offset
        )
        logger.debug(
            "API: Retrieved %d logs for regression test %s",
            len(result),
            regression_test_id,
        )
        return [convert_test_log_data_to_response(log) for log in result]
    except Exception as e:
        logger.error(
            "API: Failed to get logs for regression test %s: %s",
            regression_test_id,
            e,
        )
        raise HTTPException(status_code=500, detail="Internal server error")
