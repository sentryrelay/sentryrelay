"""
Pytest Fixtures and Helpers for Sentry Relay Python SDK Tests
"""

import pytest

VALID_LIVE_API_KEY = "sr_live_12345678901234567890123456789012"
VALID_TEST_API_KEY = "sr_test_abcdefghijklmnopqrstuvwxyz123456"


@pytest.fixture
def live_api_key() -> str:
    return VALID_LIVE_API_KEY


@pytest.fixture
def test_api_key() -> str:
    return VALID_TEST_API_KEY
