"""
Error Codes

Standardized error codes for replay-llm-call.
"""

from enum import StrEnum
from types import MappingProxyType
from typing import Any, Dict, Mapping


class ErrorCode(StrEnum):
    """Base error code enum (string-based)."""


class ConfigurationErrorCode(ErrorCode):
    """Configuration-related error codes."""

    INVALID_CONFIG = "CONFIGURATION_INVALID_CONFIG"
    MISSING_CONFIG = "CONFIGURATION_MISSING_CONFIG"
    CONFIG_LOAD_FAILED = "CONFIGURATION_LOAD_FAILED"


class DatabaseErrorCode(ErrorCode):
    """Database-related error codes."""

    CONNECTION_FAILED = "DATABASE_CONNECTION_FAILED"
    QUERY_FAILED = "DATABASE_QUERY_FAILED"
    TRANSACTION_FAILED = "DATABASE_TRANSACTION_FAILED"
    MIGRATION_FAILED = "DATABASE_MIGRATION_FAILED"


class RedisErrorCode(ErrorCode):
    """Redis-related error codes."""

    CONNECTION_FAILED = "REDIS_CONNECTION_FAILED"
    OPERATION_FAILED = "REDIS_OPERATION_FAILED"
    LOCK_FAILED = "REDIS_LOCK_FAILED"


class AgentErrorCode(ErrorCode):
    """Agent-related error codes."""

    INIT_FAILED = "AGENT_INIT_FAILED"
    RUN_FAILED = "AGENT_RUN_FAILED"
    TIMEOUT = "AGENT_TIMEOUT"
    INVALID_CONFIG = "AGENT_INVALID_CONFIG"


class APIErrorCode(ErrorCode):
    """API-related error codes."""

    INVALID_REQUEST = "API_INVALID_REQUEST"
    UNAUTHORIZED = "API_UNAUTHORIZED"
    FORBIDDEN = "API_FORBIDDEN"
    NOT_FOUND = "API_NOT_FOUND"
    METHOD_NOT_ALLOWED = "API_METHOD_NOT_ALLOWED"
    RATE_LIMITED = "API_RATE_LIMITED"
    INTERNAL_ERROR = "API_INTERNAL_ERROR"


class ValidationErrorCode(ErrorCode):
    """Validation-related error codes."""

    INVALID_INPUT = "VALIDATION_INVALID_INPUT"
    MISSING_FIELD = "VALIDATION_MISSING_FIELD"
    INVALID_FORMAT = "VALIDATION_INVALID_FORMAT"
    VALUE_OUT_OF_RANGE = "VALIDATION_VALUE_OUT_OF_RANGE"


class LLMErrorCode(ErrorCode):
    """LLM-related error codes."""

    API_KEY_INVALID = "LLM_API_KEY_INVALID"
    API_QUOTA_EXCEEDED = "LLM_API_QUOTA_EXCEEDED"
    MODEL_NOT_FOUND = "LLM_MODEL_NOT_FOUND"
    REQUEST_FAILED = "LLM_REQUEST_FAILED"
    TIMEOUT = "LLM_TIMEOUT"


class InternalServiceErrorCode(ErrorCode):
    """Internal service error codes."""

    SERVICE_UNAVAILABLE = "INTERNAL_SERVICE_UNAVAILABLE"
    OPERATION_FAILED = "INTERNAL_OPERATION_FAILED"
    INTERNAL_TIMEOUT = "INTERNAL_TIMEOUT"
    SNOWFLAKE_GENERATION_FAILED = "INTERNAL_SNOWFLAKE_GENERATION_FAILED"


class RequestParamErrorCode(ErrorCode):
    """Request parameter error codes."""

    MISSING_PARAMETER = "REQUEST_PARAM_MISSING"
    INVALID_PARAMETER = "REQUEST_PARAM_INVALID"
    PARAMETER_TYPE_ERROR = "REQUEST_PARAM_TYPE_ERROR"


class AuthErrorCode(ErrorCode):
    """Authentication/authorization error codes."""

    INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    INSUFFICIENT_PERMISSIONS = "AUTH_INSUFFICIENT_PERMISSIONS"


class DataProcessErrorCode(ErrorCode):
    """Data processing error codes."""

    PARSING_FAILED = "DATA_PROCESS_PARSING_FAILED"
    TRANSFORMATION_FAILED = "DATA_PROCESS_TRANSFORMATION_FAILED"
    VALIDATION_FAILED = "DATA_PROCESS_VALIDATION_FAILED"


class CallbackServiceErrorCode(ErrorCode):
    """Callback service error codes."""

    CALLBACK_FAILED = "CALLBACK_SERVICE_FAILED"
    INVALID_CALLBACK_URL = "CALLBACK_SERVICE_INVALID_URL"
    CALLBACK_TIMEOUT = "CALLBACK_SERVICE_TIMEOUT"


