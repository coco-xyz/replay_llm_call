"""
Test Case Store

Data access layer for test case operations.
"""

from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.core.error_codes import DatabaseErrorCode
from src.core.exceptions import DatabaseException
from src.core.logger import get_logger
from src.models import TestCase
from src.stores.database import database_session

logger = get_logger(__name__)


class TestCaseStore:
    """Store class for test case data operations."""

    def create(self, test_case: TestCase) -> TestCase:
        """
        Create a new test case.
        
        Args:
            test_case: TestCase instance to create
            
        Returns:
            TestCase: Created test case
            
        Raises:
            DatabaseException: If creation fails
        """
        try:
            with database_session() as db:
                db.add(test_case)
                db.commit()
                db.refresh(test_case)
                logger.info(f"Created test case: {test_case.id}")
                return test_case
                
        except Exception as e:
            logger.error(f"Failed to create test case: {e}")
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to create test case: {str(e)}"
            ) from e

    def get_by_id(self, test_case_id: str) -> Optional[TestCase]:
        """
        Get test case by ID.

        Args:
            test_case_id: Test case ID

        Returns:
            TestCase or None if not found

        Raises:
            DatabaseException: If query fails
        """
        try:
            with database_session() as db:
                test_case = db.query(TestCase).filter(TestCase.id == test_case_id).first()
                if test_case:
                    logger.debug(f"Found test case: {test_case_id}")
                else:
                    logger.debug(f"Test case not found: {test_case_id}")
                return test_case
                
        except Exception as e:
            logger.error(f"Failed to get test case {test_case_id}: {e}")
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to get test case: {str(e)}"
            ) from e

    def get_all(self, limit: int = 100, offset: int = 0) -> List[TestCase]:
        """
        Get all test cases with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of test cases

        Raises:
            DatabaseException: If query fails
        """
        try:
            with database_session() as db:
                test_cases = (
                    db.query(TestCase)
                    .order_by(desc(TestCase.created_at))
                    .limit(limit)
                    .offset(offset)
                    .all()
                )
                logger.debug(f"Retrieved {len(test_cases)} test cases")
                return test_cases
                
        except Exception as e:
            logger.error(f"Failed to get test cases: {e}")
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to get test cases: {str(e)}"
            ) from e

    def update(self, test_case: TestCase) -> TestCase:
        """
        Update an existing test case.

        Args:
            test_case: TestCase instance to update

        Returns:
            TestCase: Updated test case

        Raises:
            DatabaseException: If update fails
        """
        try:
            with database_session() as db:
                # Merge the test case into the session
                merged_test_case = db.merge(test_case)
                db.commit()
                db.refresh(merged_test_case)
                logger.info(f"Updated test case: {merged_test_case.id}")
                return merged_test_case
                
        except Exception as e:
            logger.error(f"Failed to update test case {test_case.id}: {e}")
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to update test case: {str(e)}"
            ) from e

    def delete(self, test_case_id: str) -> bool:
        """
        Delete a test case by ID.

        Args:
            test_case_id: Test case ID to delete

        Returns:
            bool: True if deleted, False if not found

        Raises:
            DatabaseException: If deletion fails
        """
        try:
            with database_session() as db:
                test_case = db.query(TestCase).filter(TestCase.id == test_case_id).first()
                if test_case:
                    db.delete(test_case)
                    db.commit()
                    logger.info(f"Deleted test case: {test_case_id}")
                    return True
                else:
                    logger.debug(f"Test case not found for deletion: {test_case_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to delete test case {test_case_id}: {e}")
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to delete test case: {str(e)}"
            ) from e

    def search_by_name(self, name_pattern: str, limit: int = 50) -> List[TestCase]:
        """
        Search test cases by name pattern.

        Args:
            name_pattern: Pattern to search for in names
            limit: Maximum number of results

        Returns:
            List of matching test cases

        Raises:
            DatabaseException: If search fails
        """
        try:
            with database_session() as db:
                test_cases = (
                    db.query(TestCase)
                    .filter(TestCase.name.ilike(f"%{name_pattern}%"))
                    .order_by(desc(TestCase.created_at))
                    .limit(limit)
                    .all()
                )
                logger.debug(f"Found {len(test_cases)} test cases matching '{name_pattern}'")
                return test_cases
                
        except Exception as e:
            logger.error(f"Failed to search test cases: {e}")
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to search test cases: {str(e)}"
            ) from e


__all__ = ["TestCaseStore"]
