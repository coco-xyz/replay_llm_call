"""
Custom Exceptions

Application-specific exception classes.

USAGE GUIDELINES:
- Always use ErrorCode enum members, not string literals
- Each exception subclass should use its corresponding domain error code
- Use the wrap() class method to preserve exception chains when wrapping lower-level exceptions
- Business validation errors use ValidationErrorCode (HTTP 400)
- Request format validation errors use FastAPI RequestValidationError (HTTP 422)

NOTE: When using this template in your project, you may want to rename ApplicationException
to match your project name (e.g., MyProjectException, YourAppException, etc.)
"""

import json
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from src.core.error_codes import ErrorCode


def _safe_serialize(obj: Any) -> Any:
    """Safely serialize an object for JSON, using repr() for non-serializable objects."""
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return repr(obj)


class ApplicationException(Exception):
    """Base exception for application-specific errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional["ErrorCode | str"] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for serialization with safe handling."""
        # Safely serialize details to prevent JSON serialization errors
        safe_details = {k: _safe_serialize(v) for k, v in self.details.items()}

        result = {
            "message": self.message,
            "code": (
                self.error_code.value
                if self.error_code is not None and hasattr(self.error_code, "value")
                else self.error_code
            ),
            "details": safe_details,
        }

        # Include exception chain information for better observability
        # Priority: custom cause > __cause__ > __context__
        cause = (
            self.cause
            or getattr(self, "__cause__", None)
            or getattr(self, "__context__", None)
        )
        if cause:
            result["cause"] = {"type": cause.__class__.__name__, "message": str(cause)}

        return result

    @classmethod
    def wrap(
        cls,
        exc: Exception,
        message: str,
        error_code: Optional["ErrorCode"] = None,
        **context: Any,
    ) -> "ApplicationException":
        """
        Wrap a lower-level exception into a business exception while preserving the exception chain.

        Args:
            exc: The original exception to wrap
            message: Business-level error message
            error_code: ErrorCode enum member (strongly recommended over string)
            **context: Additional context to include in details

        Returns:
            New exception instance with preserved exception chain

        Example:
            try:
                db.query(sql)
            except Exception as e:
                raise DatabaseException.wrap(
                    e, "Failed to fetch user data",
                    DatabaseErrorCode.QUERY_FAILED,
                    sql=sql, user_id=user_id
                )
        """
        return cls(message=message, error_code=error_code, details=context, cause=exc)

    def with_context(self, **kwargs: Any) -> "ApplicationException":
        """Add context details to the exception."""
        self.details.update(kwargs)
        return self

    def __str__(self) -> str:
        """String representation with error code and details."""
        parts = [self.message]
        if self.error_code:
            code_str = (
                self.error_code.value
                if hasattr(self.error_code, "value")
                else self.error_code
            )
            parts.append(f"[{code_str}]")
        if self.details:
            parts.append(f"Details: {self.details}")
        return " ".join(parts)

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_code={self.error_code!r}, "
            f"details={self.details!r}, "
            f"cause={self.cause!r})"
        )

    @property
    def http_status(self) -> int:
        """Get HTTP status code for this exception (lazy-loaded)."""
        if self.error_code:
            from src.core.error_codes import get_http_status_code

            return get_http_status_code(self.error_code)
        return 500


class ConfigurationException(ApplicationException):
    """Exception raised for configuration-related errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional["ErrorCode | str"] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code, details, **kwargs)


class DatabaseException(ApplicationException):
    """Exception raised for database-related errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional["ErrorCode | str"] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code, details, **kwargs)


class RedisException(ApplicationException):
    """Exception raised for Redis-related errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional["ErrorCode | str"] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code, details, **kwargs)


class AgentException(ApplicationException):
    """Exception raised for agent-related errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional["ErrorCode | str"] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code, details, **kwargs)


class APIException(ApplicationException):
    """Exception raised for API-related errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional["ErrorCode | str"] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code, details, **kwargs)


class ValidationException(ApplicationException):
    """Exception raised for validation errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional["ErrorCode | str"] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code, details, **kwargs)


class InternalServiceException(ApplicationException):
    """Exception raised for internal service errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional["ErrorCode | str"] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code, details, **kwargs)


class RequestParamException(ApplicationException):
    """Exception raised for request parameter errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional["ErrorCode | str"] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code, details, **kwargs)


class AuthException(ApplicationException):
    """Exception raised for authentication/authorization errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional["ErrorCode | str"] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code, details, **kwargs)


class LLMCallException(ApplicationException):
    """Exception raised for LLM call errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional["ErrorCode | str"] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code, details, **kwargs)


class DataProcessException(ApplicationException):
    """Exception raised for data processing errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional["ErrorCode | str"] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code, details, **kwargs)


class CallbackServiceException(ApplicationException):
    """Exception raised for callback service errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional["ErrorCode | str"] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, error_code, details, **kwargs)
