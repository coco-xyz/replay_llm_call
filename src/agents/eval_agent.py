"""Evaluation agent definition."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models import Model

EVAL_SYSTEM_PROMPT = """
You are an impartial judge that evaluates whether an AI assistant's response satisfies
explicit acceptance criteria. Follow these principles:

1. The acceptance criteria (if provided) are the source of truth. Every critical requirement
   must be satisfied. Missing or contradicting information means failure.
2. The reference response is optional guidance for tone or structure. Do not require exact
   wording if the acceptance criteria are satisfied.
3. If no acceptance criteria exist, infer them from the reference response when reasonable
   and focus on factual accuracy and usefulness.
4. Respond succinctly, referencing concrete issues.
""".strip()


class EvalAgentOutput(BaseModel):
    """Structured result returned by the evaluation agent."""

    passed: bool = Field(
        ..., description="Whether the actual response satisfies requirements"
    )
    feedback: str = Field(..., description="Brief explanation of the judgement")
    satisfied_criteria: List[str] = Field(
        default_factory=list,
        description="Specific criteria that were satisfied",
    )
    missing_criteria: List[str] = Field(
        default_factory=list,
        description="Specific criteria that were missing or incorrect",
    )


def create_evaluation_agent(model: Model) -> Agent[EvalAgentOutput]:
    """Instantiate a pydantic-ai agent for response evaluation."""

    return Agent(
        model=model,
        result_type=EvalAgentOutput,
        system_prompt=EVAL_SYSTEM_PROMPT,
    )


__all__ = ["EvalAgentOutput", "create_evaluation_agent"]
