"""Agent management endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException, Query

from src.api.v1.converters import (
    convert_agent_create_request,
    convert_agent_data_to_response,
    convert_agent_update_request,
)
from src.api.v1.schemas.requests import AgentCreateRequest, AgentUpdateRequest
from src.api.v1.schemas.responses import AgentResponse
from src.core.logger import get_logger
from src.services.agent_service import AgentService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])
agent_service = AgentService()


@router.post("/", response_model=AgentResponse)
async def create_agent(request: AgentCreateRequest) -> AgentResponse:
    try:
        service_request = convert_agent_create_request(request)
        agent = agent_service.create_agent(service_request)
        return convert_agent_data_to_response(agent)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("API: Failed to create agent: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    include_deleted: bool = Query(False, description="Include soft-deleted agents"),
) -> List[AgentResponse]:
    try:
        agents = agent_service.list_agents(include_deleted=include_deleted)
        return [convert_agent_data_to_response(agent) for agent in agents]
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("API: Failed to list agents: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str) -> AgentResponse:
    agent = agent_service.get_agent(agent_id, include_deleted=True)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return convert_agent_data_to_response(agent)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: str, request: AgentUpdateRequest) -> AgentResponse:
    try:
        service_request = convert_agent_update_request(request)
        agent = agent_service.update_agent(agent_id, service_request)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return convert_agent_data_to_response(agent)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("API: Failed to update agent %s: %s", agent_id, exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str) -> dict:
    try:
        deleted = agent_service.delete_agent(agent_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Agent not found")
        return {"message": "Agent deleted successfully"}
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("API: Failed to delete agent %s: %s", agent_id, exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{agent_id}/restore", response_model=AgentResponse)
async def restore_agent(agent_id: str) -> AgentResponse:
    restored = agent_service.restore_agent(agent_id)
    if not restored:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent = agent_service.get_agent(agent_id, include_deleted=True)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return convert_agent_data_to_response(agent)


__all__ = ["router"]
