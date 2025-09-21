"""Agent data access layer."""

from typing import List, Optional

from src.core.error_codes import DatabaseErrorCode
from src.core.exceptions import DatabaseException
from src.core.logger import get_logger
from src.models import Agent
from src.stores.database import database_session

logger = get_logger(__name__)


class AgentStore:
    """Store class encapsulating CRUD operations for agents."""

    def create(self, agent: Agent) -> Agent:
        try:
            with database_session() as db:
                db.add(agent)
                db.commit()
                db.refresh(agent)
                logger.info("Created agent %s", agent.id)
                return agent
        except Exception as exc:  # pragma: no cover - wrapped for consistency
            logger.error("Failed to create agent: %s", exc)
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to create agent: {exc}",
            ) from exc

    def get_by_id(
        self, agent_id: str, include_deleted: bool = False
    ) -> Optional[Agent]:
        try:
            with database_session() as db:
                query = db.query(Agent).filter(Agent.id == agent_id)
                if not include_deleted:
                    query = query.filter(Agent.is_deleted.is_(False))
                return query.first()
        except Exception as exc:  # pragma: no cover - consistent handling
            logger.error("Failed to fetch agent %s: %s", agent_id, exc)
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to fetch agent: {exc}",
            ) from exc

    def get_by_name(self, name: str, include_deleted: bool = False) -> Optional[Agent]:
        try:
            with database_session() as db:
                query = db.query(Agent).filter(Agent.name == name)
                if not include_deleted:
                    query = query.filter(Agent.is_deleted.is_(False))
                return query.first()
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to fetch agent by name %s: %s", name, exc)
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to fetch agent: {exc}",
            ) from exc

    def list_agents(self, include_deleted: bool = False) -> List[Agent]:
        try:
            with database_session() as db:
                query = db.query(Agent)
                if not include_deleted:
                    query = query.filter(Agent.is_deleted.is_(False))
                return query.order_by(Agent.created_at.desc()).all()
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to list agents: %s", exc)
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to list agents: {exc}",
            ) from exc

    def update(self, agent: Agent) -> Agent:
        try:
            with database_session() as db:
                merged = db.merge(agent)
                db.commit()
                db.refresh(merged)
                logger.info("Updated agent %s", merged.id)
                return merged
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to update agent %s: %s", agent.id, exc)
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to update agent: {exc}",
            ) from exc

    def soft_delete(self, agent_id: str) -> bool:
        try:
            with database_session() as db:
                agent = db.query(Agent).filter(Agent.id == agent_id).first()
                if not agent:
                    return False
                if agent.is_deleted:
                    return True
                agent.is_deleted = True
                db.commit()
                logger.info("Soft deleted agent %s", agent_id)
                return True
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to soft delete agent %s: %s", agent_id, exc)
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to delete agent: {exc}",
            ) from exc

    def restore(self, agent_id: str) -> bool:
        try:
            with database_session() as db:
                agent = db.query(Agent).filter(Agent.id == agent_id).first()
                if not agent:
                    return False
                if not agent.is_deleted:
                    return True
                agent.is_deleted = False
                db.commit()
                logger.info("Restored agent %s", agent_id)
                return True
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to restore agent %s: %s", agent_id, exc)
            raise DatabaseException(
                DatabaseErrorCode.QUERY_FAILED,
                f"Failed to restore agent: {exc}",
            ) from exc


__all__ = ["AgentStore"]
