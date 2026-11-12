"""
Tests for Identities API Resource & Long-Polling Wait
"""

import httpx
import pytest
import respx
from sentryrelay import SentryRelay


@respx.mock
def test_identities_crud(live_api_key: str) -> None:
    base_url = "https://sentryrelay.com"

    # 1. list
    respx.get(f"{base_url}/api/v1/identities?limit=10").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "items": [
                        {
                            "id": "id_01JAZ8XYZ",
                            "name": "Checkout Bot",
                            "slug": "checkout-bot",
                            "status": "active",
                            "emailHandle": "checkout-bot",
                            "emailDomain": "in.sentryrelay.com",
                            "emailAddress": "checkout-bot@in.sentryrelay.com",
                            "createdAt": "2026-10-25T12:00:00Z",
                            "updatedAt": "2026-10-25T12:00:00Z",
                        }
                    ],
                    "nextCursor": None,
                },
                "error": None,
            },
        )
    )

    # 2. create
    respx.post(f"{base_url}/api/v1/identities").mock(
        return_value=httpx.Response(
            201,
            json={
                "data": {
                    "identity": {
                        "id": "id_01JAZ9NEW",
                        "name": "New Agent",
                        "slug": "new-agent",
                        "emailHandle": "new-agent",
                        "emailDomain": "in.sentryrelay.com",
                        "emailAddress": "new-agent@in.sentryrelay.com",
                        "createdAt": "2026-10-25T12:00:00Z",
                        "updatedAt": "2026-10-25T12:00:00Z",
                    }
                },
                "error": None,
            },
        )
    )

    # 3. get
    respx.get(f"{base_url}/api/v1/identities/id_01JAZ9NEW").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "identity": {
                        "id": "id_01JAZ9NEW",
                        "name": "New Agent",
                        "slug": "new-agent",
                        "emailHandle": "new-agent",
                        "emailDomain": "in.sentryrelay.com",
                        "emailAddress": "new-agent@in.sentryrelay.com",
                    }
                },
                "error": None,
            },
        )
    )

    # 4. update
    respx.patch(f"{base_url}/api/v1/identities/id_01JAZ9NEW").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "identity": {
                        "id": "id_01JAZ9NEW",
                        "name": "Updated Agent",
                        "slug": "new-agent",
                        "emailHandle": "new-agent",
                        "emailDomain": "in.sentryrelay.com",
                        "emailAddress": "new-agent@in.sentryrelay.com",
                    }
                },
                "error": None,
            },
        )
    )

    # 5. delete
    respx.delete(f"{base_url}/api/v1/identities/id_01JAZ9NEW").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {"deleted": True, "id": "id_01JAZ9NEW"},
                "error": None,
            },
        )
    )

    client = SentryRelay(api_key=live_api_key)

    # List
    list_res = client.identities.list(limit=10)
    assert len(list_res.items) == 1
    assert list_res.items[0].id == "id_01JAZ8XYZ"
    assert list_res.items[0].email_address == "checkout-bot@in.sentryrelay.com"

    # Create
    created = client.identities.create(name="New Agent", email_handle="new-agent")
    assert created.id == "id_01JAZ9NEW"
    assert created.name == "New Agent"

    # Get
    fetched = client.identities.get("id_01JAZ9NEW")
    assert fetched.name == "New Agent"

    # Update
    updated = client.identities.update("id_01JAZ9NEW", name="Updated Agent")
    assert updated.name == "Updated Agent"

    # Delete
    deleted = client.identities.delete("id_01JAZ9NEW")
    assert deleted.deleted is True
    assert deleted.id == "id_01JAZ9NEW"


