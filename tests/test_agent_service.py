from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src.services.agent_service import AgentService, AgentUpdateData


def test_delete_agent_soft_deletes_cases(monkeypatch):
    service = AgentService()

    monkeypatch.setattr(service.store, "soft_delete", lambda agent_id: True)

    captured = {}

    def fake_soft_delete_by_agent(agent_id: str) -> int:
        captured["agent_id"] = agent_id
        return 2

    monkeypatch.setattr(
        service.test_case_store, "soft_delete_by_agent", fake_soft_delete_by_agent
    )

    assert service.delete_agent("agent-123") is True
    assert captured["agent_id"] == "agent-123"


def test_ensure_default_agent_creates_when_missing(monkeypatch):
    service = AgentService()

    monkeypatch.setattr(service.store, "get_by_id", lambda *_args, **_kwargs: None)

    created = {}

    def fake_create(agent):
        created["agent"] = agent
        return agent

    monkeypatch.setattr(service.store, "create", fake_create)

    default_agent = service.ensure_default_agent_exists()
    assert default_agent.id == service.DEFAULT_AGENT_ID
    assert created["agent"].name == "Default Agent"


def test_get_agent_summary_handles_missing(monkeypatch):
    service = AgentService()
    monkeypatch.setattr(service.store, "get_by_id", lambda *_args, **_kwargs: None)
    assert service.get_agent_summary("missing") is None


def test_update_agent_rejects_is_deleted_toggle(monkeypatch):
    service = AgentService()

    agent = SimpleNamespace(
        id="agent-123",
        name="Agent 123",
        description=None,
        default_model_name=None,
        default_system_prompt=None,
        default_model_settings=None,
        is_deleted=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    monkeypatch.setattr(service.store, "get_by_id", lambda *_args, **_kwargs: agent)

    def fail_update(_obj):  # pragma: no cover - defensive guard
        raise AssertionError("should not persist when deletion toggle is rejected")

    monkeypatch.setattr(service.store, "update", fail_update)

    with pytest.raises(ValueError):
        service.update_agent("agent-123", AgentUpdateData(is_deleted=True))
