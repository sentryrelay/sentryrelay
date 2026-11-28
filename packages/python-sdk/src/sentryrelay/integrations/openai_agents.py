"""
Sentry Relay OpenAI Agents SDK Integration

Provides tools for the OpenAI Agents SDK (`openai-agents` / `agents` package).
"""

from typing import Any, Callable, Dict, List, Optional, Union
from sentryrelay.client import AsyncSentryRelay, SentryRelay


def create_openai_agents_tools(relay: Union[SentryRelay, AsyncSentryRelay]) -> List[Any]:
    """
    Creates function tools for the OpenAI Agents SDK (`openai-agents`).

    If the `agents` package is installed, tools are decorated with `@function_tool`.
    Otherwise, standard typed functions are returned.

    Example:
    ```python
    from agents import Agent, Runner
    from sentryrelay import AsyncSentryRelay
    from sentryrelay.integrations.openai_agents import create_openai_agents_tools

    relay = AsyncSentryRelay()
    tools = create_openai_agents_tools(relay)

    agent = Agent(
        name="LoginAgent",
        instructions="Handle authentication challenges using Sentry Relay.",
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
            """Wait for an inbound Email or SMS 2FA verification OTP code or magic link.

            Args:
                identity: The unique Identity ID or slug (e.g. 'checkout-bot').
                sender: Optional sender domain filter (e.g. 'stripe.com').
                channel: Delivery channel filter ('email' or 'sms').
                timeout_seconds: Maximum seconds to hold connection (1..45, default: 30).

            Returns:
                Extracted OTP code, magic link, or timeout status.
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
                return f"OTP Code: {res.otp_code}"
            if res.magic_link:
                return f"Magic Link: {res.magic_link}"
            return "Event received without OTP or magic link."

        async def get_totp_code(
            identity: str,
            secret_id: str,
        ) -> str:
            """Generate a live RFC 6238 TOTP authenticator code with auto-rollover protection.

            Args:
                identity: The Identity ID or slug holding the vaulted secret.
                secret_id: The identifier of the vaulted TOTP secret (e.g. 'github_ops').

            Returns:
                Generated 6-digit TOTP code and remaining seconds in window.
            """
            totp = await relay.totp.get(id_or_slug=identity, secret_id=secret_id)
            return f"TOTP Code: {totp.code} ({totp.remaining_seconds}s remaining in 30s window)"

        async def list_identities() -> str:
            """List available Sentry Relay Identities and their assigned email addresses and SMS numbers."""
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
            """Wait for an inbound Email or SMS 2FA verification OTP code or magic link.

            Args:
                identity: The unique Identity ID or slug (e.g. 'checkout-bot').
                sender: Optional sender domain filter (e.g. 'stripe.com').
                channel: Delivery channel filter ('email' or 'sms').
                timeout_seconds: Maximum seconds to hold connection (1..45, default: 30).

            Returns:
                Extracted OTP code, magic link, or timeout status.
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
                return f"OTP Code: {res.otp_code}"
            if res.magic_link:
                return f"Magic Link: {res.magic_link}"
            return "Event received without OTP or magic link."

        def get_totp_code(
            identity: str,
            secret_id: str,
        ) -> str:
            """Generate a live RFC 6238 TOTP authenticator code with auto-rollover protection.

            Args:
                identity: The Identity ID or slug holding the vaulted secret.
                secret_id: The identifier of the vaulted TOTP secret (e.g. 'github_ops').

            Returns:
                Generated 6-digit TOTP code and remaining seconds in window.
            """
            totp = relay.totp.get(id_or_slug=identity, secret_id=secret_id)
            return f"TOTP Code: {totp.code} ({totp.remaining_seconds}s remaining in 30s window)"

        def list_identities() -> str:
            """List available Sentry Relay Identities and their assigned email addresses and SMS numbers."""
            res = relay.identities.list()
            lines = [
                f"- {i.name} (id: {i.id}, email: {i.email_address}, sms: {i.sms_phone_number or 'none'})"
                for i in res.items
            ]
            return "\n".join(lines) if lines else "No identities found."

        raw_tools = [wait_for_verification_code, get_totp_code, list_identities]

    try:
        from agents import function_tool  # type: ignore
        return [function_tool(fn) for fn in raw_tools]
    except ImportError:
        return raw_tools
