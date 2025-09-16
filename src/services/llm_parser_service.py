"""
LLM Parser Service

Service for parsing logfire raw data and extracting LLM request components.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from src.core.logger import get_logger

logger = get_logger(__name__)

class ParsedLLMData(BaseModel):
    """Parsed LLM data from raw logfire data for service layer use."""

    # Original data (used for replay concatenation)
    middle_messages: List[Dict] = Field(..., description="Messages except system prompt and last user message")
    tools: Optional[List[Dict]] = Field(None, description="Tools configuration")
    model_name: str = Field(..., description="Model name")

    # Parsed key data (used for page display and replay concatenation)
    system_prompt: str = Field(..., description="System prompt")
    last_user_message: str = Field(..., description="Last user message")

def parse_llm_raw_data(raw_data: dict) -> ParsedLLMData:
    """
    Parse logfire raw data and separate system prompt, last user message, and other messages.
    
    This function implements the optimized storage strategy where:
    - System prompt (first system message) is extracted separately
    - Last user message is extracted separately  
    - All other messages are stored in original_messages for replay concatenation
    
    Args:
        raw_data: Raw logfire data containing the LLM request
        
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
            
        request_body = attributes.get("http.request.body.text", {})
        if not request_body:
            raise ValueError("Missing 'http.request.body.text' in raw data")
        
        # Extract original data
        all_messages = request_body.get("messages", [])
        tools = request_body.get("tools", [])
        model_name = request_body.get("model", "")

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
            if all_messages[i].get("role") == "user":
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
            f"tools={len(tools) if tools else 0} items"
        )

        return ParsedLLMData(
            middle_messages=middle_messages,
            tools=tools if tools else None,
            model_name=model_name,
            system_prompt=system_prompt,
            last_user_message=last_user_message
        )
        
    except (KeyError, ValueError) as e:
        logger.error(f"Failed to parse LLM raw data: {e}")
        raise ValueError(f"Invalid raw data format: {str(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error parsing LLM raw data: {e}")
        raise ValueError(f"Failed to parse raw data: {str(e)}") from e


def validate_raw_data_format(raw_data: dict) -> bool:
    """
    Validate that raw data has the expected logfire format.
    
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
            
        request_body = attributes.get("http.request.body.text")
        if not isinstance(request_body, dict):
            return False
            
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
                
        logger.debug("Raw data format validation passed")
        return True
        
    except Exception as e:
        logger.debug(f"Raw data format validation failed: {e}")
        return False


def extract_model_info(raw_data: dict) -> Dict[str, str]:
    """
    Extract model information from raw data.
    
    Args:
        raw_data: Raw logfire data
        
    Returns:
        Dict with model information
    """
    try:
        attributes = raw_data.get("attributes", {})
        request_body = attributes.get("http.request.body.text", {})
        
        model_name = request_body.get("model", "")
        
        # Extract provider from model name if it follows provider:model format
        provider = ""
        if ":" in model_name:
            provider = model_name.split(":", 1)[0]
        
        return {
            "full_model_name": model_name,
            "provider": provider,
            "model_only": model_name.split(":", 1)[-1] if ":" in model_name else model_name
        }
        
    except Exception as e:
        logger.error(f"Failed to extract model info: {e}")
        return {
            "full_model_name": "",
            "provider": "",
            "model_only": ""
        }


__all__ = ["parse_llm_raw_data", "validate_raw_data_format", "extract_model_info"]
