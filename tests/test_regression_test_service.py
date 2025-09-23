from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src.services.regression_test_service import (
    RegressionTestCreateData,
    RegressionTestService,
)
from src.services.test_execution_service import ExecutionResult


def _build_stateful_store(monkeypatch, service):
    state = {}

    def fake_create(record):
        now = datetime.now(timezone.utc)
        record.created_at = now
        record.updated_at = now
        state[record.id] = record
        return record

    def fake_update(record):
        record.updated_at = datetime.now(timezone.utc)
        state[record.id] = record
        return record

    def fake_get(regression_id, include_deleted=False):
        return state.get(regression_id)

    monkeypatch.setattr(service.store, "create", fake_create)
    monkeypatch.setattr(service.store, "update", fake_update)
    monkeypatch.setattr(service.store, "get_by_id", fake_get)

    return state


def test_create_regression_with_no_cases(monkeypatch):
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

    state = _build_stateful_store(monkeypatch, service)

    request = RegressionTestCreateData(
        agent_id="agent-1",
        model_name_override="model",
        system_prompt_override="prompt",
        model_settings_override={},
    )

    result = service.create_regression(request)
    assert result.status == "completed"
    assert result.total_count == 0
    assert result.success_count == 0
    assert result.failed_count == 0
    assert result.passed_count == 0
    assert result.declined_count == 0
    assert result.unknown_count == 0
    stored = state[result.id]
    assert stored.status == "completed"
    assert stored.passed_count == 0
    assert stored.declined_count == 0
    assert stored.unknown_count == 0


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
    state = _build_stateful_store(monkeypatch, service)

    async def fake_execute(request):
        if request.test_case_id == "case-1":
            return ExecutionResult(status="success", is_passed=True)
        return ExecutionResult(status="failed", error_message="boom", is_passed=False)

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

    created = service.create_regression(request)
    assert created.total_count == 2
    assert created.status == "pending"

    await service.execute_regression(created.id)

    stored = state[created.id]
    assert stored.total_count == 2
    assert stored.success_count == 1
    assert stored.failed_count == 1
    assert stored.passed_count == 1
    assert stored.declined_count == 1
    assert stored.unknown_count == 0
    assert stored.status == "failed"
