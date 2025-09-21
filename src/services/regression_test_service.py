"""Service orchestrating regression test executions."""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.logger import get_logger
from src.models import RegressionTest
from src.services.agent_service import AgentService, AgentSummary
from src.services.test_case_service import TestCaseService
from src.services.test_execution_service import (
    TestExecutionData,
    TestExecutionResult,
    TestExecutionService,
)
from src.stores.regression_test_store import RegressionTestStore

logger = get_logger(__name__)


class RegressionTestCreateData(BaseModel):
    """Input payload for launching a regression test."""

    agent_id: str = Field(..., description="Agent under test")
    model_name_override: str = Field(
        ..., description="Model name override for this regression"
    )
    system_prompt_override: str = Field(..., description="System prompt override")
    model_settings_override: Dict = Field(
        default_factory=dict, description="Model settings override JSON"
    )


class RegressionTestData(BaseModel):
    """Service representation of a regression test record."""

    id: str
    agent_id: str
    status: str
    model_name_override: str
    system_prompt_override: str
    model_settings_override: Dict
    total_count: int
    success_count: int
    failed_count: int
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    agent: Optional[AgentSummary] = None

    class Config:
        from_attributes = True


class RegressionTestService:
    """Coordinates regression execution across all test cases for an agent."""

    MAX_CONCURRENCY = 5

    def __init__(self) -> None:
        self.agent_service = AgentService()
        self.test_case_service = TestCaseService()
        self.test_execution_service = TestExecutionService()
        self.store = RegressionTestStore()

    async def run_regression_test(
        self, request: RegressionTestCreateData
    ) -> RegressionTestData:
        """Create and execute a regression test for an agent."""

        agent = self.agent_service.get_active_agent_or_raise(request.agent_id)
        agent_summary = AgentSummary.model_validate(agent)
        test_cases = self.test_case_service.store.get_by_agent(agent.id)

        regression = RegressionTest(
            id=str(uuid.uuid4()),
            agent_id=agent.id,
            status="running",
            model_name_override=request.model_name_override,
            system_prompt_override=request.system_prompt_override,
            model_settings_override=request.model_settings_override,
            total_count=len(test_cases),
            success_count=0,
            failed_count=0,
            error_message=None,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
        )

        regression = self.store.create(regression)

        if not test_cases:
            logger.info(
                "No test cases available for agent %s; marking regression %s as completed",
                agent.id,
                regression.id,
            )
            regression.status = "completed"
            regression.completed_at = datetime.now(timezone.utc)
            regression = self.store.update(regression)
            return self._build_regression_test_data(regression, agent_summary)

        semaphore = asyncio.Semaphore(self.MAX_CONCURRENCY)
        results: List[TestExecutionResult] = []
        execution_errors: List[str] = []

        async def execute_case(case) -> None:
            async with semaphore:
                try:
                    execution_request = TestExecutionData(
                        test_case_id=case.id,
                        agent_id=agent.id,
                        regression_test_id=regression.id,
                        modified_model_name=request.model_name_override,
                        modified_system_prompt=request.system_prompt_override,
                        modified_model_settings=request.model_settings_override,
                    )
                    result = await self.test_execution_service.execute_test(
                        execution_request
                    )
                    results.append(result)
                except Exception as execution_error:  # pragma: no cover - defensive
                    logger.error(
                        "Regression %s execution failed for case %s: %s",
                        regression.id,
                        case.id,
                        execution_error,
                    )
                    execution_errors.append(str(execution_error))

        await asyncio.gather(*(execute_case(case) for case in test_cases))

        success_count = sum(1 for result in results if result.status == "success")
        failed_count = len(test_cases) - success_count

        if execution_errors:
            # Account for cases that raised exceptions and didn't yield results
            failed_count = max(failed_count, len(execution_errors))

        regression.success_count = success_count
        regression.failed_count = failed_count
        has_failures = failed_count > 0
        regression.status = (
            "failed" if (execution_errors or has_failures) else "completed"
        )
        regression.error_message = (
            "; ".join(execution_errors) if execution_errors else None
        )
        regression.completed_at = datetime.now(timezone.utc)

        regression = self.store.update(regression)
        return self._build_regression_test_data(regression, agent_summary)

    def get_regression_test(
        self, regression_test_id: str
    ) -> Optional[RegressionTestData]:
        record = self.store.get_by_id(regression_test_id)
        if not record:
            return None
        agent_summary = self.agent_service.get_agent_summary(record.agent_id)
        return self._build_regression_test_data(record, agent_summary)

    def list_regression_tests(
        self,
        *,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[RegressionTestData]:
        records = self.store.list_regression_tests(
            agent_id=agent_id, status=status, limit=limit, offset=offset
        )
        agent_cache: Dict[str, AgentSummary] = {}
        data: List[RegressionTestData] = []
        for record in records:
            if record.agent_id not in agent_cache:
                agent_cache[record.agent_id] = self.agent_service.get_agent_summary(
                    record.agent_id
                )
            data.append(
                self._build_regression_test_data(record, agent_cache[record.agent_id])
            )
        return data

    def _build_regression_test_data(
        self,
        regression: RegressionTest,
        agent_summary: Optional[AgentSummary] = None,
    ) -> RegressionTestData:
        if agent_summary is None:
            agent_summary = self.agent_service.get_agent_summary(regression.agent_id)

        return RegressionTestData(
            id=regression.id,
            agent_id=regression.agent_id,
            status=regression.status,
            model_name_override=regression.model_name_override,
            system_prompt_override=regression.system_prompt_override,
            model_settings_override=regression.model_settings_override,
            total_count=regression.total_count,
            success_count=regression.success_count,
            failed_count=regression.failed_count,
            error_message=regression.error_message,
            started_at=regression.started_at,
            completed_at=regression.completed_at,
            created_at=regression.created_at,
            updated_at=regression.updated_at,
            agent=agent_summary,
        )


__all__ = [
    "RegressionTestService",
    "RegressionTestCreateData",
    "RegressionTestData",
]
