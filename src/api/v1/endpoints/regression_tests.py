"""Regression test endpoints."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from src.api.v1.converters import (
    convert_regression_test_create_request,
    convert_regression_test_data_to_response,
    convert_test_log_data_to_response,
)
from src.api.v1.schemas.requests import RegressionTestCreateRequest
from src.api.v1.schemas.responses import RegressionTestResponse, TestLogResponse
from src.core.logger import get_logger
from src.services.regression_test_service import RegressionTestService
from src.services.test_log_service import TestLogService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/regression-tests", tags=["regression-tests"])
regression_service = RegressionTestService()
test_log_service = TestLogService()


@router.post("/", response_model=RegressionTestResponse)
async def start_regression(
    request: RegressionTestCreateRequest,
) -> RegressionTestResponse:
    try:
        service_request = convert_regression_test_create_request(request)
        regression = await regression_service.run_regression_test(service_request)
        return convert_regression_test_data_to_response(regression)
    except ValueError as exc:
        logger.error("API: Invalid regression request: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("API: Failed to start regression: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=List[RegressionTestResponse])
async def list_regressions(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> List[RegressionTestResponse]:
    try:
        records = regression_service.list_regression_tests(
            agent_id=agent_id, status=status, limit=limit, offset=offset
        )
        return [convert_regression_test_data_to_response(record) for record in records]
    except Exception as exc:  # pragma: no cover
        logger.error("API: Failed to list regressions: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{regression_test_id}", response_model=RegressionTestResponse)
async def get_regression(regression_test_id: str) -> RegressionTestResponse:
    record = regression_service.get_regression_test(regression_test_id)
    if not record:
        raise HTTPException(status_code=404, detail="Regression test not found")
    return convert_regression_test_data_to_response(record)


@router.get("/{regression_test_id}/logs", response_model=List[TestLogResponse])
async def get_regression_logs(
    regression_test_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[TestLogResponse]:
    try:
        logs = test_log_service.get_logs_by_regression_test(
            regression_test_id, limit=limit, offset=offset
        )
        return [convert_test_log_data_to_response(log) for log in logs]
    except Exception as exc:  # pragma: no cover
        logger.error(
            "API: Failed to fetch regression logs for %s: %s",
            regression_test_id,
            exc,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


__all__ = ["router"]
