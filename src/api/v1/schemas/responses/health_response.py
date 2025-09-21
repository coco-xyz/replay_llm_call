"""
Health Check Response Schemas

Response models for API health check endpoints.
"""

from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Response model for API health check endpoint."""

    status: str = Field(
        ..., description="Overall health status", examples=["healthy", "unhealthy"]
    )
    timestamp: str = Field(..., description="Health check timestamp (ISO format)")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Environment name")
    components: Dict[str, Any] = Field(
        ..., description="Health status of individual components"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T10:30:00.000Z",
                "version": "1.0.0",
                "environment": "development",
                "components": {
                    "api": {
                        "status": "healthy",
                        "version": "1.0.0",
                        "environment": "development",
                    },
                    "database": {
                        "status": "healthy",
                        "details": {"pool_size": 10, "checked_out": 0, "overflow": 0},
                    },
                    "redis": {
                        "status": "healthy",
                        "details": {"ping_time_ms": 1.23, "redis_version": "7.0.0"},
                    },
                },
            }
        }
    )
