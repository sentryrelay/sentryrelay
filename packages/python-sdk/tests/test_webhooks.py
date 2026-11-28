"""
Tests for Webhooks and Audit Logs Resources
"""

import httpx
import pytest
import respx
from sentryrelay import SentryRelay


@respx.mock
def test_webhooks_crud(live_api_key: str) -> None:
    base_url = "https://sentryrelay.com"

    respx.get(f"{base_url}/api/v1/webhooks").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "items": [
                        {
                            "id": "wh_01JAZ_HOOK",
                            "targetUrl": "https://example.com/webhook",
                            "events": ["otp.extracted"],
                            "enabled": True,
                        }
                    ]
                },
                "error": None,
            },
        )
    )

    respx.post(f"{base_url}/api/v1/webhooks").mock(
        return_value=httpx.Response(
            201,
            json={
                "data": {
                    "webhook": {
                        "id": "wh_01JAZ_NEW",
                        "targetUrl": "https://example.com/alerts",
                        "events": ["sms.fallback_triggered"],
                        "enabled": True,
                    }
                },
                "error": None,
            },
        )
    )

    respx.delete(f"{base_url}/api/v1/webhooks/wh_01JAZ_NEW").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {"deleted": True, "id": "wh_01JAZ_NEW"},
                "error": None,
            },
        )
    )

    client = SentryRelay(api_key=live_api_key)

    webhooks = client.webhooks.list()
    assert len(webhooks) == 1
    assert webhooks[0].id == "wh_01JAZ_HOOK"
    assert webhooks[0].target_url == "https://example.com/webhook"

    created = client.webhooks.create(
        target_url="https://example.com/alerts",
        events=["sms.fallback_triggered"],
    )
    assert created.id == "wh_01JAZ_NEW"

    deleted = client.webhooks.delete("wh_01JAZ_NEW")
    assert deleted.deleted is True
    assert deleted.id == "wh_01JAZ_NEW"


@respx.mock
def test_audit_logs_query(live_api_key: str) -> None:
    base_url = "https://sentryrelay.com"

    respx.get(f"{base_url}/api/v1/audit-logs").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "items": [
                        {
                            "id": "log_1",
                            "workspaceId": "ws_123",
                            "identityId": "id_123",
                            "eventType": "email.otp_extracted",
                            "actor": {"type": "api_key", "id": "sr_live_123"},
                            "metadata": {"senderMasked": "***@github.com", "latencyMs": 110},
                            "createdAt": "2026-10-25T12:00:00Z",
                        }
                    ]
                },
                "error": None,
            },
        )
    )

    client = SentryRelay(api_key=live_api_key)
    logs = client.audit_logs.list(identity_id="id_123")
    assert len(logs) == 1
    assert logs[0].id == "log_1"
    assert logs[0].event_type == "email.otp_extracted"
