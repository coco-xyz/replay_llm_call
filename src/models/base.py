"""
Base Models

Base classes and common model utilities for replay-llm-call.
"""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.stores.database import Base


class TimestampMixin:
    """Mixin for models that need created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )


class BaseDBModel(Base, TimestampMixin):
    """Base model class with common fields and functionality."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(String, primary_key=True)


__all__ = ["Base", "BaseDBModel", "TimestampMixin"]