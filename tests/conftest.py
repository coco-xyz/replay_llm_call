import pytest

from src.core.config import settings


@pytest.fixture
def test_settings():
    return settings