@respx.mock
def test_wait_and_latest_queries(live_api_key: str) -> None:
    base_url = "https://sentryrelay.com"

    # Match on wait
    respx.get(f"{base_url}/api/v1/identities/checkout-bot/wait?channel=email&consume=true&sender=stripe.com&timeout=25").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "matched": True,
                    "timedOut": False,
                    "event": {
                        "id": "evt_01JAZ_EVENT",
                        "identityId": "id_01JAZ8XYZ",
                        "workspaceId": "ws_123",
                        "channel": "email",
                        "classification": "otp_and_link",
                        "otpCode": "582019",
                        "magicLink": "https://stripe.com/magic?token=xyz",
                        "sender": "auth@stripe.com",
                        "subject": "Your Stripe verification code",
                        "confidence": 0.99,
                        "receivedAtMs": 1729894684112,
                        "receivedAtIso": "2026-10-25T22:18:04.112Z",
                        "receivedAt": "2026-10-25T22:18:04.112Z",
                        "consumed": True,
                        "waitDurationMs": 85,
                    },
                    "waitDurationMs": 85,
                },
                "error": None,
            },
        )
    )

    # Non-blocking /latest query
    respx.get(f"{base_url}/api/v1/identities/checkout-bot/latest?channel=sms&consume=true&lookbackSeconds=60").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "matched": True,
                    "timedOut": False,
                    "event": {
                        "id": "evt_SMS_EVENT",
                        "identityId": "id_01JAZ8XYZ",
                        "channel": "sms",
                        "classification": "otp",
                        "otpCode": "123456",
                        "magicLink": None,
                        "sender": "+18005550199",
                        "confidence": 1.0,
                        "receivedAtMs": 1729894690000,
                        "receivedAtIso": "2026-10-25T22:18:10.000Z",
                        "consumed": True,
                        "waitDurationMs": 12,
                    },
                    "waitDurationMs": 12,
                },
                "error": None,
            },
        )
    )

    client = SentryRelay(api_key=live_api_key)

    # Test top-level alias client.wait
    wait_res = client.wait("checkout-bot", channel="email", sender="stripe.com", timeout=25)
    assert wait_res.matched is True
    assert wait_res.timed_out is False
    assert wait_res.otp_code == "582019"
    assert wait_res.code == "582019"
    assert wait_res.magic_link == "https://stripe.com/magic?token=xyz"
    assert wait_res.link == "https://stripe.com/magic?token=xyz"
    assert wait_res.wait_duration_ms == 85

    # Test top-level alias client.latest
    latest_res = client.latest("checkout-bot", channel="sms")
    assert latest_res.matched is True
    assert latest_res.otp_code == "123456"
    assert latest_res.code == "123456"
    assert latest_res.magic_link is None


@respx.mock
def test_sms_did_provision_and_release(live_api_key: str) -> None:
    base_url = "https://sentryrelay.com"

    respx.post(f"{base_url}/api/v1/identities/checkout-bot/sms/provision").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "identity": {
                        "id": "id_checkout",
                        "name": "Checkout Bot",
                        "smsPhoneNumber": "+12035550142",
                        "telnyxPhoneNumberId": "phone_123",
                    },
                    "phoneNumber": "+12035550142",
                    "telnyxPhoneNumberId": "phone_123",
                },
                "error": None,
            },
        )
    )

    respx.delete(f"{base_url}/api/v1/identities/checkout-bot/sms").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "released": True,
                    "phoneNumber": "+12035550142",
                    "identityId": "id_checkout",
                },
                "error": None,
            },
        )
    )

    client = SentryRelay(api_key=live_api_key)

    prov = client.identities.provision_sms_did("checkout-bot", area_code="203")
    assert prov.phone_number == "+12035550142"
    assert prov.telnyx_phone_number_id == "phone_123"

    rel = client.identities.release_sms_did("checkout-bot")
    assert rel.released is True
    assert rel.phone_number == "+12035550142"


@respx.mock
def test_wait_and_latest_with_include_non_auth(live_api_key: str) -> None:
    base_url = "https://sentryrelay.com"

    respx.get(
        f"{base_url}/api/v1/identities/checkout-bot/wait?channel=email&consume=true&includeNonAuth=true&timeout=30"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "matched": True,
                    "timedOut": False,
                    "event": {
                        "id": "evt_NON_AUTH_01",
                        "identityId": "id_01JAZ8XYZ",
                        "channel": "email",
                        "classification": "non_auth",
                        "otpCode": None,
                        "magicLink": None,
                        "sender": "forwarding-noreply@google.com",
                        "subject": "Gmail Forwarding Confirmation",
                        "textBody": "Confirmation code: 482910384",
                        "links": [
                            {
                                "url": "https://mail-settings.google.com/mail/vf-token",
                                "anchorText": "Confirm forwarding",
                            }
                        ],
                        "confidence": 0.0,
                        "receivedAtMs": 1729894695000,
                        "receivedAtIso": "2026-10-25T22:18:15.000Z",
                        "expiresAtMs": 1729894755000,
                        "consumed": True,
                    },
                    "waitDurationMs": 42,
                },
                "error": None,
            },
        )
    )

    client = SentryRelay(api_key=live_api_key)
    res = client.wait("checkout-bot", channel="email", include_non_auth=True, timeout=30)
    assert res.matched is True
    assert res.text_body == "Confirmation code: 482910384"
    assert len(res.links) == 1
    assert res.links[0].url == "https://mail-settings.google.com/mail/vf-token"
    assert res.links[0].anchor_text == "Confirm forwarding"
    assert res.event is not None
    assert res.event.expires_at_ms == 1729894755000
