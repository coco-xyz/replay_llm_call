"""
Test Case Service

Business logic service for test case operations.
Handles creation, retrieval, updating, and deletion of test cases with parsing.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.core.logger import get_logger
from src.models import TestCase
from src.services.agent_service import AgentService, AgentSummary
from src.services.llm_parser_service import parse_llm_raw_data, validate_raw_data_format
from src.stores.test_case_store import TestCaseStore

logger = get_logger(__name__)


class TestCaseCreateData(BaseModel):
    """Service layer data for creating a test case."""

    name: str = Field(..., description="Test case name")
    raw_data: Dict = Field(..., description="Raw logfire data")
    description: Optional[str] = Field(None, description="Test case description")
    agent_id: Optional[str] = Field(None, description="Agent that owns this test case")


class TestCaseUpdateData(BaseModel):
    """Service layer data for updating a test case."""

    name: Optional[str] = Field(None, description="Updated test case name")
    raw_data: Optional[Dict] = Field(None, description="Updated raw logfire data")
    description: Optional[str] = Field(
        None, description="Updated test case description"
    )
    system_prompt: Optional[str] = Field(None, description="Updated system prompt")
    last_user_message: Optional[str] = Field(None, description="Updated user message")
    agent_id: Optional[str] = Field(None, description="Updated owning agent")


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
    agent_id: str = Field(..., description="Owning agent identifier")
    agent: Optional[AgentSummary] = Field(
        None, description="Summary information about the owning agent"
    )
    is_deleted: bool = Field(
        False, description="Indicates whether the test case is soft deleted"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class TestCaseService:
    """Service class for test case business logic."""

    def __init__(self):
        self.store = TestCaseStore()
        self.agent_service = AgentService()

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

            # Resolve agent
            try:
                agent = self.agent_service.get_active_agent_or_raise(request.agent_id)
            except ValueError as agent_error:
                logger.error("Invalid agent specified: %s", agent_error)
                raise

            # Create test case model
            test_case = TestCase(
                id=str(uuid.uuid4()),
                agent_id=agent.id,
                name=request.name,
                description=request.description,
                raw_data=request.raw_data,
                middle_messages=parsed_data.middle_messages,
                tools=parsed_data.tools,
                model_name=parsed_data.model_name,
                model_settings=parsed_data.model_settings,
                system_prompt=parsed_data.system_prompt,
                last_user_message=parsed_data.last_user_message,
                is_deleted=False,
            )

            # Save to database
            created_test_case = self.store.create(test_case)

            logger.info("Test case created successfully: %s", created_test_case.id)

            return self._build_test_case_data(created_test_case)

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
            test_case = self.store.get_by_id(test_case_id, include_deleted=True)
            if not test_case:
                logger.debug(f"Test case not found: {test_case_id}")
                return None

            if test_case.is_deleted:
                logger.debug(f"Test case is marked as deleted: {test_case_id}")

            return self._build_test_case_data(test_case)

        except Exception as e:
            logger.error(f"Failed to get test case {test_case_id}: {e}")
            raise

    def get_all_test_cases(
        self,
        limit: int = 100,
        offset: int = 0,
        agent_id: Optional[str] = None,
    ) -> List[TestCaseData]:
        """
        Get all test cases with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of test case responses
        """
        try:
            test_cases = self.store.get_all(
                limit=limit, offset=offset, agent_id=agent_id
            )

            return [self._build_test_case_data(tc) for tc in test_cases]

        except Exception as e:
            logger.error(f"Failed to get test cases: {e}")
            raise

    def update_test_case(
        self, test_case_id: str, request: TestCaseUpdateData
    ) -> Optional[TestCaseData]:
        """
        Update an existing test case.

        If raw_data is provided, it will be re-parsed and all parsed fields will be updated.
        Otherwise, only the specified fields will be updated.

        Args:
            test_case_id: Test case ID to update
            request: Update request data

        Returns:
            TestCaseData or None if not found
        """
        try:
            # Get existing test case
            test_case = self.store.get_by_id(test_case_id, include_deleted=True)
            if not test_case:
                logger.debug(f"Test case not found for update: {test_case_id}")
                return None

            if test_case.is_deleted:
                logger.debug(f"Cannot update deleted test case: {test_case_id}")
                return None

            # Change agent if requested
            if request.agent_id is not None and request.agent_id != test_case.agent_id:
                try:
                    agent = self.agent_service.get_active_agent_or_raise(request.agent_id)
                except ValueError as agent_error:
                    logger.error("Invalid agent specified on update: %s", agent_error)
                    raise
                test_case.agent_id = agent.id

            # If raw_data is provided, re-parse it and update all parsed fields
            if request.raw_data is not None:
                logger.info(f"Re-importing raw data for test case: {test_case_id}")

                # Validate raw data format
                if not validate_raw_data_format(request.raw_data):
                    raise ValueError("Invalid raw data format")

                # Parse the new raw data
                parsed_data = parse_llm_raw_data(request.raw_data)

                # Update all fields with parsed data
                test_case.raw_data = request.raw_data
                test_case.middle_messages = parsed_data.middle_messages
                test_case.tools = parsed_data.tools
                test_case.model_name = parsed_data.model_name
                test_case.model_settings = parsed_data.model_settings
                test_case.system_prompt = parsed_data.system_prompt
                test_case.last_user_message = parsed_data.last_user_message

                logger.info(
                    f"Raw data re-parsed successfully for test case: {test_case_id}"
                )

            # Update other fields if provided
            if request.name is not None:
                test_case.name = request.name
            if request.description is not None:
                test_case.description = request.description

            # Only update these fields if raw_data was not provided (to avoid overriding parsed data)
            if request.raw_data is None:
                if request.system_prompt is not None:
                    test_case.system_prompt = request.system_prompt
                if request.last_user_message is not None:
                    test_case.last_user_message = request.last_user_message

            # Save changes
            updated_test_case = self.store.update(test_case)

            logger.info(f"Test case updated successfully: {test_case_id}")

            return self._build_test_case_data(updated_test_case)

        except Exception as e:
            logger.error(f"Failed to update test case {test_case_id}: {e}")
            raise

    def delete_test_case(self, test_case_id: str) -> bool:
        """
        Soft delete a test case by ID.

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

    def search_test_cases(
        self, name_pattern: str, limit: int = 50, agent_id: Optional[str] = None
    ) -> List[TestCaseData]:
        """
        Search test cases by name pattern.

        Args:
            name_pattern: Pattern to search for in names
            limit: Maximum number of results

        Returns:
            List of matching test case responses
        """
        try:
            test_cases = self.store.search_by_name(
                name_pattern, limit=limit, agent_id=agent_id
            )

            return [self._build_test_case_data(tc) for tc in test_cases]

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
            test_case = self.store.get_by_id(test_case_id, include_deleted=True)
            if test_case and test_case.is_deleted:
                logger.debug(
                    f"Test case {test_case_id} is marked as deleted; skipping execution"
                )
                return None
            if test_case:
                try:
                    self.agent_service.get_active_agent_or_raise(test_case.agent_id)
                except ValueError:
                    logger.debug(
                        "Test case %s belongs to inactive agent; skipping execution",
                        test_case_id,
                    )
                    return None
            return test_case

        except Exception as e:
            logger.error(f"Failed to get test case for execution {test_case_id}: {e}")
            raise

    def _build_test_case_data(self, test_case: TestCase) -> TestCaseData:
        """Convert a TestCase ORM instance to TestCaseData."""

        agent_summary = None
        agent_value = None

        # Avoid triggering lazy loads on detached instances
        if hasattr(test_case, "__dict__") and "agent" in test_case.__dict__:
            agent_value = test_case.__dict__["agent"]

        if agent_value is not None:
            agent_summary = AgentSummary.model_validate(agent_value)
        else:
            agent_summary = self.agent_service.get_agent_summary(test_case.agent_id)

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
            agent_id=test_case.agent_id,
            agent=agent_summary,
            is_deleted=test_case.is_deleted,
            created_at=test_case.created_at,
            updated_at=test_case.updated_at,
        )


__all__ = ["TestCaseService"]
