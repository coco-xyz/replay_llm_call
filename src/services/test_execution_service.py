"""
Test Execution Service

Service for executing LLM tests synchronously and recording results.
"""

import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.logger import get_logger
from src.models import TestLog
from src.services.agent_service import AgentService
from src.services.llm_execution_service import execute_llm_test
from src.services.test_case_service import TestCaseService
from src.stores.test_log_store import TestLogStore

logger = get_logger(__name__)


class TestExecutionData(BaseModel):
    """Service layer data for test execution."""

    test_case_id: str = Field(..., description="ID of the test case to execute")
    agent_id: Optional[str] = Field(
        None, description="Agent context overriding the test case owner"
    )
    regression_test_id: Optional[str] = Field(
        None, description="Regression test run triggering this execution"
    )
    # User may modify these parameters (if None, use original values)
    modified_model_name: Optional[str] = Field(None, description="Override model name")
    modified_system_prompt: Optional[str] = Field(
        None, description="Override system prompt"
    )
    modified_last_user_message: Optional[str] = Field(
        None, description="Override user message"
    )
    modified_tools: Optional[List[Dict]] = Field(
        None, description="Override tools configuration"
    )
    modified_model_settings: Optional[Dict] = Field(
        None, description="Override model settings JSON"
    )


class ExecutionResult(BaseModel):
    """Service layer result of test execution."""

    status: str = Field(..., description="Execution status (success/failed)")
    log_id: Optional[str] = Field(
        None, description="Test log ID if execution completed"
    )
    agent_id: Optional[str] = Field(None, description="Agent used for execution")
    regression_test_id: Optional[str] = Field(
        None, description="Regression test context for the execution"
    )
    response_time_ms: Optional[int] = Field(
        None, description="Response time in milliseconds"
    )
    executed_at: Optional[datetime] = Field(None, description="Execution timestamp")
    error_message: Optional[str] = Field(
        None, description="Error message if execution failed"
    )
    llm_response: Optional[str] = Field(None, description="LLM response text")

    # Additional service-layer specific fields
    execution_context: Optional[Dict] = Field(
        None, description="Execution context data"
    )
    performance_metrics: Optional[Dict] = Field(None, description="Performance metrics")


