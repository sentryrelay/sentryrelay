"""
Tests for TOTP Authenticator Resource & Auto-Wait Fresh Window Protection
"""

import httpx
import pytest
import respx
from sentryrelay import SentryRelay


@respx.mock
def test_totp_crud_and_listing(live_api_key: str) -> None:
    base_url = "https://sentryrelay.com"

    # List
    respx.get(f"{base_url}/api/v1/identities/bot-1/totp").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "items": [
                        {
                            "id": "github_ops",
                            "workspaceId": "ws_123",
                            "identityId": "id_bot_1",
                            "issuer": "GitHub",
                            "accountLabel": "ops@acme.com",
                            "algorithm": "SHA1",
                            "digits": 6,
                            "period": 30,
                            "createdAt": "2026-10-25T12:00:00Z",
                            "updatedAt": "2026-10-25T12:00:00Z",
                        }
                    ]
                },
                "error": None,
            },
        )
    )

    # Create via URI
    respx.post(f"{base_url}/api/v1/identities/bot-1/totp").mock(
        return_value=httpx.Response(
            201,
            json={
                "data": {
                    "secret": {
                        "id": "aws_prod",
                        "workspaceId": "ws_123",
                        "identityId": "id_bot_1",
                        "issuer": "Amazon Web Services",
                        "accountLabel": "root",
                        "algorithm": "SHA1",
                        "digits": 6,
                        "period": 30,
                        "createdAt": "2026-10-25T12:00:00Z",
                        "updatedAt": "2026-10-25T12:00:00Z",
                    }
                },
                "error": None,
            },
        )
    )

    # Delete
    respx.delete(f"{base_url}/api/v1/identities/bot-1/totp/aws_prod").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {"deleted": True, "secretId": "aws_prod"},
                "error": None,
            },
        )
    )

    client = SentryRelay(api_key=live_api_key)

    secrets = client.totp.list("bot-1")
    assert len(secrets) == 1
    assert secrets[0].id == "github_ops"
    assert secrets[0].issuer == "GitHub"

    created = client.totp.create(
        "bot-1",
        otpauth_uri="otpauth://totp/Amazon%20Web%20Services:root?secret=JBSWY3DPEHPK3PXP&issuer=Amazon%20Web%20Services",
        id="aws_prod",
    )
    assert created.id == "aws_prod"
    assert created.issuer == "Amazon Web Services"

    deleted = client.totp.delete("bot-1", "aws_prod")
    assert deleted.deleted is True
    assert deleted.secret_id == "aws_prod"


@respx.mock
def test_totp_auto_wait_fresh_window_rollover(live_api_key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    base_url = "https://sentryrelay.com"

    sleep_calls: list[float] = []

    # First call returns remainingSeconds = 2 (< 4s)
    # Second call returns remainingSeconds = 30
    route = respx.get(f"{base_url}/api/v1/identities/bot-1/totp/github_ops")
    route.side_effect = [
        httpx.Response(
            200,
            json={
                "data": {
                    "code": "111111",
                    "remainingSeconds": 2,
                    "nextCode": "222222",
                    "period": 30,
                    "digits": 6,
                    "algorithm": "SHA1",
                },
                "error": None,
            },
        ),
        httpx.Response(
            200,
            json={
                "data": {
                    "code": "222222",
                    "remainingSeconds": 30,
                    "period": 30,
                    "digits": 6,
                    "algorithm": "SHA1",
                },
                "error": None,
            },
        ),
    ]

    client = SentryRelay(api_key=live_api_key)
    monkeypatch.setattr(client, "sleep", lambda s: sleep_calls.append(s))

    code_res = client.totp.get("bot-1", "github_ops", auto_wait_fresh_window=True)
    # Verify sleep was called with 2.2 seconds (2s * 1000 + 200ms = 2200ms -> 2.2s)
    assert len(sleep_calls) == 1
    assert abs(sleep_calls[0] - 2.2) < 0.01
    assert code_res.code == "222222"
    assert code_res.remaining_seconds == 30


@respx.mock
def test_totp_bypasses_auto_wait_when_disabled(live_api_key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    base_url = "https://sentryrelay.com"

    sleep_calls: list[float] = []

    respx.get(f"{base_url}/api/v1/identities/bot-1/totp/github_ops").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "code": "999888",
                    "remainingSeconds": 1,
                    "nextCode": "000111",
                    "period": 30,
                    "digits": 6,
                    "algorithm": "SHA1",
                },
                "error": None,
            },
        )
    )

    client = SentryRelay(api_key=live_api_key)
    monkeypatch.setattr(client, "sleep", lambda s: sleep_calls.append(s))

    code_res = client.totp.get("bot-1", "github_ops", auto_wait_fresh_window=False)
    assert len(sleep_calls) == 0
    assert code_res.code == "999888"
    assert code_res.remaining_seconds == 1
