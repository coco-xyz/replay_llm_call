"""
Test Case Model

Data model for LLM test cases in the replay system.
"""

from typing import List, Optional

from sqlalchemy import JSON, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseDBModel


class TestCase(BaseDBModel):
    """
    Test case model for storing LLM test scenarios.
    
    Stores both raw logfire data and parsed components for efficient replay.
    Uses the optimized storage strategy where system prompt and last user message
    are separated from other messages for efficient replay reconstruction.
    """
    
    __tablename__ = "test_cases"
    
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
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Parsed key components for display and replay
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    last_user_message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Relationships
    test_logs: Mapped[List["TestLog"]] = relationship(
        "TestLog", 
        back_populates="test_case",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<TestCase(id='{self.id}', name='{self.name}')>"


__all__ = ["TestCase"]
