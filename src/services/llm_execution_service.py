"""
LLM Execution Service

Service for executing LLM tests using pydantic-ai Direct Model Requests.
Implements the replay mechanism by concatenating system prompt, other messages, and user message.
"""

import json
from typing import Dict, List, Optional

from pydantic_ai.direct import model_request
from pydantic_ai.messages import (
    ModelRequest,
    SystemPromptPart,
    UserPromptPart,
    ToolReturnPart,
    ModelResponse,
    TextPart,
    ToolCallPart,
)

from pydantic_ai.models import ModelRequestParameters
from pydantic_ai import ToolDefinition, ModelSettings

from src.core.logger import get_logger
from src.core.llm_factory import create_llm_model

logger = get_logger(__name__)


def convert_logfire_tools_to_pydantic_ai(logfire_tools: list[dict]) -> ModelRequestParameters:
    """
    Convert logfire-exported tools format to pydantic-ai ModelRequestParameters format.

    Args:
        logfire_tools: List of tools in logfire format:
            [
                {
                    "type": "function",
                    "function": {
                        "name": "function_name",
                        "description": "description",
                        "parameters": {
                            // JSON schema
                        }
                    }
                }
            ]

    Returns:
        ModelRequestParameters with function_tools configured
    """
    if not logfire_tools:
        return ModelRequestParameters()

    function_tools = []
    for tool in logfire_tools:
        if tool.get("type") == "function" and "function" in tool:
            func_def = tool["function"]
            tool_definition = ToolDefinition(
                name=func_def.get("name", ""),
                description=func_def.get("description", ""),
                parameters_json_schema=func_def.get("parameters", {}),
                strict=func_def.get("strict", False)
            )
            function_tools.append(tool_definition)

    return ModelRequestParameters(
        function_tools=function_tools,
        allow_text_output=True  # Allow model to either use tools or respond directly
    )


async def execute_llm_test(
    model_name: str,
    middle_messages: List[Dict],  # Messages except system prompt and last user message
    system_prompt: str = "",
    user_message: str = "",
    original_tools: Optional[List[Dict]] = None,
    modified_tools: Optional[List[Dict]] = None,
    model_settings: Optional[Dict] = None
) -> str:
    """
    Execute LLM test using Direct Model Requests with concatenation replay strategy.

    This function implements the optimized replay mechanism:
    1. Add system prompt (if provided)
    2. Add original_messages (other messages from the original request)
    3. Add user message (if provided)

    Args:
        model_name: Complete model name (e.g., "openrouter:anthropic/claude-sonnet-4")
        middle_messages: Messages except system prompt and last user message
        system_prompt: System prompt to use (may be modified by user)
        user_message: User message to use (may be modified by user)
        original_tools: Original tools from the request
        modified_tools: Modified tools (if None, use original_tools)
        model_settings: Model settings dict (temperature, max_tokens, etc.)

    Returns:
        str: LLM response content

    Raises:
        Exception: If LLM call fails
    """
    try:
        logger.info(f"Executing LLM test with model: {model_name}")

        # Build complete replay messages through concatenation
        replay_messages = []

        # 1. Add system prompt (if provided)
        if system_prompt:
            replay_messages.append({
                "role": "system",
                "content": system_prompt
            })
            logger.debug("Added system prompt to replay messages")

        # 2. Add middle messages (other messages from the original request)
        if middle_messages:
            replay_messages.extend(middle_messages)
            logger.debug(f"Added {len(middle_messages)} middle messages to replay")

        # 3. Add user message (if provided)
        if user_message:
            replay_messages.append({
                "role": "user",
                "content": user_message
            })
            logger.debug("Added user message to replay messages")

        if not replay_messages:
            raise ValueError("No messages to send to LLM")

        logger.debug(f"Total replay messages: {len(replay_messages)}")

        # Convert to pydantic-ai message format
        # Convert OpenAI format messages to pydantic-ai format
        pydantic_messages = []

        for message in replay_messages:
            role = message.get("role")
            content = message.get("content", "")

            if role == "system":
                pydantic_messages.append(ModelRequest(parts=[SystemPromptPart(content=content)]))
            elif role == "user":
                pydantic_messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
            elif role == "assistant":
                msg = ModelResponse(parts=[TextPart(content=content)])
                if "tool_calls" in message:
                    for tool_call in message["tool_calls"]:
                        func_set = tool_call.get("function")
                        msg.parts.append(ToolCallPart(
                            tool_call_id=tool_call.get("id"),
                            tool_name=func_set.get("name"),
                            args=func_set.get("arguments"),
                        ))
                pydantic_messages.append(msg)
            elif role == "tool":
                msg = ModelRequest(parts=[ToolReturnPart(
                    tool_name=message.get("name", ""),
                    tool_call_id=message.get("tool_call_id", ""),
                    content=content,
                )])
                pydantic_messages.append(msg)
            else:
                logger.warning(f"Unknown message role: {role}")

        if not pydantic_messages:
            raise ValueError("No valid messages for pydantic-ai")

        # Determine which tools to use
        tools_to_use = modified_tools if modified_tools is not None else original_tools

        # Build model_request_parameters for tools
        model_request_parameters = None
        if tools_to_use:
            try:
                model_request_parameters = convert_logfire_tools_to_pydantic_ai(tools_to_use)
                logger.debug(
                    f"Successfully converted {len(tools_to_use)} tools to pydantic-ai format"
                )
            except Exception as e:
                logger.error(f"Failed to convert tools to pydantic-ai format: {e}")
                logger.debug(f"Tools data: {tools_to_use}")
                # Proceed without tools if conversion fails
                model_request_parameters = None

        # Create model settings if provided
        pydantic_model_settings = None
        if model_settings is not None:
            pydantic_model_settings = ModelSettings(**model_settings)
            logger.debug(f"Using model settings: {model_settings}")

        # Execute the direct model request
        logger.debug(f"Calling model: {model_name}")
        model_response = await model_request(
            model=create_llm_model(model_name, "openrouter"),
            messages=pydantic_messages,
            model_settings=pydantic_model_settings,
            model_request_parameters=model_request_parameters
        )


        # Extract response content and tool calls
        response_content = ""
        tool_calls = []

        if model_response.parts:
            for part in model_response.parts:
                # Extract text content
                if isinstance(part, TextPart) and part.content:
                    response_content += part.content

                # Extract tool calls
                elif isinstance(part, ToolCallPart):
                    tool_call_info = {
                        "tool_name": part.tool_name,
                        "tool_call_id": part.tool_call_id,
                        "args": part.args
                    }
                    tool_calls.append(tool_call_info)
                    logger.debug(
                        "Found tool call: %s with ID: %s", part.tool_name, part.tool_call_id
                    )

        # Format comprehensive response content
        formatted_response = ""

        # Add text content if present
        if response_content:
            formatted_response += response_content

        # Add tool calls information if present
        if tool_calls:
            if formatted_response:
                formatted_response += "\n\n"
            formatted_response += "=== Tool Calls ===\n"
            for i, tool_call in enumerate(tool_calls, 1):
                formatted_response += f"Tool Call {i}:\n"
                formatted_response += f"  Name: {tool_call['tool_name']}\n"
                formatted_response += f"  ID: {tool_call['tool_call_id']}\n"
                # Try to format arguments as JSON, fall back to string representation
                try:
                    if isinstance(tool_call['args'], str):
                        # Try to parse and re-format JSON string for better readability
                        parsed_args = json.loads(tool_call['args'])
                        formatted_args = json.dumps(parsed_args, indent=2, ensure_ascii=False)
                    else:
                        # Convert to JSON string for consistent formatting
                        formatted_args = json.dumps(tool_call['args'], indent=2, ensure_ascii=False)
                except (json.JSONDecodeError, TypeError, ValueError):
                    # Fall back to string representation if JSON processing fails
                    formatted_args = str(tool_call['args'])
                
                formatted_response += f"  Arguments: {formatted_args}\n"
                if i < len(tool_calls):
                    formatted_response += "\n"

        # Handle case where no content or tool calls were found
        if not formatted_response:
            logger.warning("No content or tool calls in model response")
            formatted_response = "[No response content or tool calls]"

        # Log comprehensive information
        content_length = len(response_content) if response_content else 0
        tool_count = len(tool_calls)
        logger.info(
            "LLM test completed successfully - Text length: %d, Tool calls: %d",
            content_length, tool_count
        )

        if tool_calls:
            tool_names = [tc['tool_name'] for tc in tool_calls]
            logger.info("Tools called: %s", ', '.join(tool_names))

        return formatted_response
    except Exception as e:
        logger.error("LLM test execution failed: %s", e)
        raise


