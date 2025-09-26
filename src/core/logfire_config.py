"""
Logfire Configuration Module

Centralized logfire configuration and instrumentation setup for replay-llm-call.
This module provides reusable functions for setting up logfire monitoring that can be
used across the application and in tests.

Usage:
    from src.core.logfire_config import initialize_logfire

    # Initialize logfire with optional FastAPI app
    results = initialize_logfire(app)  # idempotent; safe to call at startup
    # results: {"configured": bool, "instrumentation": {...}}
"""

import logging
from typing import Any, Dict, Optional, Union

import logfire
from fastapi import FastAPI, Request, WebSocket

from src.core.config import settings
from src.core.logger import setup_logfire_handler


class _LogfireState:
    """Internal state management for logfire configuration."""

    def __init__(self) -> None:
        self.configured = False
        self.instrumented = False
        self.instrument_results: Dict[str, bool] = {
            "pydantic_ai": False,
            "redis": False,
            "httpx": False,
        }

    def is_configured(self) -> bool:
        """Check if logfire has been configured."""
        return self.configured

    def set_configured(self, value: bool) -> None:
        """Set the logfire configuration status."""
        self.configured = value

    def is_instrumented(self) -> bool:
        """Check if logfire instrumentation has been set up."""
        return self.instrumented

    def set_instrumented(self, value: bool) -> None:
        """Set the logfire instrumentation status."""
        self.instrumented = value

    def get_instrument_results(self) -> Dict[str, bool]:
        """Get a copy of the current instrumentation results."""
        return self.instrument_results.copy()

    def update_instrument_result(self, key: str, value: bool) -> None:
        """Update the result for a specific instrumentation component."""
        self.instrument_results[key] = value


# Module-level state instance
_state = _LogfireState()


def _custom_scrub_callback(match: Any) -> Any:
    """
    Custom scrubbing callback that allows session_id fields while keeping other protections.

    Args:
        match: ScrubMatch object containing path, value, and pattern_match

    Returns:
        The original value if it should be kept, None if it should be redacted
    """
    # Get the path as a tuple of keys
    path = match.path

    allowed_keys = {
        "sid", # sid is used to identify the chat session, injected in logger.py
        "http.request.body.text", # prevent the LLM’s input parameters from being redacted. 
    }
    if any(str(part).lower() in allowed_keys for part in path):
        return match.value

    # For all other matches, use default behavior (redact)
    return None


