"""Test Case SQLAlchemy model."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseDBModel

if TYPE_CHECKING:  # pragma: no cover - imports only needed for type checking
    from .agent import Agent
    from .test_log import TestLog


class TestCase(BaseDBModel):
    """Test case model for storing LLM test scenarios."""

    __tablename__ = "test_cases"

    # Agent relationship
    agent_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agents.id"),
        nullable=False,
    )

    # Basic information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Raw data storage (for audit and reference)
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Separated storage for efficient replay
    # middle_messages contains all messages EXCEPT the first system prompt
    # and the last user message (which are stored separately below)
    middle_messages: Mapped[List[dict]] = mapped_column(JSON, nullable=False)
    tools: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Parsed key components for display and replay
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    last_user_message: Mapped[str] = mapped_column(Text, nullable=False)
    response_example: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_expectation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Soft delete flag
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Relationships
    agent: Mapped["Agent"] = relationship(
        "Agent",
        back_populates="test_cases",
    )
    test_logs: Mapped[List["TestLog"]] = relationship(
        "TestLog",
        back_populates="test_case",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<TestCase(id='{self.id}', name='{self.name}', agent_id='{self.agent_id}')>"


__all__ = ["TestCase"]
