import pytest

from src.services.test_execution_service import ExecutionService


@pytest.mark.parametrize(
    "vector_a, vector_b, expected",
    [
        ([1.0, 0.0], [1.0, 0.0], 1.0),
        ([1.0, 0.0], [0.0, 1.0], 0.0),
        ([1.0, 1.0], [1.0, -1.0], 0.0),
    ],
)
def test_compute_similarity(vector_a, vector_b, expected):
    score = ExecutionService._compute_similarity(vector_a, vector_b)
    assert pytest.approx(expected, abs=1e-6) == score