def custom_request_attributes_mapper(
    request: Union[Request, WebSocket], attributes: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Custom request attributes mapper for logfire.

    This function customizes what information gets logged for each request.
    It filters sensitive information and focuses on useful debugging data.

    Args:
        request: The FastAPI request or WebSocket object
        attributes: Default attributes dictionary from logfire

    Returns:
        dict or None: Customized attributes dict, or None to set span level to 'debug'
    """
    # Always log validation errors as they're important for debugging
    if attributes.get("errors"):
        # Handle both Request and WebSocket objects
        endpoint = (
            str(request.url.path)
            if hasattr(request, "url")
            else getattr(request, "path", "unknown")
        )
        method = getattr(request, "method", "WebSocket")
        user_agent = (
            request.headers.get("user-agent", "unknown")
            if hasattr(request, "headers")
            else "unknown"
        )
        request_id = (
            request.headers.get("x-request-id") if hasattr(request, "headers") else None
        )

        return {
            "errors": attributes["errors"],
            "endpoint": endpoint,
            "method": method,
            "user_agent": user_agent,
            "request_id": request_id,
        }

    # For successful requests, log basic info but hide sensitive data
    filtered_values = {}
    session_id = None

    if attributes.get("values"):
        for key, value in attributes["values"].items():
            # Explicitly preserve session_id fields
            if key.lower() in ["session_id", "sid"]:
                filtered_values[key] = value
                session_id = value
            # Filter out sensitive information
            elif key.lower() in ["password", "token", "api_key", "secret"]:
                filtered_values[key] = "[REDACTED]"
            elif key == "file" and hasattr(value, "filename"):
                # For file uploads, just log filename and size
                filtered_values[key] = {
                    "filename": getattr(value, "filename", "unknown"),
                    "content_type": getattr(value, "content_type", "unknown"),
                    "size": (
                        getattr(value, "size", 0)
                        if hasattr(value, "size")
                        else "unknown"
                    ),
                }
            else:
                filtered_values[key] = value

    # Handle both Request and WebSocket objects for result
    endpoint = (
        str(request.url.path)
        if hasattr(request, "url")
        else getattr(request, "path", "unknown")
    )
    method = getattr(request, "method", "WebSocket")
    request_id = (
        request.headers.get("x-request-id") if hasattr(request, "headers") else None
    )

    result = {
        "values": filtered_values,
        "endpoint": endpoint,
        "method": method,
        "request_id": request_id,
    }

    # Explicitly add session_id at the top level if found
    if session_id:
        result["session_id"] = session_id

    return result


def setup_logfire() -> bool:
    """
    Set up basic logfire configuration.

    Returns:
        bool: True if logfire was successfully configured, False otherwise
    """
    logger = logging.getLogger("replay_llm_call.logfire")

    if not settings.logfire__enabled or _state.is_configured():
        return _state.is_configured()

    try:
        config_kwargs: Dict[str, Any] = {
            "service_name": settings.logfire__service_name,
            "environment": settings.logfire__environment,
        }

        # Configure scrubbing to allow session_id fields
        if settings.logfire__disable_scrubbing:
            # Completely disable scrubbing if explicitly requested
            config_kwargs["scrubbing"] = False
        else:
            # Use custom scrubbing options to allow session_id while keeping other protections
            try:
                config_kwargs["scrubbing"] = logfire.ScrubbingOptions(
                    callback=_custom_scrub_callback
                )
            except (AttributeError, TypeError) as e:
                # Fallback: if ScrubbingOptions is not available or API changed
                logger.warning("ScrubbingOptions not available or API changed: %s", e)
                logger.warning("Falling back to default scrubbing")
                config_kwargs["scrubbing"] = True

        # Handle token (SecretStr compatible)
        if settings.logfire__token:
            token_value: str
            if hasattr(settings.logfire__token, "get_secret_value"):
                token_value = settings.logfire__token.get_secret_value()
            else:
                token_value = str(settings.logfire__token)
            config_kwargs["token"] = token_value
        # Note: sample_rate is commented out as it's not supported in current version
        # if settings.logfire__sample_rate is not None:
        #     try:
        #         config_kwargs["sample_rate"] = settings.logfire__sample_rate
        #     except TypeError:
        #         logging.warning("sample_rate parameter not supported in this logfire version")

        logfire.configure(**config_kwargs)
        startup_logger = logging.getLogger("replay_llm_call.startup")
        startup_logger.info(
            "Logfire initialized for service: %s", settings.logfire__service_name
        )

        # Set up Logfire logging handler after configuration
        setup_logfire_handler()

        _state.set_configured(True)
        return True

    except Exception as e:
        logger.error("Failed to initialize logfire: %s", e)
        return False


def instrument_logfire() -> Dict[str, bool]:
    """
    Set up logfire instrumentation for various libraries.

    Returns:
        dict: Dictionary with instrumentation results for each library
    """
    logger = logging.getLogger("replay_llm_call.logfire")

    if not settings.logfire__enabled:
        return _state.get_instrument_results()

    if _state.is_instrumented():
        return _state.get_instrument_results()

    try:
        # Instrument pydantic-ai
        if settings.logfire__instrument__pydantic_ai:
            try:
                logfire.instrument_pydantic_ai()
                logger.info("Logfire pydantic-ai instrumentation enabled")
                _state.update_instrument_result("pydantic_ai", True)
            except Exception as e:
                logger.warning("Failed to instrument pydantic-ai with logfire: %s", e)

        # Instrument Redis
        if settings.logfire__instrument__redis:
            try:
                logfire.instrument_redis()
                logger.info("Logfire Redis instrumentation enabled")
                _state.update_instrument_result("redis", True)
            except Exception as e:
                logger.warning("Failed to instrument Redis with logfire: %s", e)

        # Instrument HTTPX
        if settings.logfire__instrument__httpx:
            try:
                capture_all = settings.logfire__httpx_capture_all
                logfire.instrument_httpx(capture_all=capture_all)
                logger.info(
                    "Logfire HTTPX instrumentation enabled (capture_all=%s)",
                    capture_all,
                )
                _state.update_instrument_result("httpx", True)
            except Exception as e:
                logger.warning("Failed to instrument HTTPX with logfire: %s", e)

        _state.set_instrumented(True)

    except ImportError:
        logger.warning("Logfire not available for instrumentation")
    except Exception as e:
        logger.error("Failed to set up logfire instrumentation: %s", e)

    return _state.get_instrument_results()


def instrument_fastapi(app: FastAPI) -> bool:
    """
    Set up logfire instrumentation for FastAPI.

    Args:
        app: The FastAPI application instance

    Returns:
        bool: True if FastAPI was successfully instrumented, False otherwise
    """
    logger = logging.getLogger("replay_llm_call.logfire")

    if not settings.logfire__enabled or not settings.logfire__instrument__fastapi:
        return False

    try:
        logfire.instrument_fastapi(
            app,
            request_attributes_mapper=custom_request_attributes_mapper,
            capture_headers=True,
        )
        logger.info("FastAPI instrumented with logfire")
        return True

    except Exception as e:
        logger.error("Failed to instrument FastAPI with logfire: %s", e)
        return False


def initialize_logfire(app: Optional[FastAPI] = None) -> Dict[str, Any]:
    """
    Complete logfire initialization including configuration and instrumentation.

    Args:
        app: Optional FastAPI application instance for instrumentation

    Returns:
        dict: Initialization results with status for each component
    """
    results: Dict[str, Any] = {
        "configured": False,
        "instrumentation": {
            "pydantic_ai": False,
            "redis": False,
            "httpx": False,
            "fastapi": False,
        },
    }

    # Set up basic logfire configuration
    results["configured"] = setup_logfire()

    if results["configured"]:
        # Set up library instrumentation
        instrumentation_results = instrument_logfire()
        results["instrumentation"].update(instrumentation_results)

        # Set up FastAPI instrumentation if app is provided
        if app is not None:
            results["instrumentation"]["fastapi"] = instrument_fastapi(app)

    return results


def is_logfire_enabled() -> bool:
    """
    Check if logfire is enabled in settings.

    Returns:
        bool: True if logfire is enabled, False otherwise
    """
    return settings.logfire__enabled


def get_logfire_service_name() -> str:
    """
    Get the configured logfire service name.

    Returns:
        str: The logfire service name
    """
    return settings.logfire__service_name


def get_logfire_environment() -> str:
    """
    Get the configured logfire environment.

    Returns:
        str: The logfire environment
    """
    return settings.logfire__environment
