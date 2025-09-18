"""
Test Log Service

Service for viewing and filtering test execution logs.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from src.core.logger import get_logger
from src.stores.test_log_store import TestLogStore

logger = get_logger(__name__)

class TestLogData(BaseModel):
    """Service layer representation of a test log."""

    id: str = Field(..., description="Test log ID")
    test_case_id: str = Field(..., description="Associated test case ID")
    model_name: str = Field(..., description="Model used for execution")
    model_settings: Optional[Dict] = Field(None, description="Model settings JSON used for execution")
    system_prompt: str = Field(..., description="System prompt used")
    user_message: str = Field(..., description="User message used")
    tools: Optional[List[Dict]] = Field(None, description="Tools configuration used")
    llm_response: Optional[str] = Field(None, description="LLM response text")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")
    status: str = Field(..., description="Execution status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    # Additional service-layer specific fields
    execution_metadata: Optional[Dict] = Field(None, description="Execution metadata")
    performance_data: Optional[Dict] = Field(None, description="Performance analysis data")
    
    class Config:
        from_attributes = True


class TestLogService:
    """Service class for test log business logic."""

    def __init__(self):
        self.store = TestLogStore()

    def get_test_log(self, log_id: str) -> Optional[TestLogData]:
        """
        Get a test log by ID.
        
        Args:
            log_id: Test log ID
            
        Returns:
            TestLogData or None if not found
        """
        try:
            test_log = self.store.get_by_id(log_id)
            if not test_log:
                logger.debug(f"Test log not found: {log_id}")
                return None
            
            return TestLogData(
                id=test_log.id,
                test_case_id=test_log.test_case_id,
                model_name=test_log.model_name,
                model_settings=test_log.model_settings,
                system_prompt=test_log.system_prompt,
                user_message=test_log.user_message,
                tools=test_log.tools,
                llm_response=test_log.llm_response,
                response_time_ms=test_log.response_time_ms,
                status=test_log.status,
                error_message=test_log.error_message,
                created_at=test_log.created_at
            )
            
        except Exception as e:
            logger.error(f"Failed to get test log {log_id}: {e}")
            raise

    def get_logs_by_test_case(
        self, 
        test_case_id: str, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[TestLogData]:
        """
        Get test logs for a specific test case.
        
        Args:
            test_case_id: Test case ID to filter by
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of test log responses
        """
        try:
            test_logs = self.store.get_by_test_case_id(
                test_case_id=test_case_id,
                limit=limit,
                offset=offset
            )
            
            return [
                TestLogData(
                    id=log.id,
                    test_case_id=log.test_case_id,
                    model_name=log.model_name,
                    model_settings=log.model_settings,
                    system_prompt=log.system_prompt,
                    user_message=log.user_message,
                    tools=log.tools,
                    llm_response=log.llm_response,
                    response_time_ms=log.response_time_ms,
                    status=log.status,
                    error_message=log.error_message,
                    created_at=log.created_at
                )
                for log in test_logs
            ]
            
        except Exception as e:
            logger.error(f"Failed to get logs for test case {test_case_id}: {e}")
            raise

    def get_all_logs(self, limit: int = 100, offset: int = 0) -> List[TestLogData]:
        """
        Get all test logs with pagination.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of test log responses
        """
        try:
            test_logs = self.store.get_all(limit=limit, offset=offset)
            
            return [
                TestLogData(
                    id=log.id,
                    test_case_id=log.test_case_id,
                    model_name=log.model_name,
                    model_settings=log.model_settings,
                    system_prompt=log.system_prompt,
                    user_message=log.user_message,
                    tools=log.tools,
                    llm_response=log.llm_response,
                    response_time_ms=log.response_time_ms,
                    status=log.status,
                    error_message=log.error_message,
                    created_at=log.created_at
                )
                for log in test_logs
            ]
            
        except Exception as e:
            logger.error(f"Failed to get all test logs: {e}")
            raise

    def get_logs_by_status(
        self, 
        status: str, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[TestLogData]:
        """
        Get test logs filtered by status.
        
        Args:
            status: Status to filter by (success, failed)
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of test log responses with the specified status
        """
        try:
            test_logs = self.store.get_by_status(
                status=status,
                limit=limit,
                offset=offset
            )
            
            return [
                TestLogData(
                    id=log.id,
                    test_case_id=log.test_case_id,
                    model_name=log.model_name,
                    model_settings=log.model_settings,
                    system_prompt=log.system_prompt,
                    user_message=log.user_message,
                    tools=log.tools,
                    llm_response=log.llm_response,
                    response_time_ms=log.response_time_ms,
                    status=log.status,
                    error_message=log.error_message,
                    created_at=log.created_at
                )
                for log in test_logs
            ]
            
        except Exception as e:
            logger.error(f"Failed to get logs by status {status}: {e}")
            raise

    def get_success_logs(self, limit: int = 100, offset: int = 0) -> List[TestLogData]:
        """
        Get successful test logs.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of successful test log responses
        """
        return self.get_logs_by_status("success", limit=limit, offset=offset)

    def get_failed_logs(self, limit: int = 100, offset: int = 0) -> List[TestLogData]:
        """
        Get failed test logs.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of failed test log responses
        """
        return self.get_logs_by_status("failed", limit=limit, offset=offset)

    def get_logs_filtered(
        self,
        status: Optional[str] = None,
        test_case_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TestLogData]:
        """
        Get test logs with combined filters.

        Args:
            status: Optional status filter
            test_case_id: Optional test case ID filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of filtered test log responses
        """
        try:
            test_logs = self.store.get_filtered(
                status=status,
                test_case_id=test_case_id,
                limit=limit,
                offset=offset
            )

            return [
                TestLogData(
                    id=log.id,
                    test_case_id=log.test_case_id,
                    model_name=log.model_name,
                    model_settings=log.model_settings,
                    system_prompt=log.system_prompt,
                    user_message=log.user_message,
                    tools=log.tools,
                    llm_response=log.llm_response,
                    response_time_ms=log.response_time_ms,
                    status=log.status,
                    error_message=log.error_message,
                    created_at=log.created_at
                ) for log in test_logs
            ]

        except Exception as e:
            logger.error(f"Failed to get filtered logs: {e}")
            raise

    def delete_test_log(self, log_id: str) -> bool:
        """
        Delete a test log by ID.
        
        Args:
            log_id: Test log ID to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        try:
            deleted = self.store.delete(log_id)
            if deleted:
                logger.info(f"Test log deleted successfully: {log_id}")
            else:
                logger.debug(f"Test log not found for deletion: {log_id}")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete test log {log_id}: {e}")
            raise

    def delete_logs_by_test_case(self, test_case_id: str) -> int:
        """
        Delete all test logs for a test case.
        
        Args:
            test_case_id: Test case ID
            
        Returns:
            int: Number of deleted test logs
        """
        try:
            deleted_count = self.store.delete_by_test_case_id(test_case_id)
            logger.info(f"Deleted {deleted_count} test logs for case {test_case_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete logs for test case {test_case_id}: {e}")
            raise

    def get_log_statistics(self) -> dict:
        """
        Get statistics about test logs.
        
        Returns:
            Dict with log statistics
        """
        try:
            # Get counts by status
            success_logs = self.store.get_by_status("success", limit=1)
            failed_logs = self.store.get_by_status("failed", limit=1)
            all_logs = self.store.get_all(limit=1)
            
            # For a more accurate count, we'd need to implement count methods
            # For now, we'll use the length of limited results as approximation
            return {
                "total_logs": len(all_logs),  # This is not accurate for large datasets
                "success_count": len(success_logs),  # This is not accurate
                "failed_count": len(failed_logs),  # This is not accurate
                "success_rate": 0.0  # Would need proper counts to calculate
            }
            
        except Exception as e:
            logger.error(f"Failed to get log statistics: {e}")
            return {
                "total_logs": 0,
                "success_count": 0,
                "failed_count": 0,
                "success_rate": 0.0
            }


__all__ = ["TestLogService"]
