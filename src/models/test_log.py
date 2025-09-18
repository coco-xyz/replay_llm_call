"""
Test Log Model

Data model for LLM test execution logs in the replay system.
"""

from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseDBModel


class TestLog(BaseDBModel):
    """
    Test log model for storing LLM test execution results.
    
    Records the actual execution parameters (which may be modified from the original)
    and the results of the LLM call.
    """
    
    __tablename__ = "test_logs"
    
    # Reference to the test case
    test_case_id: Mapped[str] = mapped_column(
        String, 
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False
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
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Execution status (synchronous execution: success or failed)
    status: Mapped[str] = mapped_column(String(20), default="success", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    test_case: Mapped["TestCase"] = relationship(
        "TestCase", 
        back_populates="test_logs"
    )
    
    def __repr__(self) -> str:
        return (
            f"<TestLog(id='{self.id}', "
            f"test_case_id='{self.test_case_id}', "
            f"status='{self.status}')>"
        )


__all__ = ["TestLog"]
