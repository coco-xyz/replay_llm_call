"""Test Log Store.

Data access layer for test log operations.

The list-style queries in this store deliberately exclude logs that belong to
soft-deleted test cases so that UI listings stay in sync with the visible test
case catalog. Individual log lookups remain unrestricted and can still access
records tied to deleted test cases.
"""

from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.core.error_codes import DatabaseErrorCode
from src.core.exceptions import DatabaseException
from src.core.logger import get_logger
from src.models import TestCase, TestLog
from src.stores.database import database_session

logger = get_logger(__name__)


class TestLogStore:
    """Store class for test log data operations."""

    def create(self, test_log: TestLog) -> TestLog:
        """
        Create a new test log.

        Args:
            test_log: TestLog instance to create

        Returns:
            TestLog: Created test log

        Raises:
            DatabaseException: If creation fails
        """
        try:
            with database_session() as db:
                db.add(test_log)
                db.commit()
                db.refresh(test_log)
                logger.info("Created test log: %s", test_log.id)
                return test_log

        except Exception as e:
            logger.error(f"Failed to create test log: {e}")
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED, f"Failed to create test log: {str(e)}"
            ) from e

    def get_by_id(self, test_log_id: str) -> Optional[TestLog]:
        """
        Get test log by ID.

        Args:
            test_log_id: Test log ID

        Returns:
            TestLog or None if not found

        Raises:
            DatabaseException: If query fails
        """
        try:
            with database_session() as db:
                test_log = db.query(TestLog).filter(TestLog.id == test_log_id).first()
                if test_log:
                    logger.debug("Found test log: %s", test_log_id)
                else:
                    logger.debug("Test log not found: %s", test_log_id)
                return test_log

        except Exception as e:
            logger.error(f"Failed to get test log {test_log_id}: {e}")
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED, f"Failed to get test log: {str(e)}"
            ) from e

    def get_by_test_case_id(
        self, test_case_id: str, limit: int = 20, offset: int = 0
    ) -> List[TestLog]:
        """
        Get test logs by test case ID with pagination.

        Args:
            test_case_id: Test case ID to filter by
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of test logs for the test case

        Raises:
            DatabaseException: If query fails
        """
        try:
            with database_session() as db:
                test_logs = (
                    db.query(TestLog)
                    .filter(TestLog.test_case_id == test_case_id)
                    .order_by(desc(TestLog.created_at))
                    .limit(limit)
                    .offset(offset)
                    .all()
                )
                logger.debug(
                    "Retrieved %s test logs for case %s", len(test_logs), test_case_id
                )
                return test_logs

        except Exception as e:
            logger.error(f"Failed to get test logs for case {test_case_id}: {e}")
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED, f"Failed to get test logs: {str(e)}"
            ) from e

    def _query_with_active_test_cases(self, db: Session):
        """Return a base query scoped to logs whose test cases are not deleted."""

        return (
            db.query(TestLog)
            .join(TestLog.test_case)
            .filter(TestCase.is_deleted.is_(False))
        )

    def get_all(self, limit: int = 20, offset: int = 0) -> List[TestLog]:
        """
        Get all test logs with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of test logs

        Raises:
            DatabaseException: If query fails
        """
        try:
            with database_session() as db:
                query = self._query_with_active_test_cases(db)
                test_logs = (
                    query.order_by(desc(TestLog.created_at))
                    .limit(limit)
                    .offset(offset)
                    .all()
                )
                logger.debug(f"Retrieved {len(test_logs)} test logs")
                return test_logs

        except Exception as e:
            logger.error(f"Failed to get test logs: {e}")
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED, f"Failed to get test logs: {str(e)}"
            ) from e

    def get_by_status(
        self,
        status: str,
        limit: int = 20,
        offset: int = 0,
        agent_id: Optional[str] = None,
        regression_test_id: Optional[str] = None,
    ) -> List[TestLog]:
        """
        Get test logs by status with pagination.

        Args:
            status: Status to filter by (success, failed)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of test logs with the specified status

        Raises:
            DatabaseException: If query fails
        """
        try:
            with database_session() as db:
                query = self._query_with_active_test_cases(db)
                query = query.filter(TestLog.status == status)
                if agent_id:
                    query = query.filter(TestLog.agent_id == agent_id)
                if regression_test_id:
                    query = query.filter(
                        TestLog.regression_test_id == regression_test_id
                    )
                test_logs = (
                    query.order_by(desc(TestLog.created_at))
                    .limit(limit)
                    .offset(offset)
                    .all()
                )
                logger.debug(
                    "Retrieved %s test logs with status %s", len(test_logs), status
                )
                return test_logs

        except Exception as e:
            logger.error(f"Failed to get test logs by status {status}: {e}")
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to get test logs by status: {str(e)}",
            ) from e

    def get_filtered(
        self,
        status: Optional[str] = None,
        model_name: Optional[str] = None,
        test_case_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        regression_test_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[TestLog]:
        """
        Get test logs with combined filters.

        Args:
            status: Optional status filter
            test_case_id: Optional test case ID filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List[TestLog]: Filtered test logs

        Raises:
            DatabaseException: If query fails
        """
        try:
            with database_session() as db:
                query = self._query_with_active_test_cases(db)

                # Apply filters
                if status:
                    query = query.filter(TestLog.status == status)
                if model_name:
                    query = query.filter(TestLog.model_name == model_name)
                if test_case_id:
                    query = query.filter(TestLog.test_case_id == test_case_id)
                if agent_id:
                    query = query.filter(TestLog.agent_id == agent_id)
                if regression_test_id:
                    query = query.filter(
                        TestLog.regression_test_id == regression_test_id
                    )

                test_logs = (
                    query.order_by(desc(TestLog.created_at))
                    .limit(limit)
                    .offset(offset)
                    .all()
                )
                logger.debug("Retrieved %s filtered test logs", len(test_logs))
                return test_logs

        except Exception as e:
            logger.error(f"Failed to get filtered test logs: {e}")
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to get filtered test logs: {str(e)}",
            ) from e

    def get_by_regression_test(
        self,
        regression_test_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> List[TestLog]:
        """Return logs that belong to a specific regression test."""

        try:
            with database_session() as db:
                query = self._query_with_active_test_cases(db)
                test_logs = (
                    query.filter(TestLog.regression_test_id == regression_test_id)
                    .order_by(desc(TestLog.created_at))
                    .limit(limit)
                    .offset(offset)
                    .all()
                )
                logger.debug(
                    "Retrieved %s logs for regression test %s",
                    len(test_logs),
                    regression_test_id,
                )
                return test_logs
        except Exception as e:  # pragma: no cover
            logger.error(
                "Failed to get logs for regression test %s: %s", regression_test_id, e
            )
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to get regression test logs: {str(e)}",
            ) from e

    def delete(self, test_log_id: str) -> bool:
        """
        Delete a test log by ID.

        Args:
            test_log_id: Test log ID to delete

        Returns:
            bool: True if deleted, False if not found

        Raises:
            DatabaseException: If deletion fails
        """
        try:
            with database_session() as db:
                test_log = db.query(TestLog).filter(TestLog.id == test_log_id).first()
                if test_log:
                    db.delete(test_log)
                    db.commit()
                    logger.info("Deleted test log: %s", test_log_id)
                    return True
                else:
                    logger.debug("Test log not found for deletion: %s", test_log_id)
                    return False

        except Exception as e:
            logger.error(f"Failed to delete test log {test_log_id}: {e}")
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED, f"Failed to delete test log: {str(e)}"
            ) from e

    def delete_by_test_case_id(self, test_case_id: str) -> int:
        """
        Delete all test logs for a test case.

        Args:
            test_case_id: Test case ID

        Returns:
            int: Number of deleted test logs

        Raises:
            DatabaseException: If deletion fails
        """
        try:
            with database_session() as db:
                deleted_count = (
                    db.query(TestLog)
                    .filter(TestLog.test_case_id == test_case_id)
                    .delete()
                )
                db.commit()
                logger.info(
                    "Deleted %s test logs for case %s", deleted_count, test_case_id
                )
                return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete test logs for case {test_case_id}: {e}")
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED, f"Failed to delete test logs: {str(e)}"
            ) from e


__all__ = ["TestLogStore"]
