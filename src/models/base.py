"""
Base Models

Base classes and common model utilities for replay-llm-call.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.stores.database import Base


class TimestampMixin:
    """Mixin for models that need created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class BaseDBModel(Base, TimestampMixin):
    """Base model class with common fields and functionality."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(String, primary_key=True)


__all__ = ["Base", "BaseDBModel", "TimestampMixin"]
