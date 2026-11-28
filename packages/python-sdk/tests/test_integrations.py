"""
Tests for Integrations (Playwright, Browser-Use, etc.)
"""

import pytest
from sentryrelay import SentryRelay, WaitResponse
from sentryrelay.integrations.browser_use import (
    create_browser_use_actions,
    register_sentryrelay_actions,
)
from sentryrelay.integrations.playwright import fill_otp_code
from sentryrelay.models import ExtractedAuthEvent


class MockSyncPage:
    def __init__(self) -> None:
        self.filled: list[tuple[str, str]] = []

    def fill(self, selector: str, value: str) -> None:
        self.filled.append((selector, value))


class MockAsyncPage:
    def __init__(self) -> None:
        self.filled: list[tuple[str, str]] = []

    async def fill(self, selector: str, value: str) -> None:
        self.filled.append((selector, value))


def test_fill_otp_code_sync() -> None:
    page = MockSyncPage()
    res = WaitResponse(
        matched=True,
        event=ExtractedAuthEvent(
            id="evt_1",
            identityId="id_1",
            channel="email",
            classification="otp",
            otpCode="492019",
            sender="auth@stripe.com",
            receivedAtMs=1000,
            receivedAtIso="2026-10-25T12:00:00Z",
        ),
    )

    fill_otp_code(page, 'input[name="code"]', res)
    assert page.filled == [('input[name="code"]', "492019")]


@pytest.mark.asyncio
async def test_fill_otp_code_async() -> None:
    page = MockAsyncPage()
    res = WaitResponse(
        matched=True,
        event=ExtractedAuthEvent(
            id="evt_2",
            identityId="id_2",
            channel="sms",
            classification="otp",
            otpCode="882194",
            sender="+18005550100",
            receivedAtMs=1000,
            receivedAtIso="2026-10-25T12:00:00Z",
        ),
    )

    await fill_otp_code(page, "#otp-input", res)
    assert page.filled == [("#otp-input", "882194")]


def test_fill_otp_code_raises_on_unmatched() -> None:
    page = MockSyncPage()
    res = WaitResponse(matched=False, timed_out=True)
    with pytest.raises(ValueError, match="did not contain an extracted OTP"):
        fill_otp_code(page, 'input[name="code"]', res)


def test_browser_use_action_registration(live_api_key: str) -> None:
    client = SentryRelay(api_key=live_api_key)
    actions = create_browser_use_actions(client)
    assert "wait_for_2fa_code" in actions
    assert "get_totp_token" in actions

    class MockController:
        def __init__(self) -> None:
            self.registered: dict = {}

        def action(self, name: str):
            def decorator(fn):
                self.registered[name] = fn
                return fn
            return decorator

    ctrl = MockController()
    register_sentryrelay_actions(ctrl, client)
    assert "wait_for_2fa_code" in ctrl.registered
    assert "get_totp_token" in ctrl.registered


def test_langgraph_tools_creation(live_api_key: str) -> None:
    from sentryrelay.integrations.langgraph import create_sentryrelay_tools

    client = SentryRelay(api_key=live_api_key)
    tools = create_sentryrelay_tools(client)
    assert len(tools) == 3
    tool_names = [t.name for t in tools]
    assert "wait_for_verification_code" in tool_names
    assert "get_totp_code" in tool_names
    assert "list_identities" in tool_names

