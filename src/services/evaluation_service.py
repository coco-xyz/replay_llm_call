"""Service orchestrating evaluation agent runs."""

from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field

from src.agents.eval_agent import EvalAgentOutput, create_evaluation_agent
from src.core.logger import get_logger
from src.core.llm_registry import get_eval_model
from src.services.evaluation_settings_service import (
    EvaluationSettingsData,
    EvaluationSettingsService,
)

logger = get_logger(__name__)


class EvaluationResult(BaseModel):
    """Outcome of an evaluation agent run."""

    passed: bool = Field(..., description="Whether the evaluation marked the log as passing")
    feedback: str = Field(..., description="Human-readable evaluation summary")
    model_name: str = Field(..., description="Model identifier used for the evaluation agent")
    metadata: Dict = Field(default_factory=dict, description="Structured payload returned by the agent")


class EvaluationService:
    """High-level evaluation coordinator with caching."""

    def __init__(
        self,
        settings_service: Optional[EvaluationSettingsService] = None,
    ) -> None:
        self.settings_service = settings_service or EvaluationSettingsService()
        self._agent_cache: dict[str, object] = {}

    def get_settings(self) -> EvaluationSettingsData:
        """Expose the current evaluation configuration."""
        return self.settings_service.get_settings()

    async def evaluate(
        self,
        *,
        actual_response: Optional[str],
        expectation: Optional[str],
        reference_response: Optional[str],
        test_case_name: Optional[str],
        settings: Optional[EvaluationSettingsData] = None,
    ) -> EvaluationResult:
        """Run the evaluation agent and return a normalized result."""
        cfg = settings or self.get_settings()
        model_name = cfg.model_name

        if actual_response is None or not actual_response.strip():
            feedback = "No LLM response was produced to evaluate."
            metadata = {"reason": "missing_response"}
            return EvaluationResult(
                passed=False,
                feedback=feedback,
                model_name=model_name,
                metadata=metadata,
            )

        agent = await self._get_agent(model_name)
        prompt = self._build_prompt(
            actual_response=actual_response,
            expectation=expectation,
            reference_response=reference_response,
            test_case_name=test_case_name,
        )

        try:
            result = await agent.run(prompt)
            output: EvalAgentOutput = result.output
            metadata = output.model_dump()
            feedback = output.feedback.strip() or "Evaluation completed without additional feedback."
            return EvaluationResult(
                passed=bool(output.passed),
                feedback=feedback,
                model_name=model_name,
                metadata=metadata,
            )
        except Exception as exc:  # pragma: no cover - defensive against runtime LLM issues
            logger.error("Evaluation agent failed: %s", exc, exc_info=True)
            return EvaluationResult(
                passed=False,
                feedback=f"Evaluation failed due to error: {exc}",
                model_name=model_name,
                metadata={"error": str(exc)},
            )

    async def _get_agent(self, model_name: str):
        agent = self._agent_cache.get(model_name)
        if agent is not None:
            return agent

        model = get_eval_model(model_name)
        agent = create_evaluation_agent(model)
        self._agent_cache[model_name] = agent
        return agent

    @staticmethod
    def _build_prompt(
        *,
        actual_response: str,
        expectation: Optional[str],
        reference_response: Optional[str],
        test_case_name: Optional[str],
    ) -> str:
        sections = []
        if test_case_name:
            sections.append(
                "Test Case Name:\n"
                + f"""\n{test_case_name.strip()}\n"""
            )

        if expectation:
            sections.append(
                "Acceptance Criteria:\n"
                + f"""\n{expectation.strip()}\n"""
            )
        else:
            sections.append(
                "Acceptance Criteria:\n" """\nNo explicit criteria were provided. Derive expectations from the reference response if available and ensure factual correctness.\n"""
            )

        if reference_response:
            sections.append(
                "Reference Response (if helpful):\n"
                + f"""\n{reference_response.strip()}\n"""
            )
        else:
            sections.append(
                "Reference Response (if helpful):\n" """\nNot provided. Focus on the acceptance criteria above.\n"""
            )

        sections.append(
            "Actual Response to Evaluate:\n"
            + f"""\n{actual_response.strip()}\n"""
        )

        instruction = (
            "Determine if the actual response satisfies the acceptance criteria. "
            "If any critical requirement is missing or incorrect, mark it as failed. "
            "Respond concisely with your judgement."
        )
        sections.append(instruction)
        return "\n\n".join(sections)


__all__ = ["EvaluationService", "EvaluationResult"]
