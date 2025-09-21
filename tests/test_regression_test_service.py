from datetime import datetime, timezone
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
        name="Agent 1",
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

    def fake_create(record):
        now = datetime.now(timezone.utc)
        record.created_at = now
        record.updated_at = now
        return record

    def fake_update(record):
        record.updated_at = datetime.now(timezone.utc)
        return record

    monkeypatch.setattr(service.store, "create", fake_create)
    monkeypatch.setattr(service.store, "update", fake_update)

    request = RegressionTestCreateData(
        agent_id="agent-1",
        model_name_override="model",
        system_prompt_override="prompt",
        model_settings_override={},
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
        name="Agent 1",
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
    def fake_create(record):
        now = datetime.now(timezone.utc)
        record.created_at = now
        record.updated_at = now
        return record

    def fake_update(record):
        record.updated_at = datetime.now(timezone.utc)
        return record

    monkeypatch.setattr(service.store, "create", fake_create)
    monkeypatch.setattr(service.store, "update", fake_update)

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
        model_name_override="override-model",
        system_prompt_override="override",
        model_settings_override={},
    )

    result = await service.run_regression_test(request)
    assert result.total_count == 2
    assert result.success_count == 1
    assert result.failed_count == 1
    assert result.status == "failed"
