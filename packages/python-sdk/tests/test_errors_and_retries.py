"""
Tests for Retries, Exponential Backoff & Typed Exception Hierarchy
"""

import httpx
import pytest
import respx
from sentryrelay import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PaymentRequiredError,
    PermissionDeniedError,
    QuotaExceededError,
    RateLimitError,
    SentryRelay,
    SentryRelayApiError,
    ValidationError,
)


@respx.mock
def test_retries_transient_5xx_on_get(live_api_key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    base_url = "https://sentryrelay.com"

    sleep_calls: list[float] = []
    route = respx.get(f"{base_url}/api/v1/identities")
    route.side_effect = [
        httpx.Response(500, json={"error": {"code": "INTERNAL_ERROR", "message": "Flaky error"}}),
        httpx.Response(
            200,
            json={"data": {"items": [{"id": "id_1", "name": "Bot 1"}]}},
        ),
    ]

    client = SentryRelay(api_key=live_api_key, retry_delay_seconds=0.01)
    monkeypatch.setattr(client, "sleep", lambda s: sleep_calls.append(s))

    res = client.identities.list()
    assert len(res.items) == 1
    assert len(sleep_calls) == 1
    assert route.call_count == 2


@respx.mock
def test_does_not_retry_4xx_client_errors(live_api_key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    base_url = "https://sentryrelay.com"

    sleep_calls: list[float] = []
    route = respx.get(f"{base_url}/api/v1/identities/missing-bot")
    route.return_value = httpx.Response(
        404,
        json={"error": {"code": "IDENTITY_NOT_FOUND", "message": "Identity not found"}},
    )

    client = SentryRelay(api_key=live_api_key)
    monkeypatch.setattr(client, "sleep", lambda s: sleep_calls.append(s))

    with pytest.raises(NotFoundError) as exc_info:
        client.identities.get("missing-bot")

    assert exc_info.value.code == "IDENTITY_NOT_FOUND"
    assert exc_info.value.status_code == 404
    assert route.call_count == 1
    assert len(sleep_calls) == 0


@respx.mock
def test_typed_exceptions_mapping(live_api_key: str) -> None:
    base_url = "https://sentryrelay.com"
    client = SentryRelay(api_key=live_api_key)

    test_cases = [
        (401, "UNAUTHORIZED", AuthenticationError),
        (402, "WORKSPACE_GRACE_SUSPENDED", PaymentRequiredError),
        (403, "INSUFFICIENT_SCOPE", PermissionDeniedError),
        (404, "NOT_FOUND", NotFoundError),
        (409, "EMAIL_HANDLE_TAKEN", ConflictError),
        (422, "VALIDATION_ERROR", ValidationError),
        (429, "RATE_LIMIT_EXCEEDED", RateLimitError),
        (429, "MONTHLY_QUOTA_EXCEEDED", QuotaExceededError),
    ]

    for status, code, expected_cls in test_cases:
        respx.get(f"{base_url}/api/v1/test-{code}").mock(
            return_value=httpx.Response(status, json={"error": {"code": code, "message": f"Test {code}"}})
        )
        with pytest.raises(expected_cls) as exc_info:
            client.request("GET", f"/api/v1/test-{code}", skip_retry=True)
        assert exc_info.value.code == code
        assert exc_info.value.status_code == status


@respx.mock
def test_mutating_requests_do_not_retry_5xx(live_api_key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    base_url = "https://sentryrelay.com"
    sleep_calls: list[float] = []

    route = respx.post(f"{base_url}/api/v1/identities")
    route.return_value = httpx.Response(500, json={"error": {"code": "INTERNAL_ERROR", "message": "Server error"}})

    client = SentryRelay(api_key=live_api_key)
    monkeypatch.setattr(client, "sleep", lambda s: sleep_calls.append(s))

    with pytest.raises(SentryRelayApiError):
        client.identities.create(name="Bot")

    # Should NOT have retried because POST is mutating
    assert route.call_count == 1
    assert len(sleep_calls) == 0
