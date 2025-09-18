"""
Test Case Service

Business logic service for test case operations.
Handles creation, retrieval, updating, and deletion of test cases with parsing.
"""

from datetime import datetime
import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from src.core.logger import get_logger
from src.models import TestCase
from src.services.llm_parser_service import parse_llm_raw_data, validate_raw_data_format
from src.stores.test_case_store import TestCaseStore

logger = get_logger(__name__)

class TestCaseCreateData(BaseModel):
    """Service layer data for creating a test case."""
    
    name: str = Field(..., description="Test case name")
    raw_data: Dict = Field(..., description="Raw logfire data")
    description: Optional[str] = Field(None, description="Test case description")

class TestCaseUpdateData(BaseModel):
    """Service layer data for updating a test case."""

    name: Optional[str] = Field(None, description="Updated test case name")
    raw_data: Optional[Dict] = Field(None, description="Updated raw logfire data")
    description: Optional[str] = Field(None, description="Updated test case description")
    system_prompt: Optional[str] = Field(None, description="Updated system prompt")
    last_user_message: Optional[str] = Field(None, description="Updated user message")

class TestCaseData(BaseModel):
    """Service layer representation of a test case."""

    id: str = Field(..., description="Test case ID")
    name: str = Field(..., description="Test case name")
    description: Optional[str] = Field(None, description="Test case description")
    raw_data: Dict = Field(..., description="Raw logfire data")
    middle_messages: List[Dict] = Field(..., description="Middle messages for replay")
    tools: Optional[List[Dict]] = Field(None, description="Tools configuration")
    model_name: str = Field(..., description="Model name")
    model_settings: Optional[Dict] = Field(None, description="Model settings JSON")
    system_prompt: str = Field(..., description="System prompt")
    last_user_message: str = Field(..., description="Last user message")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class TestCaseService:
    """Service class for test case business logic."""

    def __init__(self):
        self.store = TestCaseStore()

    def create_test_case(self, request: TestCaseCreateData) -> TestCaseData:
        """
        Create a new test case with automatic parsing of raw data.
        
        Args:
            request: Test case creation request
            
        Returns:
            TestCaseData: Created test case data
            
        Raises:
            ValueError: If raw data is invalid
            Exception: If creation fails
        """
        try:
            logger.info(f"Creating test case: {request.name}")
            
            # Validate raw data format
            if not validate_raw_data_format(request.raw_data):
                raise ValueError("Invalid raw data format")
            
            # Parse the raw data
            parsed_data = parse_llm_raw_data(request.raw_data)
            
            # Create test case model
            test_case = TestCase(
                id=str(uuid.uuid4()),
                name=request.name,
                description=request.description,
                raw_data=request.raw_data,
                middle_messages=parsed_data.middle_messages,
                tools=parsed_data.tools,
                model_name=parsed_data.model_name,
                model_settings=parsed_data.model_settings,
                system_prompt=parsed_data.system_prompt,
                last_user_message=parsed_data.last_user_message
            )
            
            # Save to database
            created_test_case = self.store.create(test_case)
            
            logger.info(f"Test case created successfully: {created_test_case.id}")
            
            return TestCaseData(
                id=created_test_case.id,
                name=created_test_case.name,
                description=created_test_case.description,
                raw_data=created_test_case.raw_data,
                middle_messages=created_test_case.middle_messages,
                tools=created_test_case.tools,
                model_name=created_test_case.model_name,
                model_settings=created_test_case.model_settings,
                system_prompt=created_test_case.system_prompt,
                last_user_message=created_test_case.last_user_message,
                created_at=created_test_case.created_at,
                updated_at=created_test_case.updated_at
            )
            
        except ValueError as e:
            logger.error(f"Invalid data for test case creation: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create test case: {e}")
            raise

    def get_test_case(self, test_case_id: str) -> Optional[TestCaseData]:
        """
        Get a test case by ID.
        
        Args:
            test_case_id: Test case ID
            
        Returns:
            TestCaseData or None if not found
        """
        try:
            test_case = self.store.get_by_id(test_case_id)
            if not test_case:
                logger.debug(f"Test case not found: {test_case_id}")
                return None
            
            return TestCaseData(
                id=test_case.id,
                name=test_case.name,
                description=test_case.description,
                raw_data=test_case.raw_data,
                middle_messages=test_case.middle_messages,
                tools=test_case.tools,
                model_name=test_case.model_name,
                model_settings=test_case.model_settings,
                system_prompt=test_case.system_prompt,
                last_user_message=test_case.last_user_message,
                created_at=test_case.created_at,
                updated_at=test_case.updated_at
            )
            
        except Exception as e:
            logger.error(f"Failed to get test case {test_case_id}: {e}")
            raise

    def get_all_test_cases(self, limit: int = 100, offset: int = 0) -> List[TestCaseData]:
        """
        Get all test cases with pagination.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of test case responses
        """
        try:
            test_cases = self.store.get_all(limit=limit, offset=offset)
            
            return [
                TestCaseData(
                    id=tc.id,
                    name=tc.name,
                    description=tc.description,
                    raw_data=tc.raw_data,
                    middle_messages=tc.middle_messages,
                    tools=tc.tools,
                    model_name=tc.model_name,
                    model_settings=tc.model_settings,
                    system_prompt=tc.system_prompt,
                    last_user_message=tc.last_user_message,
                    created_at=tc.created_at,
                    updated_at=tc.updated_at
                )
                for tc in test_cases
            ]
            
        except Exception as e:
            logger.error(f"Failed to get test cases: {e}")
            raise

    def update_test_case(self, test_case_id: str, request: TestCaseUpdateData) -> Optional[TestCaseData]:
        """
        Update an existing test case.
        
        Args:
            test_case_id: Test case ID to update
            request: Update request data
            
        Returns:
            TestCaseData or None if not found
        """
        try:
            # Get existing test case
            test_case = self.store.get_by_id(test_case_id)
            if not test_case:
                logger.debug(f"Test case not found for update: {test_case_id}")
                return None
            
            # Update fields
            if request.name is not None:
                test_case.name = request.name
            if request.description is not None:
                test_case.description = request.description
            if request.system_prompt is not None:
                test_case.system_prompt = request.system_prompt
            if request.last_user_message is not None:
                test_case.last_user_message = request.last_user_message
            
            # Save changes
            updated_test_case = self.store.update(test_case)
            
            logger.info(f"Test case updated successfully: {test_case_id}")
            
            return TestCaseData(
                id=updated_test_case.id,
                name=updated_test_case.name,
                description=updated_test_case.description,
                raw_data=updated_test_case.raw_data,
                middle_messages=updated_test_case.middle_messages,
                tools=updated_test_case.tools,
                model_name=updated_test_case.model_name,
                model_settings=updated_test_case.model_settings,
                system_prompt=updated_test_case.system_prompt,
                last_user_message=updated_test_case.last_user_message,
                created_at=updated_test_case.created_at,
                updated_at=updated_test_case.updated_at
            )
            
        except Exception as e:
            logger.error(f"Failed to update test case {test_case_id}: {e}")
            raise

    def delete_test_case(self, test_case_id: str) -> bool:
        """
        Delete a test case by ID.
        
        Args:
            test_case_id: Test case ID to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        try:
            deleted = self.store.delete(test_case_id)
            if deleted:
                logger.info(f"Test case deleted successfully: {test_case_id}")
            else:
                logger.debug(f"Test case not found for deletion: {test_case_id}")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete test case {test_case_id}: {e}")
            raise

    def search_test_cases(self, name_pattern: str, limit: int = 50) -> List[TestCaseData]:
        """
        Search test cases by name pattern.
        
        Args:
            name_pattern: Pattern to search for in names
            limit: Maximum number of results
            
        Returns:
            List of matching test case responses
        """
        try:
            test_cases = self.store.search_by_name(name_pattern, limit=limit)
            
            return [
                TestCaseData(
                    id=tc.id,
                    name=tc.name,
                    description=tc.description,
                    raw_data=tc.raw_data,
                    middle_messages=tc.middle_messages,
                    tools=tc.tools,
                    model_name=tc.model_name,
                    model_settings=tc.model_settings,
                    system_prompt=tc.system_prompt,
                    last_user_message=tc.last_user_message,
                    created_at=tc.created_at,
                    updated_at=tc.updated_at
                )
                for tc in test_cases
            ]
            
        except Exception as e:
            logger.error(f"Failed to search test cases: {e}")
            raise

    def get_test_case_for_execution(self, test_case_id: str) -> Optional[TestCase]:
        """
        Get a test case with all data needed for execution.
        
        Args:
            test_case_id: Test case ID
            
        Returns:
            TestCase model with all execution data or None if not found
        """
        try:
            return self.store.get_by_id(test_case_id)
            
        except Exception as e:
            logger.error(f"Failed to get test case for execution {test_case_id}: {e}")
            raise


__all__ = ["TestCaseService"]
