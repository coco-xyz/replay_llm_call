"""Application setting SQLAlchemy model."""

from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class AppSetting(Base, TimestampMixin):
    """Simple key-value settings store backed by JSON payloads."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<AppSetting(key='{self.key}')>"


__all__ = ["AppSetting"]
