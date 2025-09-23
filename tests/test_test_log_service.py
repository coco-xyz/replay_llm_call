from datetime import datetime
from typing import Optional

from src.services.test_log_service import LogData, LogService


class FakeTestLog:
    def __init__(self):
        self.id = "log-1"
        self.test_case_id = "case-123"
        self.agent_id = "agent-456"
        self.regression_test_id = "reg-789"
        self.model_name = "gpt-4"
        self.model_settings = {"temperature": 0.1}
        self.system_prompt = "system"
        self.user_message = "user"
        self.tools: Optional[list] = None
        self.llm_response = "hello"
        self.response_example = "expected"
        self.response_example_vector = [0.1, 0.2]
        self.response_expectation_snapshot = "Must mention pricing and delivery time."
        self.response_time_ms = 42
        self.llm_response_vector = [0.3, 0.4]
        self.similarity_score = 0.95
        self.is_passed = True
        self.evaluation_feedback = "Response covered pricing and delivery expectations."
        self.evaluation_model_name = "openai/gpt-4o-mini"
        self.evaluation_metadata = {"satisfied_criteria": ["pricing", "delivery"]}
        self.status = "success"
        self.error_message = None
        self.created_at = datetime(2024, 1, 1, 12, 0, 0)


class FakeStore:
    def __init__(self, log):
        self.log = log

    def get_by_id(self, log_id: str):  # pragma: no cover - simple passthrough
        assert log_id == self.log.id
        return self.log


def test_get_test_log_includes_response_example():
    service = LogService()
    fake_log = FakeTestLog()
    service.store = FakeStore(fake_log)

    result = service.get_test_log(fake_log.id)

    assert isinstance(result, LogData)
    assert result.response_example == fake_log.response_example
    assert result.response_example_vector == fake_log.response_example_vector
    assert (
        result.response_expectation_snapshot == fake_log.response_expectation_snapshot
    )
    assert result.similarity_score == fake_log.similarity_score
    assert result.is_passed == fake_log.is_passed
    assert result.evaluation_feedback == fake_log.evaluation_feedback
    assert result.evaluation_model_name == fake_log.evaluation_model_name
    assert result.evaluation_metadata == fake_log.evaluation_metadata
