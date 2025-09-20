"""Agent SQLAlchemy model."""

from typing import List, Optional

from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseDBModel


class Agent(BaseDBModel):
    """Represents a logical LLM agent that groups test cases."""

    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_model_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    default_system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_model_settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    test_cases: Mapped[List["TestCase"]] = relationship(
        "TestCase",
        back_populates="agent",
    )
    regression_tests: Mapped[List["RegressionTest"]] = relationship(
        "RegressionTest",
        back_populates="agent",
    )
    test_logs: Mapped[List["TestLog"]] = relationship(
        "TestLog",
        back_populates="agent",
    )

    def __repr__(self) -> str:
        status = "deleted" if self.is_deleted else "active"
        return f"<Agent(id='{self.id}', name='{self.name}', status='{status}')>"


__all__ = ["Agent"]
