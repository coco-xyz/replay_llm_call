from datetime import datetime, timezone
from types import SimpleNamespace

from src.services.test_case_service import TestCaseService, TestCaseUpdateData

TestCaseService.__test__ = False
TestCaseUpdateData.__test__ = False


def _build_test_case(**overrides):
    base = {
        "id": "case-1",
        "agent_id": "agent-1",
        "agent": None,
        "name": "Sample",
        "description": "desc",
        "raw_data": {"messages": []},
        "middle_messages": [],
        "tools": None,
        "model_name": "gpt",
        "model_settings": {"temperature": 0.2},
        "system_prompt": "system",
        "last_user_message": "user",
        "response_example": None,
        "response_expectation": None,
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_get_test_case_includes_soft_delete_flag(monkeypatch):
    service = TestCaseService()
    deleted_case = _build_test_case(is_deleted=True)
    call_args = {}

    def _fake_get_by_id(case_id, include_deleted=False):
        call_args["case_id"] = case_id
        call_args["include_deleted"] = include_deleted
        return deleted_case

    monkeypatch.setattr(service.store, "get_by_id", _fake_get_by_id)
    monkeypatch.setattr(
        service.agent_service,
        "get_agent_summary",
        lambda _agent_id: None,
    )

    result = service.get_test_case("case-1")

    assert result is not None
    assert result.is_deleted is True
    assert call_args == {"case_id": "case-1", "include_deleted": True}


def test_get_test_case_includes_response_expectation(monkeypatch):
    service = TestCaseService()
    expected = "Must mention pricing and delivery time."
    test_case = _build_test_case(response_expectation=expected)

    monkeypatch.setattr(
        service.store,
        "get_by_id",
        lambda _case_id, include_deleted=True: test_case,
    )
    monkeypatch.setattr(
        service.agent_service,
        "get_agent_summary",
        lambda _agent_id: None,
    )

    result = service.get_test_case("case-1")

    assert result is not None
    assert result.response_expectation == expected


def test_update_test_case_blocks_deleted_records(monkeypatch):
    service = TestCaseService()
    deleted_case = _build_test_case(is_deleted=True)

    monkeypatch.setattr(
        service.store,
        "get_by_id",
        lambda _case_id, include_deleted=False: deleted_case,
    )

    update_called = {"value": False}

    def _fake_update(test_case):
        update_called["value"] = True
        return test_case

    monkeypatch.setattr(service.store, "update", _fake_update)

    result = service.update_test_case("case-1", TestCaseUpdateData(name="Updated"))

    assert result is None
    assert update_called["value"] is False
