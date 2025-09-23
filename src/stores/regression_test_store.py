"""Regression test persistence layer."""

from typing import List, Optional

from sqlalchemy import desc

from src.core.error_codes import DatabaseErrorCode
from src.core.exceptions import DatabaseException
from src.core.logger import get_logger
from src.models import RegressionTest
from src.stores.database import database_session

logger = get_logger(__name__)


class RegressionTestStore:
    """Store class for regression test records."""

    def create(self, regression_test: RegressionTest) -> RegressionTest:
        try:
            with database_session() as db:
                db.add(regression_test)
                db.commit()
                db.refresh(regression_test)
                logger.info("Created regression test %s", regression_test.id)
                return regression_test
        except Exception as exc:  # pragma: no cover - consistent error handling
            logger.error("Failed to create regression test: %s", exc)
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to create regression test: {exc}",
            ) from exc

    def update(self, regression_test: RegressionTest) -> RegressionTest:
        try:
            with database_session() as db:
                merged = db.merge(regression_test)
                db.commit()
                db.refresh(merged)
                logger.info("Updated regression test %s", merged.id)
                return merged
        except Exception as exc:  # pragma: no cover
            logger.error(
                "Failed to update regression test %s: %s", regression_test.id, exc
            )
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to update regression test: {exc}",
            ) from exc

    def get_by_id(
        self, regression_test_id: str, *, include_deleted: bool = False
    ) -> Optional[RegressionTest]:
        try:
            with database_session() as db:
                query = db.query(RegressionTest).filter(
                    RegressionTest.id == regression_test_id
                )
                if not include_deleted:
                    query = query.filter(RegressionTest.is_deleted.is_(False))
                return query.first()
        except Exception as exc:  # pragma: no cover
            logger.error(
                "Failed to fetch regression test %s: %s", regression_test_id, exc
            )
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to fetch regression test: {exc}",
            ) from exc

    def list_regression_tests(
        self,
        *,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> List[RegressionTest]:
        try:
            with database_session() as db:
                query = db.query(RegressionTest)
                if agent_id:
                    query = query.filter(RegressionTest.agent_id == agent_id)
                if status:
                    query = query.filter(RegressionTest.status == status)
                if not include_deleted:
                    query = query.filter(RegressionTest.is_deleted.is_(False))
                return (
                    query.order_by(desc(RegressionTest.created_at))
                    .limit(limit)
                    .offset(offset)
                    .all()
                )
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to list regression tests: %s", exc)
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to list regression tests: {exc}",
            ) from exc

    def soft_delete_by_agent(self, agent_id: str) -> int:
        """Soft delete regression tests tied to the given agent."""

        try:
            with database_session() as db:
                updated = (
                    db.query(RegressionTest)
                    .filter(RegressionTest.agent_id == agent_id)
                    .filter(RegressionTest.is_deleted.is_(False))
                    .update(
                        {RegressionTest.is_deleted: True}, synchronize_session=False
                    )
                )
                db.commit()
                logger.info(
                    "Soft deleted %s regression tests for agent %s", updated, agent_id
                )
                return updated
        except Exception as exc:  # pragma: no cover
            logger.error(
                "Failed to soft delete regression tests for agent %s: %s", agent_id, exc
            )
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to delete regression tests for agent: {exc}",
            ) from exc


__all__ = ["RegressionTestStore"]