# Error code to HTTP status mapping
#
# CONVENTIONS FOR ADDING NEW ERROR CODES:
# 1. Error code names should be descriptive and use UPPER_SNAKE_CASE
# 2. Error code values MUST include domain prefixes for global uniqueness:
#    - DATABASE_*, REDIS_*, AGENT_*, API_*, VALIDATION_*, LLM_*, etc.
#    - This ensures no conflicts when error codes are used in API responses, logs, or external systems
# 3. Always add corresponding HTTP status mapping in this dictionary
# 4. HTTP status code guidelines:
#    - 400: Client errors (bad request, validation failures)
#    - 401: Authentication required
#    - 403: Forbidden (authenticated but not authorized)
#    - 404: Resource not found
#    - 422: Request validation errors (FastAPI RequestValidationError)
#    - 429: Rate limiting
#    - 500: Internal server errors
#    - 503: Service unavailable (external dependencies)
#    - 504: Timeout errors
# 5. ValidationErrorCode uses 400 for business logic validation errors,
#    while FastAPI RequestValidationError uses 422 for request format validation
#
ERROR_CODE_MAP: Mapping[ErrorCode, int] = MappingProxyType(
    {
        # Configuration errors
        ConfigurationErrorCode.INVALID_CONFIG: 500,
        ConfigurationErrorCode.MISSING_CONFIG: 500,
        ConfigurationErrorCode.CONFIG_LOAD_FAILED: 500,
        # Database errors
        DatabaseErrorCode.CONNECTION_FAILED: 503,
        DatabaseErrorCode.QUERY_FAILED: 500,
        DatabaseErrorCode.TRANSACTION_FAILED: 500,
        DatabaseErrorCode.MIGRATION_FAILED: 500,
        # Redis errors
        RedisErrorCode.CONNECTION_FAILED: 503,
        RedisErrorCode.OPERATION_FAILED: 500,
        RedisErrorCode.LOCK_FAILED: 500,
        # Agent errors
        AgentErrorCode.INIT_FAILED: 500,
        AgentErrorCode.RUN_FAILED: 500,
        AgentErrorCode.TIMEOUT: 504,
        AgentErrorCode.INVALID_CONFIG: 500,
        # API errors
        APIErrorCode.INVALID_REQUEST: 400,
        APIErrorCode.UNAUTHORIZED: 401,
        APIErrorCode.FORBIDDEN: 403,
        APIErrorCode.NOT_FOUND: 404,
        APIErrorCode.METHOD_NOT_ALLOWED: 405,
        APIErrorCode.RATE_LIMITED: 429,
        APIErrorCode.INTERNAL_ERROR: 500,
        # Validation errors
        ValidationErrorCode.INVALID_INPUT: 400,
        ValidationErrorCode.MISSING_FIELD: 400,
        ValidationErrorCode.INVALID_FORMAT: 400,
        ValidationErrorCode.VALUE_OUT_OF_RANGE: 400,
        # LLM errors
        LLMErrorCode.API_KEY_INVALID: 401,
        LLMErrorCode.API_QUOTA_EXCEEDED: 429,
        LLMErrorCode.MODEL_NOT_FOUND: 404,
        LLMErrorCode.REQUEST_FAILED: 500,
        LLMErrorCode.TIMEOUT: 504,
        # Internal service errors
        InternalServiceErrorCode.SERVICE_UNAVAILABLE: 503,
        InternalServiceErrorCode.OPERATION_FAILED: 500,
        InternalServiceErrorCode.INTERNAL_TIMEOUT: 504,
        InternalServiceErrorCode.SNOWFLAKE_GENERATION_FAILED: 500,
        # Request parameter errors
        RequestParamErrorCode.MISSING_PARAMETER: 400,
        RequestParamErrorCode.INVALID_PARAMETER: 400,
        RequestParamErrorCode.PARAMETER_TYPE_ERROR: 400,
        # Auth errors
        AuthErrorCode.INVALID_CREDENTIALS: 401,
        AuthErrorCode.TOKEN_EXPIRED: 401,
        AuthErrorCode.INSUFFICIENT_PERMISSIONS: 403,
        # Data processing errors
        DataProcessErrorCode.PARSING_FAILED: 400,
        DataProcessErrorCode.TRANSFORMATION_FAILED: 500,
        DataProcessErrorCode.VALIDATION_FAILED: 400,
        # Callback service errors
        CallbackServiceErrorCode.CALLBACK_FAILED: 500,
        CallbackServiceErrorCode.INVALID_CALLBACK_URL: 400,
        CallbackServiceErrorCode.CALLBACK_TIMEOUT: 504,
    }
)


def _get_status_for_string(error_code_str: str) -> int:
    """Helper function to get status code for string error code."""
    for code in ERROR_CODE_MAP:
        if code.value == error_code_str:
            return ERROR_CODE_MAP[code]
    return 500


def get_http_status_code(error_code: ErrorCode | str) -> int:
    """
    Get HTTP status code for an error code.

    Args:
        error_code: Error code enum or string

    Returns:
        HTTP status code (defaults to 500 if not found)
    """
    if isinstance(error_code, str):
        return _get_status_for_string(error_code)

    # At this point, mypy knows error_code is ErrorCode
    return ERROR_CODE_MAP.get(error_code, 500)  # type: ignore[unreachable]


def get_error_info(error_code: ErrorCode | str) -> Dict[str, Any]:
    """
    Get error information including HTTP status code.

    Args:
        error_code: Error code enum or string

    Returns:
        Dictionary with error information
    """
    code_value = error_code.value if isinstance(error_code, ErrorCode) else error_code
    return {"error_code": code_value, "http_status": get_http_status_code(error_code)}
