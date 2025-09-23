from typing import Optional

import pytest

from src.agents.eval_agent import EvalAgentOutput
from src.services.evaluation_service import EvaluationResult, EvaluationService
from src.services.evaluation_settings_service import EvaluationSettingsData


class FakeSettingsService:
    def __init__(self, model_name: str = "openai/gpt-4o-mini", provider: str = "openrouter"):
        self._data = EvaluationSettingsData(
            model_name=model_name,
            provider=provider,
            updated_at=None,
        )

    def get_settings(self) -> EvaluationSettingsData:
        return self._data

    def update_settings(self, *_args, **_kwargs) -> EvaluationSettingsData:  # pragma: no cover - not used
        raise NotImplementedError


class FakeAgentResult:
    def __init__(self, output: EvalAgentOutput):
        self.output = output


class FakeAgent:
    def __init__(self, output: EvalAgentOutput):
        self.output = output
        self.last_prompt: Optional[str] = None

    async def run(self, prompt: str) -> FakeAgentResult:
        self.last_prompt = prompt
        return FakeAgentResult(self.output)


@pytest.mark.asyncio
async def test_evaluate_handles_missing_response():
    service = EvaluationService(settings_service=FakeSettingsService())

    result = await service.evaluate(
        actual_response=None,
        expectation="Must mention delivery",
        reference_response="Sample",
        test_case_name="Case A",
    )

    assert isinstance(result, EvaluationResult)
    assert result.passed is False
    assert "No LLM response" in result.feedback
    assert result.metadata.get("reason") == "missing_response"


@pytest.mark.asyncio
async def test_evaluate_uses_agent_output(monkeypatch):
    service = EvaluationService(settings_service=FakeSettingsService())

    agent_output = EvalAgentOutput(
        passed=True,
        feedback="All acceptance criteria satisfied.",
        satisfied_criteria=["pricing"],
        missing_criteria=[],
    )

    fake_agent = FakeAgent(agent_output)

    async def fake_get_agent(model_name: str):  # pragma: no cover - replaced function
        assert model_name == "openai/gpt-4o-mini"
        return fake_agent

    monkeypatch.setattr(service, "_get_agent", fake_get_agent)

    result = await service.evaluate(
        actual_response="Here is pricing and delivery info",
        expectation="Mention pricing and delivery",
        reference_response="Pricing is X",
        test_case_name="Case B",
    )

    assert result.passed is True
    assert "acceptance criteria" in result.feedback.lower()
    assert result.metadata["satisfied_criteria"] == ["pricing"]
    assert fake_agent.last_prompt is not None
