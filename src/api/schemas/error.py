"""
API Error Response Schemas

Pydantic models for standardized error responses in FastAPI.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ValidationErrorDetail(BaseModel):
    """Individual validation error detail."""

    loc: List[str | int] = Field(..., description="Location of the error in the input")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")
    ctx: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ErrorDetail(BaseModel):
    """Detailed error information."""

    type: str = Field(..., description="Exception type", examples=["ValidationError"])
    message: str = Field(..., description="Human-readable error message")
    code: Optional[str] = Field(
        None, description="Machine-readable error code", examples=["VALIDATION_ERROR"]
    )
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    debug: Optional[Dict[str, Any]] = Field(
        None, description="Debug information (only in debug mode)"
    )


class ErrorResponse(BaseModel):
    """Standard error response format."""

    model_config = ConfigDict(
        extra="forbid",  # Prevent unexpected fields from being added
        json_schema_extra={
            "examples": [
                {
                    "error": {
                        "type": "ValidationError",
                        "message": "Request validation failed",
                        "code": "VALIDATION_ERROR",
                        "details": {
                            "validation_errors": [
                                {
                                    "loc": ["body", "message"],
                                    "msg": "field required",
                                    "type": "value_error.missing",
                                }
                            ]
                        },
                    },
                    "request_id": "req_123456789",
                    "path": "/api/v1/demo/chat",
                    "method": "POST",
                }
            ]
        },
    )

    error: ErrorDetail = Field(..., description="Error details")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")
    path: Optional[str] = Field(
        None, description="Request path", examples=["/api/v1/demo/chat"]
    )
    method: Optional[str] = Field(None, description="HTTP method", examples=["POST"])
