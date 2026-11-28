"""
Tests for Client Initialization, API Key Validation & Environment Handling
"""

import os
import pytest
from sentryrelay import AuthenticationError, SentryRelay, SentryRelayApiError
from sentryrelay.constants import DEFAULT_BASE_URL


def test_client_initialization_with_valid_key(live_api_key: str) -> None:
    client = SentryRelay(api_key=live_api_key, base_url="https://sentryrelay.com/")
    assert client.api_key == live_api_key
    assert client.base_url == "https://sentryrelay.com"

    headers = client.get_auth_headers()
    assert headers["Authorization"] == f"Bearer {live_api_key}"
    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "application/json"
    assert "sentryrelay-python" in headers["User-Agent"]


def test_client_initialization_with_test_key(test_api_key: str) -> None:
    client = SentryRelay(api_key=test_api_key)
    assert client.api_key == test_api_key
    assert client.base_url == DEFAULT_BASE_URL


def test_client_rejects_malformed_keys() -> None:
    for invalid_key in ["invalid_key", "sk_live_1234", "sr_live_short", "sr_prod_12345678901234567890123456789012"]:
        with pytest.raises(SentryRelayApiError) as exc_info:
            SentryRelay(api_key=invalid_key)
        assert exc_info.value.code == "INVALID_API_KEY"


def test_client_loads_key_from_environment(monkeypatch: pytest.MonkeyPatch, live_api_key: str) -> None:
    monkeypatch.setenv("SENTRY_RELAY_API_KEY", live_api_key)
    client = SentryRelay()
    assert client.api_key == live_api_key


def test_client_context_manager(live_api_key: str) -> None:
    with SentryRelay(api_key=live_api_key) as client:
        assert client.api_key == live_api_key
        assert not client._http_client.is_closed

    assert client._http_client.is_closed
