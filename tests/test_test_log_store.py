from contextlib import contextmanager

import pytest

from src.models import TestLog
from src.stores import test_log_store
from src.stores.test_log_store import TestLogStore

TestLog.__test__ = False


class FakeQuery:
    def __init__(self, results=None):
        self.join_targets = []
        self.filters = []
        self.order_columns = []
        self.limit_value = None
        self.offset_value = None
        self.results = results or []
        self.all_called = False

    def join(self, target):
        self.join_targets.append(target)
        return self

    def filter(self, condition):
        self.filters.append(condition)
        return self

    def order_by(self, clause):
        self.order_columns.append(clause)
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def offset(self, value):
        self.offset_value = value
        return self

    def all(self):
        self.all_called = True
        return self.results


class FakeSession:
    def __init__(self, query):
        self._query = query

    def query(self, model):
        assert model is TestLog
        return self._query


def _patch_database_session(monkeypatch: pytest.MonkeyPatch, query: FakeQuery) -> None:
    @contextmanager
    def fake_database_session():
        yield FakeSession(query)

    monkeypatch.setattr(test_log_store, "database_session", fake_database_session)


def _has_filter(filters, column_name: str, table_name: str) -> bool:
    for condition in filters:
        left = getattr(condition, "left", None)
        table = getattr(left, "table", None)
        if (
            getattr(left, "key", None) == column_name
            and getattr(table, "name", None) == table_name
        ):
            return True
    return False


def test_get_all_excludes_soft_deleted_cases(monkeypatch: pytest.MonkeyPatch) -> None:
    store = TestLogStore()
    query = FakeQuery()
    _patch_database_session(monkeypatch, query)

    result = store.get_all(limit=25, offset=5)

    assert result == []
    assert query.all_called is True
    assert query.limit_value == 25
    assert query.offset_value == 5
    assert len(query.join_targets) == 1
    assert _has_filter(query.filters, "is_deleted", "test_cases")


def test_get_filtered_excludes_soft_deleted_cases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = TestLogStore()
    fake_results = [object()]
    query = FakeQuery(results=fake_results)
    _patch_database_session(monkeypatch, query)

    result = store.get_filtered(
        status="success", test_case_id="case-1", limit=10, offset=2
    )

    assert result == fake_results
    assert query.limit_value == 10
    assert query.offset_value == 2
    assert len(query.join_targets) == 1
    assert _has_filter(query.filters, "is_deleted", "test_cases")
    assert _has_filter(query.filters, "status", "test_logs")
    assert _has_filter(query.filters, "test_case_id", "test_logs")


def test_get_filtered_supports_agent_and_regression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = TestLogStore()
    query = FakeQuery(results=[object()])
    _patch_database_session(monkeypatch, query)

    result = store.get_filtered(agent_id="agent-7", regression_test_id="reg-2")

    assert result
    assert _has_filter(query.filters, "agent_id", "test_logs")
    assert _has_filter(query.filters, "regression_test_id", "test_logs")