class TestExecutionService:
    """Service class for test execution business logic."""

    def __init__(self):
        self.test_case_service = TestCaseService()
        self.test_log_store = TestLogStore()
        self.agent_service = AgentService()

    async def execute_test(self, request: TestExecutionData) -> ExecutionResult:
        """
        Execute a test case synchronously and record the results.

        Args:
            request: Test execution request

        Returns:
            ExecutionResult: Execution results

        Raises:
            ValueError: If test case not found or invalid parameters
            Exception: If execution fails
        """
        try:
            logger.info(f"Executing test for case: {request.test_case_id}")

            # Get test case data
            test_case = self.test_case_service.get_test_case_for_execution(
                request.test_case_id
            )
            if not test_case:
                raise ValueError(f"Test case not found: {request.test_case_id}")

            # Determine agent context
            agent_identifier = request.agent_id or test_case.agent_id
            try:
                agent = self.agent_service.get_active_agent_or_raise(agent_identifier)
            except ValueError as agent_error:
                logger.error("Agent not available for execution: %s", agent_error)
                raise ValueError(str(agent_error)) from agent_error

            # Use provided parameters or fall back to test case defaults / agent defaults
            model_name = (
                request.modified_model_name
                or test_case.model_name
                or agent.default_model_name
            )
            system_prompt = (
                request.modified_system_prompt
                or test_case.system_prompt
                or agent.default_system_prompt
            )
            user_message = (
                request.modified_last_user_message or test_case.last_user_message
            )
            tools = request.modified_tools or test_case.tools
            if request.modified_model_settings is not None:
                model_settings = request.modified_model_settings
            elif test_case.model_settings is not None:
                model_settings = test_case.model_settings
            else:
                model_settings = agent.default_model_settings

            if not model_name:
                raise ValueError("No model name specified")

            logger.debug(f"Executing with model: {model_name}")

            # Record start time
            start_time = time.time()

            # Execute the LLM test
            try:
                llm_response = await execute_llm_test(
                    model_name=model_name,
                    middle_messages=test_case.middle_messages,
                    system_prompt=system_prompt,
                    user_message=user_message,
                    original_tools=test_case.tools,
                    modified_tools=tools,
                    model_settings=model_settings,
                )

                # Calculate response time
                response_time_ms = int((time.time() - start_time) * 1000)

                # Create success log
                test_log = TestLog(
                    id=str(uuid.uuid4()),
                    test_case_id=request.test_case_id,
                    agent_id=agent.id,
                    regression_test_id=request.regression_test_id,
                    model_name=model_name,
                    model_settings=model_settings,
                    system_prompt=system_prompt,
                    user_message=user_message,
                    tools=tools,
                    llm_response=llm_response,
                    response_time_ms=response_time_ms,
                    status="success",
                    error_message=None,
                )

                # Save log
                saved_log = self.test_log_store.create(test_log)

                logger.info(f"Test executed successfully: {saved_log.id}")

                return ExecutionResult(
                    log_id=saved_log.id,
                    status="success",
                    agent_id=agent.id,
                    regression_test_id=request.regression_test_id,
                    llm_response=llm_response,
                    response_time_ms=response_time_ms,
                    error_message=None,
                    executed_at=saved_log.created_at,
                )

            except Exception as llm_error:
                # Calculate response time even for failures
                response_time_ms = int((time.time() - start_time) * 1000)

                # Create failure log
                error_message = str(llm_error)
                test_log = TestLog(
                    id=str(uuid.uuid4()),
                    test_case_id=request.test_case_id,
                    agent_id=agent.id,
                    regression_test_id=request.regression_test_id,
                    model_name=model_name,
                    model_settings=model_settings,
                    system_prompt=system_prompt,
                    user_message=user_message,
                    tools=tools,
                    llm_response=None,
                    response_time_ms=response_time_ms,
                    status="failed",
                    error_message=error_message,
                )

                # Save log
                saved_log = self.test_log_store.create(test_log)

                logger.error(f"Test execution failed: {error_message}")

                return ExecutionResult(
                    log_id=saved_log.id,
                    status="failed",
                    agent_id=agent.id,
                    regression_test_id=request.regression_test_id,
                    llm_response=None,
                    response_time_ms=response_time_ms,
                    error_message=error_message,
                    executed_at=saved_log.created_at,
                )

        except ValueError as e:
            logger.error(f"Invalid test execution request: {e}")
            raise
        except Exception as e:
            logger.error(f"Test execution service error: {e}")
            raise

    def execute_test_with_modifications(
        self,
        test_case_id: str,
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        user_message: Optional[str] = None,
        tools: Optional[list] = None,
    ) -> ExecutionResult:
        """
        Execute a test case with optional parameter modifications.

        Args:
            test_case_id: Test case ID to execute
            model_name: Override model name (optional)
            system_prompt: Override system prompt (optional)
            user_message: Override user message (optional)
            tools: Override tools (optional)

        Returns:
            ExecutionResult: Execution results
        """
        request = TestExecutionData(
            test_case_id=test_case_id,
            modified_system_prompt=system_prompt,
            modified_last_user_message=user_message,
            modified_tools=tools,
        )

        return self.execute_test(request)

    def validate_execution_parameters(
        self, test_case_id: str, model_name: Optional[str] = None
    ) -> bool:
        """
        Validate that execution parameters are valid.

        Args:
            test_case_id: Test case ID
            model_name: Model name to validate

        Returns:
            bool: True if parameters are valid
        """
        try:
            # Check if test case exists
            test_case = self.test_case_service.get_test_case_for_execution(test_case_id)
            if not test_case:
                logger.debug(f"Test case not found: {test_case_id}")
                return False

            # Check if we have a valid model name
            effective_model_name = model_name or test_case.model_name
            if not effective_model_name or not effective_model_name.strip():
                logger.debug("No valid model name available")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating execution parameters: {e}")
            return False

    def get_execution_preview(self, test_case_id: str) -> dict:
        """
        Get a preview of what will be executed for a test case.

        Args:
            test_case_id: Test case ID

        Returns:
            Dict with execution preview data
        """
        try:
            test_case = self.test_case_service.get_test_case_for_execution(test_case_id)
            if not test_case:
                return {"error": "Test case not found"}

            return {
                "test_case_id": test_case_id,
                "test_case_name": test_case.name,
                "model_name": test_case.model_name,
                "system_prompt": test_case.system_prompt,
                "user_message": test_case.last_user_message,
                "has_tools": bool(test_case.tools),
                "tools_count": len(test_case.tools) if test_case.tools else 0,
                "other_messages_count": len(test_case.middle_messages),
            }

        except Exception as e:
            logger.error(f"Error getting execution preview: {e}")
            return {"error": str(e)}


__all__ = ["TestExecutionService"]
