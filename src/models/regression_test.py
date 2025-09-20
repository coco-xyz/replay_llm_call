"""Regression test SQLAlchemy model."""

from typing import List, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseDBModel


class RegressionTest(BaseDBModel):
    """Represents a batched regression execution for a single agent."""

    __tablename__ = "regression_tests"

    agent_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agents.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    model_name_override: Mapped[str] = mapped_column(String(255), nullable=False)
    system_prompt_override: Mapped[str] = mapped_column(Text, nullable=False)
    model_settings_override: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )

    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)

    agent: Mapped["Agent"] = relationship(
        "Agent",
        back_populates="regression_tests",
    )
    test_logs: Mapped[List["TestLog"]] = relationship(
        "TestLog",
        back_populates="regression_test",
    )

    def __repr__(self) -> str:
        return (
            f"<RegressionTest(id='{self.id}', agent_id='{self.agent_id}', "
            f"status='{self.status}', total={self.total_count})>"
        )


__all__ = ["RegressionTest"]
