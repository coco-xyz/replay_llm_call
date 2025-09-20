"""Agent API converters."""

from src.api.v1.schemas.requests import AgentCreateRequest, AgentUpdateRequest
from src.api.v1.schemas.responses.agent_responses import (
    AgentResponse,
    AgentSummaryResponse,
)
from src.services.agent_service import (
    AgentCreateData,
    AgentData,
    AgentSummary,
    AgentUpdateData,
)


def convert_agent_create_request(request: AgentCreateRequest) -> AgentCreateData:
    """Convert API create request to service layer data."""

    return AgentCreateData(
        name=request.name,
        description=request.description,
        default_model_name=request.default_model_name,
        default_system_prompt=request.default_system_prompt,
        default_model_settings=request.default_model_settings,
    )


def convert_agent_update_request(request: AgentUpdateRequest) -> AgentUpdateData:
    """Convert API update request to service layer data."""

    return AgentUpdateData(
        name=request.name,
        description=request.description,
        default_model_name=request.default_model_name,
        default_system_prompt=request.default_system_prompt,
        default_model_settings=request.default_model_settings,
        is_deleted=request.is_deleted,
    )


def convert_agent_data_to_response(data: AgentData) -> AgentResponse:
    """Convert service agent data to API response."""

    return AgentResponse.model_validate(data)


def convert_agent_summary_to_response(
    summary: AgentSummary | None,
) -> AgentSummaryResponse | None:
    """Convert service summary to API summary response."""

    if not summary:
        return None
    return AgentSummaryResponse.model_validate(summary)


__all__ = [
    "convert_agent_create_request",
    "convert_agent_update_request",
    "convert_agent_data_to_response",
    "convert_agent_summary_to_response",
]
