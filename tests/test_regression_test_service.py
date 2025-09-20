from types import SimpleNamespace

import pytest

from src.services.regression_test_service import (
    RegressionTestCreateData,
    RegressionTestService,
)
from src.services.test_execution_service import TestExecutionResult


@pytest.mark.asyncio
async def test_run_regression_with_no_cases(monkeypatch):
    service = RegressionTestService()

    agent = SimpleNamespace(
        id="agent-1",
        is_deleted=False,
        default_model_name="model",
        default_system_prompt="prompt",
        default_model_settings={"temperature": 0.2},
    )

    monkeypatch.setattr(
        service.agent_service,
        "get_active_agent_or_raise",
        lambda agent_id: agent,
    )
    monkeypatch.setattr(
        service.agent_service,
        "get_agent_summary",
        lambda agent_id: None,
    )
    monkeypatch.setattr(
        service.test_case_service.store,
        "get_by_agent",
        lambda agent_id: [],
    )

    created = {}
    monkeypatch.setattr(service.store, "create", lambda record: record)
    monkeypatch.setattr(service.store, "update", lambda record: record)

    request = RegressionTestCreateData(
        agent_id="agent-1",
        model_name="model",
        system_prompt="prompt",
        model_settings={},
    )

    result = await service.run_regression_test(request)
    assert result.status == "completed"
    assert result.total_count == 0
    assert result.success_count == 0
    assert result.failed_count == 0


@pytest.mark.asyncio
async def test_run_regression_counts_results(monkeypatch):
    service = RegressionTestService()

    agent = SimpleNamespace(
        id="agent-1",
        is_deleted=False,
        default_model_name="model",
        default_system_prompt="prompt",
        default_model_settings={},
    )

    test_cases = [
        SimpleNamespace(id="case-1", agent_id="agent-1"),
        SimpleNamespace(id="case-2", agent_id="agent-1"),
    ]

    monkeypatch.setattr(
        service.agent_service,
        "get_active_agent_or_raise",
        lambda agent_id: agent,
    )
    monkeypatch.setattr(
        service.agent_service,
        "get_agent_summary",
        lambda agent_id: None,
    )
    monkeypatch.setattr(
        service.test_case_service.store,
        "get_by_agent",
        lambda agent_id: test_cases,
    )
    monkeypatch.setattr(service.store, "create", lambda record: record)
    monkeypatch.setattr(service.store, "update", lambda record: record)

    async def fake_execute(request):
        if request.test_case_id == "case-1":
            return TestExecutionResult(status="success")
        return TestExecutionResult(status="failed", error_message="boom")

    monkeypatch.setattr(
        service.test_execution_service,
        "execute_test",
        fake_execute,
    )

    request = RegressionTestCreateData(
        agent_id="agent-1",
        model_name="override-model",
        system_prompt="override",
        model_settings={},
    )

    result = await service.run_regression_test(request)
    assert result.total_count == 2
    assert result.success_count == 1
    assert result.failed_count == 1
    assert result.status == "failed"
