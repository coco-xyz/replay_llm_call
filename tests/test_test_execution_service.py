from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src.services.test_execution_service import ExecutionService, TestExecutionData


class DummyTestCaseService:
    def get_test_case_for_execution(self, test_case_id):
        assert test_case_id == "case-123"
        return SimpleNamespace(
            id=test_case_id,
            agent_id="agent-1",
            model_name="gpt-4",
            model_settings={"temperature": 0.1},
            system_prompt="system prompt",
            last_user_message="user message",
            middle_messages=[],
            tools=None,
            response_expectation=None,
            response_example=None,
            name="Example Case",
        )


class DummyAgentService:
    def get_active_agent_or_raise(self, agent_id):
        assert agent_id == "agent-1"
        return SimpleNamespace(
            id=agent_id,
            default_model_name="gpt-4",
            default_system_prompt="default prompt",
            default_model_settings={"temperature": 0.2},
        )


class DummyEvaluationService:
    def __init__(self):
        self.called = False

    def get_settings(self):
        return SimpleNamespace(model_name="eval-agent")

    async def evaluate(self, **_):  # pragma: no cover - should not be called
        self.called = True
        return SimpleNamespace(
            passed=True,
            feedback="Would have passed",
            model_name="eval-agent",
            metadata={},
        )


class DummyTestLogStore:
    def __init__(self):
        self.saved_log = None

    def create(self, test_log):
        self.saved_log = test_log
        test_log.created_at = datetime.now(timezone.utc)
        return test_log


@pytest.mark.asyncio
async def test_execute_test_marks_unknown_when_expectations_missing(monkeypatch):
    async def fake_execute_llm_test(**_):
        return "assistant response"

    monkeypatch.setattr(
        "src.services.test_execution_service.execute_llm_test",
        fake_execute_llm_test,
    )

    service = ExecutionService()
    service.test_case_service = DummyTestCaseService()
    service.agent_service = DummyAgentService()
    evaluation_service = DummyEvaluationService()
    service.evaluation_service = evaluation_service
    store = DummyTestLogStore()
    service.test_log_store = store

    request = TestExecutionData(test_case_id="case-123")
    result = await service.execute_test(request)

    assert result.is_passed is None
    assert result.evaluation_model_name is None
    assert "Evaluation skipped" in (result.evaluation_feedback or "")
    assert evaluation_service.called is False
    assert store.saved_log is not None
    assert store.saved_log.is_passed is None
