"""Test Log SQLAlchemy model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseDBModel

if TYPE_CHECKING:  # pragma: no cover - imports only needed for type checking
    from .agent import Agent
    from .regression_test import RegressionTest
    from .test_case import TestCase


class TestLog(BaseDBModel):
    """Test log model for storing LLM test execution results."""

    __tablename__ = "test_logs"

    # Reference to the test case and agent
    test_case_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agents.id"),
        nullable=False,
    )
    regression_test_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("regression_tests.id"),
        nullable=True,
    )

    # Model information
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Input data (actual parameters used in execution, may be modified by user)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    tools: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Output data
    llm_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_example: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_expectation_snapshot: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_passed: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True, default=None
    )
    evaluation_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluation_model_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    evaluation_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Execution status (synchronous execution: success or failed)
    status: Mapped[str] = mapped_column(String(20), default="success", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    test_case: Mapped["TestCase"] = relationship(
        "TestCase",
        back_populates="test_logs",
    )
    agent: Mapped["Agent"] = relationship(
        "Agent",
        back_populates="test_logs",
    )
    regression_test: Mapped[Optional["RegressionTest"]] = relationship(
        "RegressionTest",
        back_populates="test_logs",
    )

    def __repr__(self) -> str:
        return (
            f"<TestLog(id='{self.id}', test_case_id='{self.test_case_id}', "
            f"agent_id='{self.agent_id}', status='{self.status}')>"
        )


__all__ = ["TestLog"]
