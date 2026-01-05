"""
LLM Parser Service

Service for parsing logfire raw data and extracting LLM request components.
Supports multiple formats:
- OpenAI format (via http.request.body.text)
- Google Gemini format (via http.request.body.text)
- pydantic-ai OpenTelemetry format (via gen_ai.* attributes)
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from src.core.logger import get_logger

logger = get_logger(__name__)


class ParsedLLMData(BaseModel):
    """Parsed LLM data from raw logfire data for service layer use."""

    # Original data (used for replay concatenation)
    middle_messages: List[Dict] = Field(
        ..., description="Messages except system prompt and last user message"
    )
    tools: Optional[List[Dict]] = Field(None, description="Tools configuration")
    model_name: str = Field(..., description="Model name")
    model_settings: Optional[Dict] = Field(
        None, description="Model settings JSON (temperature, max_tokens, etc.)"
    )

    # Parsed key data (used for page display and replay concatenation)
    system_prompt: str = Field(..., description="System prompt")
    last_user_message: str = Field(..., description="Last user message")


def parse_llm_raw_data(raw_data: dict) -> ParsedLLMData:
    """
    Parse logfire raw data and separate system prompt, last user message, and other messages.
    Supports OpenAI, Google Gemini, and pydantic-ai OpenTelemetry formats.

    This function implements the optimized storage strategy where:
    - System prompt (first system message) is extracted separately
    - Last user message is extracted separately
    - All other messages are stored in original_messages for replay concatenation

    Args:
        raw_data: Raw logfire data containing the LLM request (OpenAI, Gemini, or pydantic-ai format)

    Returns:
        ParsedLLMData: Parsed data with separated components

    Raises:
        ValueError: If raw data format is invalid
        KeyError: If required fields are missing
    """
    try:
        logger.debug("Parsing LLM raw data")

        # Extract the request body from logfire data
        attributes = raw_data.get("attributes", {})
        if not attributes:
            raise ValueError("Missing 'attributes' in raw data")

        # Detect data source format and convert if necessary
        data_source = _detect_data_source(raw_data)
        logger.debug(f"Detected data source: {data_source}")

        if data_source == "pydantic_ai":
            # Convert pydantic-ai format to OpenAI format
            logger.debug("Converting pydantic-ai format to OpenAI format")
            converted_data = _convert_pydantic_ai_to_openai_format(raw_data)
            request_body = converted_data["attributes"]["http.request.body.text"]
        elif data_source == "http_body":
            request_body = attributes.get("http.request.body.text", {})
            if not request_body:
                raise ValueError("Missing 'http.request.body.text' in raw data")

            # Detect API format and convert if necessary
            api_format = _detect_api_format(request_body)
            logger.debug(f"Detected API format: {api_format}")

            if api_format == "gemini":
                # Convert Gemini format to OpenAI format
                logger.debug("Converting Gemini format to OpenAI format")
                converted_data = _convert_gemini_to_openai_format(raw_data)
                request_body = converted_data["attributes"]["http.request.body.text"]
            elif api_format != "openai":
                raise ValueError(f"Unsupported API format: {api_format}")
        else:
            raise ValueError(f"Unsupported data source format: {data_source}")

        # Extract original data (now in OpenAI format)
        all_messages = request_body.get("messages", [])
        tools = request_body.get("tools", [])
        model_name = request_body.get("model", "")

        # Extract model settings (temperature, max_tokens, top_p, etc.)
        model_settings = {}

        # Direct mapping for most parameters
        for key in [
            "temperature",
            "top_p",
            "parallel_tool_calls",
            "seed",
            "presence_penalty",
            "frequency_penalty",
        ]:
            if key in request_body:
                model_settings[key] = request_body[key]

        # Handle parameter name mapping: max_completion_tokens -> max_tokens
        if "max_completion_tokens" in request_body:
            model_settings["max_tokens"] = request_body["max_completion_tokens"]
        elif "max_tokens" in request_body:
            model_settings["max_tokens"] = request_body["max_tokens"]

        # Only keep model_settings if it has any values
        model_settings = model_settings if model_settings else None

        if not all_messages:
            raise ValueError("No messages found in request body")
        if not model_name:
            raise ValueError("No model specified in request body")

        logger.debug(f"Found {len(all_messages)} messages, model: {model_name}")

        # Find and extract the first system message
        system_prompt = ""
        system_message_index = -1
        for i, message in enumerate(all_messages):
            if message.get("role") == "system":
                system_prompt = message.get("content", "")
                system_message_index = i
                logger.debug(f"Found system message at index {i}")
                break

        # Find and extract the last user message
        last_user_message = ""
        last_user_message_index = -1
        for i in range(len(all_messages) - 1, -1, -1):
            if all_messages[i].get("role") != "assistant":
                if all_messages[i].get("role") == "tool":
                    last_user_message = json.dumps(all_messages[i], ensure_ascii=False)
                else:
                    last_user_message = all_messages[i].get("content", "")
                last_user_message_index = i
                logger.debug(f"Found last user message at index {i}")
                break

        # Build middle_messages (all messages except first system and last user)
        middle_messages = []
        for i, message in enumerate(all_messages):
            if i != system_message_index and i != last_user_message_index:
                middle_messages.append(message)

        logger.debug(
            f"Parsed data: system_prompt={len(system_prompt)} chars, "
            f"last_user_message={len(last_user_message)} chars, "
            f"middle_messages={len(middle_messages)} items, "
            f"tools={len(tools) if tools else 0} items, "
            f"model_settings={model_settings}"
        )

        return ParsedLLMData(
            middle_messages=middle_messages,
            tools=tools if tools else None,
            model_name=model_name,
            model_settings=model_settings,
            system_prompt=system_prompt,
            last_user_message=last_user_message,
        )

    except (KeyError, ValueError) as e:
        logger.error(f"Failed to parse LLM raw data: {e}")
        raise ValueError(f"Invalid raw data format: {str(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error parsing LLM raw data: {e}")
        raise ValueError(f"Failed to parse raw data: {str(e)}") from e


def _detect_api_format(request_body: dict) -> str:
    """
    Detect whether the request body is OpenAI or Gemini format.

    Args:
        request_body: The request body to analyze

    Returns:
        str: "openai" or "gemini"
    """
    if "messages" in request_body and "model" in request_body:
        return "openai"
    elif "contents" in request_body or "systemInstruction" in request_body:
        return "gemini"
    else:
        return "unknown"


def _validate_openai_format(request_body: dict) -> bool:
    """Validate OpenAI format request body."""
    # Check required fields
    messages = request_body.get("messages")
    if not isinstance(messages, list) or not messages:
        return False

    model = request_body.get("model")
    if not isinstance(model, str) or not model:
        return False

    # Validate message format
    for message in messages:
        if not isinstance(message, dict):
            return False
        if "role" not in message or "content" not in message:
            return False
        if message["role"] not in ["system", "user", "assistant", "tool"]:
            return False

    return True


def _validate_gemini_format(request_body: dict) -> bool:
    """Validate Gemini format request body."""
    # Check for contents or systemInstruction
    contents = request_body.get("contents")
    system_instruction = request_body.get("systemInstruction")

    if not contents and not system_instruction:
        return False

    # Validate contents format if present
    if contents:
        if not isinstance(contents, list):
            return False
        for content in contents:
            if not isinstance(content, dict):
                return False
            if "parts" not in content:
                return False
            if not isinstance(content["parts"], list):
                return False

    # Validate systemInstruction format if present
    if system_instruction:
        if not isinstance(system_instruction, dict):
            return False
        if "parts" not in system_instruction:
            return False
        if not isinstance(system_instruction["parts"], list):
            return False

    return True


def _extract_model_from_url(raw_data: dict) -> str:
    """
    Extract model name from Gemini API URL.

    Args:
        raw_data: Raw logfire data

    Returns:
        str: Model name (e.g., "gemini-2.5-flash")
    """
    try:
        attributes = raw_data.get("attributes", {})
        url_path = attributes.get("http.target", "")

        # Extract model from URL like "/v1beta/models/gemini-2.5-flash:generateContent"
        match = re.search(r"/models/([^:]+)", url_path)
        if match:
            return match.group(1)

        # Fallback: try to get from url_path or message
        message = raw_data.get("message", "")
        if "gemini" in message.lower():
            # Extract from message like "POST generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
            match = re.search(r"models/([^:]+)", message)
            if match:
                return match.group(1)

        return "gemini-unknown"
    except Exception as e:
        logger.debug(f"Failed to extract model from URL: {e}")
        return "gemini-unknown"


def _convert_gemini_parts_to_content(parts: List[Dict]) -> str:
    """
    Convert Gemini parts array to OpenAI content string.

    Args:
        parts: List of parts from Gemini format

    Returns:
        str: Combined content string
    """
    content_parts = []
    for part in parts:
        if "text" in part:
            content_parts.append(part["text"])
        # Could add support for other part types (images, etc.) in the future

    return "\n".join(content_parts)


def _convert_gemini_parts_to_openai_message(
    parts: List[Dict],
    role: str,
    tool_call_state: Dict[str, Any],
) -> Tuple[Optional[Dict], List[Dict]]:
    """Convert Gemini parts list to an OpenAI chat message and any follow-up tool messages."""

    text_segments: List[str] = []
    tool_calls: List[Dict] = []
    extra_messages: List[Dict] = []

    for part in parts:
        if "text" in part:
            text_segments.append(part["text"])
            continue

        if "functionCall" in part:
            function_call = part.get("functionCall", {}) or {}
            name = function_call.get("name", "")
            arguments = function_call.get("args")
            if arguments is None:
                arguments = function_call.get("arguments")

            if not isinstance(arguments, str):
                try:
                    arguments = json.dumps(arguments or {}, ensure_ascii=False)
                except TypeError:
                    arguments = json.dumps({}, ensure_ascii=False)

            call_id = function_call.get("id")
            if isinstance(call_id, str) and call_id.strip():
                call_id = call_id.strip()
            else:
                counter = int(tool_call_state.get("counter", 1))
                call_id = f"tool_call_{counter}"
                tool_call_state["counter"] = counter + 1

            pending_calls = tool_call_state.setdefault("pending", {})
            pending_by_name = tool_call_state.setdefault("pending_by_name", {})
            pending_calls[call_id] = name or None
            if name:
                pending_by_name.setdefault(name, []).append(call_id)

            tool_calls.append(
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": name, "arguments": arguments},
                }
            )
            continue

        if "functionResponse" in part:
            function_response = part.get("functionResponse", {}) or {}
            name = function_response.get("name", "")
            response_payload = function_response.get("response")
            if response_payload is None:
                response_payload = function_response

            serialized_response = {"name": name, "response": response_payload}

            try:
                content = json.dumps(serialized_response, ensure_ascii=False)
            except TypeError:
                content = json.dumps({"name": name, "response": {}}, ensure_ascii=False)

            call_id = None
            pending_calls = tool_call_state.setdefault("pending", {})
            pending_by_name = tool_call_state.setdefault("pending_by_name", {})

            response_id = function_response.get("id")
            if isinstance(response_id, str) and response_id.strip():
                response_id = response_id.strip()
                if response_id in pending_calls:
                    call_id = response_id
                    pending_name = pending_calls.pop(response_id) or None
                    if pending_name:
                        name_queue = pending_by_name.get(pending_name, [])
                        try:
                            name_queue.remove(response_id)
                        except ValueError:
                            pass
                        if not name_queue:
                            pending_by_name.pop(pending_name, None)
                        else:
                            pending_by_name[pending_name] = name_queue

            if call_id is None and name:
                name_queue = pending_by_name.get(name)
                if name_queue:
                    call_id = name_queue.pop(0)
                    if not name_queue:
                        pending_by_name.pop(name, None)
                    pending_calls.pop(call_id, None)

            tool_message = {"role": "tool", "content": content}
            if call_id:
                tool_message["tool_call_id"] = call_id

            extra_messages.append(tool_message)
            continue

        # Preserve any unrecognized part types as JSON content to avoid data loss
        try:
            text_segments.append(json.dumps(part, ensure_ascii=False))
        except TypeError:
            text_segments.append(json.dumps({}, ensure_ascii=False))

    if not text_segments and not tool_calls:
        # Nothing to emit for the primary message
        return None, extra_messages

    message: Dict = {"role": role}

    if text_segments:
        message["content"] = "\n".join(text_segments)
    elif role == "assistant":
        # Ensure assistant tool call messages have explicit content
        message["content"] = ""

    if tool_calls:
        message["tool_calls"] = tool_calls

    return message, extra_messages


def _convert_gemini_type_to_openai(gemini_type: str) -> str:
    """
    Convert Gemini parameter type format to OpenAI format.
    
    Gemini uses uppercase types: BOOLEAN, STRING, OBJECT, ARRAY, INTEGER, NUMBER
    OpenAI uses lowercase types: boolean, string, object, array, integer, number
    
    Args:
        gemini_type: Gemini format type (uppercase)
        
    Returns:
        str: OpenAI format type (lowercase)
    """
    type_mapping = {
        "BOOLEAN": "boolean",
        "STRING": "string", 
        "OBJECT": "object",
        "ARRAY": "array",
        "INTEGER": "integer",
        "NUMBER": "number",
    }
    return type_mapping.get(gemini_type, gemini_type.lower())


def _convert_gemini_parameters_to_openai(parameters: Dict) -> Dict:
    """
    Recursively convert Gemini parameter schema to OpenAI format.
    
    This function converts:
    - Type names from uppercase to lowercase (BOOLEAN -> boolean)
    - Recursively processes nested objects and arrays
    
    Args:
        parameters: Gemini format parameter schema
        
    Returns:
        Dict: OpenAI format parameter schema
    """
    if not isinstance(parameters, dict):
        return parameters
        
    converted = {}
    
    for key, value in parameters.items():
        if key == "type" and isinstance(value, str):
            # Convert type from Gemini format to OpenAI format
            converted[key] = _convert_gemini_type_to_openai(value)
        elif key == "properties" and isinstance(value, dict):
            # Recursively convert properties
            converted[key] = {
                prop_name: _convert_gemini_parameters_to_openai(prop_value)
                for prop_name, prop_value in value.items()
            }
        elif key == "items" and isinstance(value, dict):
            # Recursively convert array items schema
            converted[key] = _convert_gemini_parameters_to_openai(value)
        else:
            # Copy other fields as-is
            converted[key] = value
            
    return converted


def _convert_gemini_tools_to_openai(gemini_tools: List[Dict]) -> List[Dict]:
    """
    Convert Gemini tools format to OpenAI tools format.

    Gemini format:
    [
        {
            "functionDeclarations": [
                {
                    "name": "function_name",
                    "description": "Function description",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "param1": {"type": "STRING", "description": "..."}
                        }
                    }
                }
            ]
        }
    ]

    OpenAI format:
    [
        {
            "type": "function",
            "function": {
                "name": "function_name",
                "description": "Function description",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param1": {"type": "string", "description": "..."}
                    }
                }
            }
        }
    ]

    Args:
        gemini_tools: List of Gemini format tools

    Returns:
        List[Dict]: OpenAI format tools with converted parameter types
    """
    openai_tools = []

    for tool in gemini_tools:
        if "functionDeclarations" in tool:
            for func_decl in tool["functionDeclarations"]:
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": func_decl.get("name", ""),
                        "description": func_decl.get("description", ""),
                    }
                }

                # Add parameters if present, with type conversion
                if "parameters" in func_decl:
                    openai_tool["function"]["parameters"] = _convert_gemini_parameters_to_openai(
                        func_decl["parameters"]
                    )

                openai_tools.append(openai_tool)

    return openai_tools


def _convert_gemini_to_openai_format(raw_data: dict) -> dict:
    """
    Convert Gemini format request to OpenAI format.

    Args:
        raw_data: Raw logfire data with Gemini format

    Returns:
        dict: Modified raw_data with OpenAI format in request body
    """
    try:
        # Create a copy to avoid modifying the original
        converted_data = json.loads(json.dumps(raw_data))

        attributes = converted_data.get("attributes", {})
        request_body = attributes.get("http.request.body.text", {})

        # Extract Gemini data
        contents = request_body.get("contents", [])
        system_instruction = request_body.get("systemInstruction")
        tools = request_body.get("tools", [])
        generation_config = request_body.get("generationConfig", {})

        # Convert to OpenAI format
        openai_messages = []

        # Add system instruction as first system message
        if system_instruction and "parts" in system_instruction:
            system_content = _convert_gemini_parts_to_content(
                system_instruction["parts"]
            )
            if system_content:
                openai_messages.append({"role": "system", "content": system_content})

        # Convert contents to messages
        tool_call_state: Dict[str, Any] = {
            "counter": 1,
            "pending": {},
            "pending_by_name": {},
        }

        for content in contents:
            role = content.get("role", "user")
            parts = content.get("parts", [])

            # Map Gemini roles to OpenAI roles
            if role == "model":
                role = "assistant"

            message, extra_messages = _convert_gemini_parts_to_openai_message(
                parts, role, tool_call_state
            )
            if message:
                openai_messages.append(message)
            if extra_messages:
                openai_messages.extend(extra_messages)

        # Extract model name from URL
        model_name = _extract_model_from_url(raw_data)

        # Build OpenAI format request body
        openai_request_body = {"messages": openai_messages, "model": model_name}

        # Convert tools if present
        if tools:
            openai_tools = _convert_gemini_tools_to_openai(tools)
            if openai_tools:
                openai_request_body["tools"] = openai_tools

        # Convert generation config to OpenAI parameters
        if generation_config:
            if "temperature" in generation_config:
                openai_request_body["temperature"] = generation_config["temperature"]
            if "maxOutputTokens" in generation_config:
                openai_request_body["max_tokens"] = generation_config["maxOutputTokens"]
            if "topP" in generation_config:
                openai_request_body["top_p"] = generation_config["topP"]

        # Update the converted data
        converted_data["attributes"]["http.request.body.text"] = openai_request_body

        logger.debug(
            f"Converted Gemini format to OpenAI format: {len(openai_messages)} messages, model: {model_name}"
        )

        return converted_data

    except Exception as e:
        logger.error(f"Failed to convert Gemini to OpenAI format: {e}")
        raise ValueError(f"Failed to convert Gemini format: {str(e)}") from e


def _detect_data_source(raw_data: dict) -> str:
    """
    Detect the data source format of the raw data.

    Args:
        raw_data: Raw data to analyze

    Returns:
        str: "http_body" for http.request.body.text format,
             "pydantic_ai" for gen_ai.* format,
             "unknown" otherwise
    """
    attributes = raw_data.get("attributes", {})

    # Check for pydantic-ai OpenTelemetry format (gen_ai.* attributes)
    if "gen_ai.input.messages" in attributes:
        return "pydantic_ai"

    # Check for HTTP body format
    if "http.request.body.text" in attributes:
        return "http_body"

    return "unknown"


def _validate_pydantic_ai_format(attributes: dict) -> bool:
    """
    Validate pydantic-ai OpenTelemetry format.

    Args:
        attributes: The attributes dict from raw data

    Returns:
        bool: True if format is valid
    """
    # Must have gen_ai.input.messages as a list
    input_messages = attributes.get("gen_ai.input.messages")
    if not isinstance(input_messages, list) or not input_messages:
        return False

    # Must have gen_ai.request.model as a string
    model = attributes.get("gen_ai.request.model")
    if not isinstance(model, str) or not model:
        return False

    # Validate message format - each message should have role and parts
    for message in input_messages:
        if not isinstance(message, dict):
            return False
        if "role" not in message:
            return False
        if "parts" not in message or not isinstance(message["parts"], list):
            return False

    return True


def _convert_pydantic_ai_parts_to_content(parts: List[Dict]) -> str:
    """
    Convert pydantic-ai parts array to content string.

    Args:
        parts: List of parts from pydantic-ai format

    Returns:
        str: Combined content string
    """
    content_parts = []
    for part in parts:
        # pydantic-ai uses "content" key, while Gemini uses "text"
        if "content" in part:
            content_parts.append(str(part["content"]))
        elif "text" in part:
            content_parts.append(str(part["text"]))

    return "\n".join(content_parts)


def _convert_pydantic_ai_tool_to_openai(tool: Dict) -> Dict:
    """
    Convert pydantic-ai output_tool format to OpenAI tool format.

    Args:
        tool: pydantic-ai tool definition

    Returns:
        Dict: OpenAI format tool
    """
    return {
        "type": "function",
        "function": {
            "name": tool.get("name", ""),
            "description": tool.get("description", ""),
            "parameters": tool.get("parameters_json_schema", {}),
        },
    }


def _convert_pydantic_ai_to_openai_format(raw_data: dict) -> dict:
    """
    Convert pydantic-ai OpenTelemetry format to standard format for parsing.

    This creates a synthetic http.request.body.text structure from gen_ai.* attributes.

    Args:
        raw_data: Raw logfire data with pydantic-ai format

    Returns:
        dict: Modified raw_data with OpenAI format in request body
    """
    try:
        # Create a copy to avoid modifying the original
        converted_data = json.loads(json.dumps(raw_data))

        attributes = converted_data.get("attributes", {})

        # Convert pydantic-ai messages to OpenAI format
        openai_messages = []

        # Extract system instructions if present (gen_ai.system_instructions)
        # This is separate from gen_ai.input.messages in pydantic-ai format
        system_instructions = attributes.get("gen_ai.system_instructions", [])
        if system_instructions:
            # system_instructions is a list of instruction objects with parts
            system_content_parts = []
            for instruction in system_instructions:
                if isinstance(instruction, dict) and "content" in instruction:
                    # Direct content format
                    system_content_parts.append(str(instruction["content"]))
                elif isinstance(instruction, dict) and "parts" in instruction:
                    # Parts format (similar to messages)
                    parts = instruction.get("parts", [])
                    content = _convert_pydantic_ai_parts_to_content(parts)
                    if content:
                        system_content_parts.append(content)
                elif isinstance(instruction, str):
                    # Plain string format
                    system_content_parts.append(instruction)

            if system_content_parts:
                system_content = "\n".join(system_content_parts)
                openai_messages.append({"role": "system", "content": system_content})
                logger.debug(
                    f"Extracted system instructions: {len(system_content)} chars"
                )

        # Extract input messages
        input_messages = attributes.get("gen_ai.input.messages", [])

        # Convert pydantic-ai messages to OpenAI format
        for msg in input_messages:
            role = msg.get("role", "user")
            parts = msg.get("parts", [])

            # Extract content from parts
            content = _convert_pydantic_ai_parts_to_content(parts)

            openai_messages.append({"role": role, "content": content})

        # Extract model name
        model_name = attributes.get("gen_ai.request.model", "")

        # Build OpenAI format request body
        openai_request_body = {"messages": openai_messages, "model": model_name}

        # Extract model settings
        if "gen_ai.request.temperature" in attributes:
            openai_request_body["temperature"] = attributes["gen_ai.request.temperature"]
        if "gen_ai.request.max_tokens" in attributes:
            openai_request_body["max_tokens"] = attributes["gen_ai.request.max_tokens"]

        # Extract tools from model_request_parameters if present
        model_params = attributes.get("model_request_parameters", {})
        tools = []

        # Collect from function_tools
        function_tools = model_params.get("function_tools", [])
        if function_tools:
            for tool in function_tools:
                tools.append(_convert_pydantic_ai_tool_to_openai(tool))

        # Collect from output_tools
        output_tools = model_params.get("output_tools", [])
        if output_tools:
            for tool in output_tools:
                tools.append(_convert_pydantic_ai_tool_to_openai(tool))

        if tools:
            openai_request_body["tools"] = tools

        # Update the converted data
        converted_data["attributes"]["http.request.body.text"] = openai_request_body

        logger.debug(
            f"Converted pydantic-ai format to OpenAI format: "
            f"{len(openai_messages)} messages, model: {model_name}"
        )

        return converted_data

    except Exception as e:
        logger.error(f"Failed to convert pydantic-ai to OpenAI format: {e}")
        raise ValueError(f"Failed to convert pydantic-ai format: {str(e)}") from e


def validate_raw_data_format(raw_data: dict) -> bool:
    """
    Validate that raw data has the expected logfire format.
    Supports OpenAI, Google Gemini, and pydantic-ai OpenTelemetry formats.

    Args:
        raw_data: Raw data to validate

    Returns:
        bool: True if format is valid
    """
    try:
        # Check basic structure
        if not isinstance(raw_data, dict):
            return False

        attributes = raw_data.get("attributes")
        if not isinstance(attributes, dict):
            return False

        # Detect data source format
        data_source = _detect_data_source(raw_data)

        if data_source == "pydantic_ai":
            # Validate pydantic-ai format
            is_valid = _validate_pydantic_ai_format(attributes)
            if is_valid:
                logger.debug("Raw data format validation passed (pydantic-ai format)")
            else:
                logger.debug("Raw data format validation failed (pydantic-ai format)")
            return is_valid

        elif data_source == "http_body":
            # Original HTTP body format - validate OpenAI or Gemini
            request_body = attributes.get("http.request.body.text")
            if not isinstance(request_body, dict):
                return False

            # Detect and validate format
            api_format = _detect_api_format(request_body)

            if api_format == "openai":
                is_valid = _validate_openai_format(request_body)
            elif api_format == "gemini":
                is_valid = _validate_gemini_format(request_body)
            else:
                logger.debug("Unknown API format detected")
                return False

            if is_valid:
                logger.debug(f"Raw data format validation passed ({api_format} format)")
            else:
                logger.debug(f"Raw data format validation failed ({api_format} format)")

            return is_valid

        else:
            logger.debug("Unknown data source format detected")
            return False

    except Exception as e:
        logger.debug(f"Raw data format validation failed: {e}")
        return False


def extract_model_info(raw_data: dict) -> Dict[str, str]:
    """
    Extract model information from raw data.
    Supports OpenAI, Google Gemini, and pydantic-ai OpenTelemetry formats.

    Args:
        raw_data: Raw logfire data

    Returns:
        Dict with model information
    """
    try:
        attributes = raw_data.get("attributes", {})

        # Detect data source format
        data_source = _detect_data_source(raw_data)

        if data_source == "pydantic_ai":
            # pydantic-ai format: model is in gen_ai.request.model
            model_name = attributes.get("gen_ai.request.model", "")
            # Extract provider from model name if it follows provider/model format
            provider = ""
            if "/" in model_name:
                provider = model_name.split("/", 1)[0]
            elif ":" in model_name:
                provider = model_name.split(":", 1)[0]

            return {
                "full_model_name": model_name,
                "provider": provider,
                "model_only": (
                    model_name.split("/", 1)[-1]
                    if "/" in model_name
                    else model_name.split(":", 1)[-1]
                    if ":" in model_name
                    else model_name
                ),
            }

        # HTTP body format
        request_body = attributes.get("http.request.body.text", {})

        # Detect API format
        api_format = _detect_api_format(request_body)

        if api_format == "gemini":
            # Extract model from URL for Gemini format
            model_name = _extract_model_from_url(raw_data)
            provider = "google"
        else:
            # OpenAI format
            model_name = request_body.get("model", "")
            # Extract provider from model name if it follows provider:model format
            provider = ""
            if ":" in model_name:
                provider = model_name.split(":", 1)[0]

        return {
            "full_model_name": model_name,
            "provider": provider,
            "model_only": (
                model_name.split(":", 1)[-1] if ":" in model_name else model_name
            ),
        }

    except Exception as e:
        logger.error(f"Failed to extract model info: {e}")
        return {"full_model_name": "", "provider": "", "model_only": ""}


__all__ = ["parse_llm_raw_data", "validate_raw_data_format", "extract_model_info"]
