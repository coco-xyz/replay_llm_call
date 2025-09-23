"""Store for application settings persisted as JSON blobs."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.exc import SQLAlchemyError

from src.core.error_codes import DatabaseErrorCode
from src.core.exceptions import DatabaseException
from src.core.logger import get_logger
from src.models import AppSetting
from src.stores.database import database_session

logger = get_logger(__name__)


class AppSettingsStore:
    """CRUD operations for application-level settings."""

    def get_setting(self, key: str) -> Optional[AppSetting]:
        """Return a stored setting by key."""
        try:
            with database_session() as db:
                return db.query(AppSetting).filter(AppSetting.key == key).first()
        except SQLAlchemyError as exc:
            logger.error("Failed to load setting %s: %s", key, exc)
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to load setting: {key}",
            ) from exc

    def upsert_setting(self, key: str, value: dict) -> AppSetting:
        """Insert or update a setting atomically."""
        try:
            with database_session() as db:
                setting = db.query(AppSetting).filter(AppSetting.key == key).first()
                if setting is None:
                    setting = AppSetting(key=key, value=value)
                    db.add(setting)
                else:
                    setting.value = value
                db.commit()
                db.refresh(setting)
                logger.info("Persisted setting '%s'", key)
                return setting
        except SQLAlchemyError as exc:
            logger.error("Failed to persist setting %s: %s", key, exc)
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to persist setting: {key}",
            ) from exc


__all__ = ["AppSettingsStore"]