def build_replay_messages(
    system_prompt: str,
    middle_messages: List[Dict],
    user_message: str
) -> List[Dict]:
    """
    Build the complete message list for replay by concatenation.

    Args:
        system_prompt: System prompt
        middle_messages: Other messages from original request
        user_message: User message

    Returns:
        List of messages in the correct order
    """
    replay_messages = []
    # 1. System prompt first
    if system_prompt:
        replay_messages.append({
            "role": "system",
            "content": system_prompt
        })

    # 2. Middle messages in the middle
    if middle_messages:
        replay_messages.extend(middle_messages)

    # 3. User message last
    if user_message:
        replay_messages.append({
            "role": "user",
            "content": user_message
        })

    return replay_messages


def validate_model_name(model_name: str) -> bool:
    """
    Validate that the model name is in the expected format.

    Args:
        model_name: Model name to validate

    Returns:
        bool: True if valid
    """
    if not model_name or not isinstance(model_name, str):
        return False

    # Model name should be non-empty string
    # Can be in format "provider:model" or just "model"
    return len(model_name.strip()) > 0


def extract_response_metadata(model_response) -> Dict:
    """
    Extract metadata from model response.

    Args:
        model_response: Response from pydantic-ai model_request

    Returns:
        Dict with response metadata
    """
    try:
        metadata = {
            "parts_count": len(model_response.parts) if model_response.parts else 0,
            "has_content": False,
            "content_length": 0
        }

        if model_response.parts:
            total_content_length = 0
            has_content = False

            for part in model_response.parts:
                if isinstance(part, TextPart) and part.content:
                    has_content = True
                    total_content_length += len(part.content)

            metadata["has_content"] = has_content
            metadata["content_length"] = total_content_length

        return metadata

    except Exception as e:
        logger.error(f"Failed to extract response metadata: {e}")
        return {
            "parts_count": 0,
            "has_content": False,
            "content_length": 0
        }


__all__ = [
    "execute_llm_test",
    "build_replay_messages",
    "validate_model_name",
    "extract_response_metadata"
]
