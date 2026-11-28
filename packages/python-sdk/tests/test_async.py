"""
Tests for AsyncSentryRelay Client & Asynchronous Resources
"""

import httpx
import pytest
import respx
from sentryrelay import AsyncSentryRelay, NotFoundError


@pytest.mark.asyncio
@respx.mock
async def test_async_identities_and_wait(live_api_key: str) -> None:
    base_url = "https://sentryrelay.com"

    respx.get(f"{base_url}/api/v1/identities?limit=5").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "items": [
                        {
                            "id": "id_async_bot",
                            "name": "Async Bot",
                            "slug": "async-bot",
                            "emailHandle": "async-bot",
                            "emailDomain": "in.sentryrelay.com",
                            "emailAddress": "async-bot@in.sentryrelay.com",
                        }
                    ]
                }
            },
        )
    )

    respx.get(f"{base_url}/api/v1/identities/async-bot/wait?consume=true&sender=github.com&timeout=30").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "matched": True,
                    "timedOut": False,
                    "event": {
                        "id": "evt_async_123",
                        "identityId": "id_async_bot",
                        "channel": "email",
                        "classification": "otp",
                        "otpCode": "777888",
                        "magicLink": None,
                        "sender": "noreply@github.com",
                        "receivedAtMs": 1729894690000,
                        "receivedAtIso": "2026-10-25T22:18:10.000Z",
                    },
                    "waitDurationMs": 42,
                }
            },
        )
    )

    async with AsyncSentryRelay(api_key=live_api_key) as client:
        identities = await client.identities.list(limit=5)
        assert len(identities.items) == 1
        assert identities.items[0].slug == "async-bot"

        # Test async client top-level wait alias
        wait_res = await client.wait("async-bot", sender="github.com")
        assert wait_res.matched is True
        assert wait_res.otp_code == "777888"
        assert wait_res.code == "777888"


@pytest.mark.asyncio
@respx.mock
async def test_async_totp_auto_wait(live_api_key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    base_url = "https://sentryrelay.com"
    sleep_calls: list[float] = []

    route = respx.get(f"{base_url}/api/v1/identities/async-bot/totp/secret_1")
    route.side_effect = [
        httpx.Response(
            200,
            json={
                "data": {
                    "code": "111111",
                    "remainingSeconds": 2,
                    "period": 30,
                    "digits": 6,
                    "algorithm": "SHA1",
                }
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
                }
            },
        ),
    ]

    async with AsyncSentryRelay(api_key=live_api_key) as client:
        async def mock_async_sleep(s: float) -> None:
            sleep_calls.append(s)

        monkeypatch.setattr(client, "sleep", mock_async_sleep)

        totp = await client.totp.get("async-bot", "secret_1", auto_wait_fresh_window=True)
        assert len(sleep_calls) == 1
        assert totp.code == "222222"
        assert totp.remaining_seconds == 30


@pytest.mark.asyncio
@respx.mock
async def test_async_error_handling(live_api_key: str) -> None:
    base_url = "https://sentryrelay.com"

    respx.get(f"{base_url}/api/v1/identities/missing").mock(
        return_value=httpx.Response(
            404,
            json={"error": {"code": "NOT_FOUND", "message": "Missing identity"}},
        )
    )

    async with AsyncSentryRelay(api_key=live_api_key) as client:
        with pytest.raises(NotFoundError):
            await client.identities.get("missing")
