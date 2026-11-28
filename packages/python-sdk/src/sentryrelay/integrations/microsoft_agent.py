"""
Sentry Relay Microsoft Agent Framework Integration

Provides tools for the Microsoft Agent Framework (`agent-framework`),
Azure AI Foundry Projects (`azure-ai-projects`), and Semantic Kernel agents.
"""

from typing import Any, Callable, Dict, List, Optional, Union
from sentryrelay.client import AsyncSentryRelay, SentryRelay


def create_microsoft_agent_tools(relay: Union[SentryRelay, AsyncSentryRelay]) -> List[Any]:
    """
    Creates tools compatible with Microsoft Agent Framework (`agent-framework`)
    and Azure AI Foundry Agents (`azure-ai-projects`).

    If `agent_framework` is installed, tools are wrapped using `AIFunction`.
    Otherwise, standard typed callables with docstrings are returned.

    Example:
    ```python
    from agent_framework import ChatAgent
    from sentryrelay import SentryRelay
    from sentryrelay.integrations.microsoft_agent import create_microsoft_agent_tools

    relay = SentryRelay()
    tools = create_microsoft_agent_tools(relay)

    agent = ChatAgent(
        name="SecurityAssistant",
        instructions="Help with automated sign-ins and 2FA verification.",
        tools=tools,
    )
    ```
    """
    is_async = isinstance(relay, AsyncSentryRelay)

    if is_async:
        async def wait_for_verification_code(
            identity: str,
            sender: Optional[str] = None,
            channel: Optional[str] = None,
            timeout_seconds: int = 30,
        ) -> str:
            """Wait for an inbound Email or SMS 2FA verification code or magic login link.

            Args:
                identity: The Identity ID or slug (e.g. 'checkout-bot').
                sender: Optional sender domain filter (e.g. 'stripe.com').
                channel: Delivery channel filter ('email' or 'sms').
                timeout_seconds: Maximum seconds to hold connection (1..45, default: 30).

            Returns:
                String describing the extracted OTP code, magic link, or timeout status.
            """
            res = await relay.wait(
                id_or_slug=identity,
                sender=sender,
                channel=channel,  # type: ignore
                timeout=timeout_seconds,
            )
            if not res.matched:
                return f"Timed out waiting for verification code on identity '{identity}'."
            if res.otp_code:
                return f"OTP Code: {res.otp_code} (channel: {res.event.channel if res.event else 'unknown'}, sender: {res.event.sender if res.event else 'unknown'})"
            if res.magic_link:
                return f"Magic Link: {res.magic_link}"
            return "Auth event received without OTP or magic link."

        async def get_totp_code(
            identity: str,
            secret_id: str,
        ) -> str:
            """Generate a live RFC 6238 TOTP authenticator code with auto-rollover protection.

            Args:
                identity: The Identity ID or slug holding the secret.
                secret_id: The vaulted secret ID (e.g. 'github_ops').

            Returns:
                String with current TOTP code and remaining seconds in cycle.
            """
            totp = await relay.totp.get(id_or_slug=identity, secret_id=secret_id)
            return f"TOTP Code: {totp.code} ({totp.remaining_seconds}s remaining in window)"

        async def list_identities() -> str:
            """List available Sentry Relay Identities and their assigned email and phone numbers."""
            res = await relay.identities.list()
            lines = [
                f"- {i.name} (id: {i.id}, email: {i.email_address}, sms: {i.sms_phone_number or 'none'})"
                for i in res.items
            ]
            return "\n".join(lines) if lines else "No identities found."

        raw_tools = [wait_for_verification_code, get_totp_code, list_identities]

    else:
        def wait_for_verification_code(
            identity: str,
            sender: Optional[str] = None,
            channel: Optional[str] = None,
            timeout_seconds: int = 30,
        ) -> str:
            """Wait for an inbound Email or SMS 2FA verification code or magic login link.

            Args:
                identity: The Identity ID or slug (e.g. 'checkout-bot').
                sender: Optional sender domain filter (e.g. 'stripe.com').
                channel: Delivery channel filter ('email' or 'sms').
                timeout_seconds: Maximum seconds to hold connection (1..45, default: 30).

            Returns:
                String describing the extracted OTP code, magic link, or timeout status.
            """
            res = relay.wait(
                id_or_slug=identity,
                sender=sender,
                channel=channel,  # type: ignore
                timeout=timeout_seconds,
            )
            if not res.matched:
                return f"Timed out waiting for verification code on identity '{identity}'."
            if res.otp_code:
                return f"OTP Code: {res.otp_code} (channel: {res.event.channel if res.event else 'unknown'}, sender: {res.event.sender if res.event else 'unknown'})"
            if res.magic_link:
                return f"Magic Link: {res.magic_link}"
            return "Auth event received without OTP or magic link."

        def get_totp_code(
            identity: str,
            secret_id: str,
        ) -> str:
            """Generate a live RFC 6238 TOTP authenticator code with auto-rollover protection.

            Args:
                identity: The Identity ID or slug holding the secret.
                secret_id: The vaulted secret ID (e.g. 'github_ops').

            Returns:
                String with current TOTP code and remaining seconds in cycle.
            """
            totp = relay.totp.get(id_or_slug=identity, secret_id=secret_id)
            return f"TOTP Code: {totp.code} ({totp.remaining_seconds}s remaining in window)"

        def list_identities() -> str:
            """List available Sentry Relay Identities and their assigned email and phone numbers."""
            res = relay.identities.list()
            lines = [
                f"- {i.name} (id: {i.id}, email: {i.email_address}, sms: {i.sms_phone_number or 'none'})"
                for i in res.items
            ]
            return "\n".join(lines) if lines else "No identities found."

        raw_tools = [wait_for_verification_code, get_totp_code, list_identities]

    # If Microsoft agent-framework AIFunction is available, wrap the tools
    try:
        from agent_framework import AIFunction  # type: ignore
        return [AIFunction(fn) for fn in raw_tools]
    except ImportError:
        return raw_tools
