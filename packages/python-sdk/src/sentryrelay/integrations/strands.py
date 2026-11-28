"""
Sentry Relay Strands Agents Integration

Provides tool functions for Strands Agents (`strands-agents` / `strands`).
"""

from typing import Any, Callable, Dict, List, Optional, Union
from sentryrelay.client import AsyncSentryRelay, SentryRelay

# Optional strands @tool decorator
try:
    from strands import tool as _strands_tool  # type: ignore
except ImportError:
    try:
        from strands_agents import tool as _strands_tool  # type: ignore
    except ImportError:
        _strands_tool = None


def create_strands_tools(relay: Union[SentryRelay, AsyncSentryRelay]) -> List[Callable[..., Any]]:
    """
    Creates tool functions for Strands Agents (`strands` / `strands-agents`).

    If the `strands` package is installed, tools are decorated with `@tool`.
    Otherwise, typed callables with detailed docstrings are returned.

    Example:
    ```python
    from strands import Agent
    from sentryrelay import SentryRelay
    from sentryrelay.integrations.strands import create_strands_tools

    relay = SentryRelay()
    tools = create_strands_tools(relay)

    agent = Agent(
        model="claude-3-7-sonnet-20250219",
        name="auth_assistant",
        system_prompt="Resolve 2FA challenges using Sentry Relay tools.",
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
            """Wait for an incoming 2FA verification code, OTP, or magic link for an Identity.

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
                return f"OTP Code: {res.otp_code} (sender: {res.event.sender if res.event else 'unknown'})"
            if res.magic_link:
                return f"Magic Link: {res.magic_link} (sender: {res.event.sender if res.event else 'unknown'})"
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
            return f"TOTP Code: {totp.code} (remaining: {totp.remaining_seconds}s)"

        async def list_identities() -> List[Dict[str, Any]]:
            """List all available Sentry Relay Identities and their assigned inbox addresses and phone numbers."""
            identities = await relay.identities.list()
            return [
                {
                    "id": idn.id,
                    "slug": idn.slug,
                    "name": idn.name,
                    "email": idn.email_address,
                    "phone": idn.phone_number,
                }
                for idn in identities
            ]

    else:
        def wait_for_verification_code(
            identity: str,
            sender: Optional[str] = None,
            channel: Optional[str] = None,
            timeout_seconds: int = 30,
        ) -> str:
            """Wait for an incoming 2FA verification code, OTP, or magic link for an Identity.

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
                return f"OTP Code: {res.otp_code} (sender: {res.event.sender if res.event else 'unknown'})"
            if res.magic_link:
                return f"Magic Link: {res.magic_link} (sender: {res.event.sender if res.event else 'unknown'})"
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
            return f"TOTP Code: {totp.code} (remaining: {totp.remaining_seconds}s)"

        def list_identities() -> List[Dict[str, Any]]:
            """List all available Sentry Relay Identities and their assigned inbox addresses and phone numbers."""
            identities = relay.identities.list()
            return [
                {
                    "id": idn.id,
                    "slug": idn.slug,
                    "name": idn.name,
                    "email": idn.email_address,
                    "phone": idn.phone_number,
                }
                for idn in identities
            ]

    raw_tools = [wait_for_verification_code, get_totp_code, list_identities]

    if _strands_tool is not None:
        return [_strands_tool(fn) for fn in raw_tools]

    return raw_tools
