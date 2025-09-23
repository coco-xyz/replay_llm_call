"""Business logic for managing agents."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.core.logger import get_logger
from src.models import Agent
from src.stores.agent_store import AgentStore
from src.stores.regression_test_store import RegressionTestStore
from src.stores.test_case_store import TestCaseStore

logger = get_logger(__name__)


class AgentSummary(BaseModel):
    """Light-weight agent projection for embedding in other responses."""

    id: str = Field(..., description="Agent identifier")
    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")

    model_config = ConfigDict(from_attributes=True)


class AgentCreateData(BaseModel):
    """Input payload for creating an agent."""

    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    default_model_name: Optional[str] = Field(
        None, description="Default model name applied during regression"
    )
    default_system_prompt: Optional[str] = Field(
        None, description="Default system prompt applied during regression"
    )
    default_model_settings: Optional[dict] = Field(
        None, description="Default model settings JSON"
    )


class AgentUpdateData(BaseModel):
    """Input payload for updating an agent."""

    name: Optional[str] = Field(None, description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    default_model_name: Optional[str] = Field(None, description="Default model name")
    default_system_prompt: Optional[str] = Field(
        None, description="Default system prompt"
    )
    default_model_settings: Optional[dict] = Field(
        None, description="Default model settings JSON"
    )
    is_deleted: Optional[bool] = Field(
        None,
        description="Soft delete flag (managed via dedicated delete operations)",
    )


class AgentData(BaseModel):
    """Full agent representation."""

    id: str = Field(..., description="Agent identifier")
    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    default_model_name: Optional[str] = Field(
        None, description="Default model name applied during regression"
    )
    default_system_prompt: Optional[str] = Field(
        None, description="Default system prompt applied during regression"
    )
    default_model_settings: Optional[dict] = Field(
        None, description="Default model settings JSON"
    )
    is_deleted: bool = Field(False, description="Soft delete flag")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")

    model_config = ConfigDict(from_attributes=True)


class AgentService:
    """Service exposing agent-related operations."""

    def __init__(self) -> None:
        self.store = AgentStore()
        self.test_case_store = TestCaseStore()
        self.regression_test_store = RegressionTestStore()

    def create_agent(self, data: AgentCreateData) -> AgentData:
        """Create a new agent."""

        agent = Agent(
            id=str(uuid.uuid4()),
            name=data.name,
            description=data.description,
            default_model_name=data.default_model_name,
            default_system_prompt=data.default_system_prompt,
            default_model_settings=data.default_model_settings,
            is_deleted=False,
        )
        created = self.store.create(agent)
        return AgentData.model_validate(created)

    def get_agent(
        self, agent_id: str, include_deleted: bool = False
    ) -> Optional[AgentData]:
        agent = self.store.get_by_id(agent_id, include_deleted=include_deleted)
        if not agent:
            return None
        return AgentData.model_validate(agent)

    def list_agents(
        self,
        include_deleted: bool = False,
        *,
        limit: int = 20,
        offset: int = 0,
        search: Optional[str] = None,
    ) -> List[AgentData]:
        agents = self.store.list_agents(
            include_deleted=include_deleted,
            limit=limit,
            offset=offset,
            search=search,
        )
        return [AgentData.model_validate(agent) for agent in agents]

    def update_agent(self, agent_id: str, data: AgentUpdateData) -> Optional[AgentData]:
        agent = self.store.get_by_id(agent_id, include_deleted=True)
        if not agent:
            return None

        if data.is_deleted is not None:
            raise ValueError("Agent delete state cannot be modified via update")

        if data.name is not None:
            agent.name = data.name
        if data.description is not None:
            agent.description = data.description
        if data.default_model_name is not None:
            agent.default_model_name = data.default_model_name
        if data.default_system_prompt is not None:
            agent.default_system_prompt = data.default_system_prompt
        if data.default_model_settings is not None:
            agent.default_model_settings = data.default_model_settings

        updated = self.store.update(agent)
        return AgentData.model_validate(updated)

    def delete_agent(self, agent_id: str) -> bool:
        """Soft delete an agent and cascade to dependent records."""

        deleted = self.store.soft_delete(agent_id)
        if not deleted:
            return False
        self.test_case_store.soft_delete_by_agent(agent_id)
        self.regression_test_store.soft_delete_by_agent(agent_id)
        return True

    def get_agent_summary(self, agent_id: str) -> Optional[AgentSummary]:
        agent = self.store.get_by_id(agent_id, include_deleted=True)
        if not agent:
            return None
        return AgentSummary.model_validate(agent)

    def get_active_agent_or_raise(self, agent_id: str) -> Agent:
        agent = self.store.get_by_id(agent_id, include_deleted=True)
        if not agent or agent.is_deleted:
            raise ValueError(f"Agent not found or inactive: {agent_id}")
        return agent


__all__ = [
    "AgentService",
    "AgentCreateData",
    "AgentUpdateData",
    "AgentData",
    "AgentSummary",
]
