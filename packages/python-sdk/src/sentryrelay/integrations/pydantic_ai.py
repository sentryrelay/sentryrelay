"""
Sentry Relay PydanticAI Integration

Provides native tool registration for PydanticAI (`pydantic-ai`) agents.
"""

from typing import Any, Callable, Dict, List, Optional, Union
from sentryrelay.client import AsyncSentryRelay, SentryRelay


def create_pydantic_ai_tools(relay: Union[SentryRelay, AsyncSentryRelay]) -> List[Callable[..., Any]]:
    """
    Creates standalone plain tool functions suitable for PydanticAI agents.
    """
    is_async = isinstance(relay, AsyncSentryRelay)

    if is_async:
        async def wait_for_verification_code(
            identity: str,
            sender: Optional[str] = None,
            channel: Optional[str] = None,
            timeout_seconds: int = 30,
        ) -> Dict[str, Any]:
            """Wait for an incoming Email or SMS 2FA verification code or magic login link.

            Args:
                identity: The unique Identity ID or slug (e.g. 'checkout-bot').
                sender: Optional sender domain filter (e.g. 'stripe.com').
                channel: Optional channel: 'email' or 'sms'.
                timeout_seconds: Max seconds to hold the connection (1..45, default: 30).

            Returns:
                Dictionary with matched, timed_out, otp_code, magic_link, sender, and channel.
            """
            res = await relay.wait(
                id_or_slug=identity,
                sender=sender,
                channel=channel,  # type: ignore
                timeout=timeout_seconds,
            )
            return {
                "matched": res.matched,
                "timed_out": res.timed_out,
                "otp_code": res.otp_code,
                "magic_link": res.magic_link,
                "sender": res.event.sender if res.event else None,
                "channel": res.event.channel if res.event else None,
            }

        async def get_totp_code(
            identity: str,
            secret_id: str,
        ) -> Dict[str, Any]:
            """Generate a live RFC 6238 TOTP authenticator code with auto-rollover protection.

            Args:
                identity: The Identity ID or slug holding the vaulted secret.
                secret_id: The identifier of the vaulted TOTP secret (e.g. 'github_ops').

            Returns:
                Dictionary containing code, remaining_seconds, and period.
            """
            totp = await relay.totp.get(id_or_slug=identity, secret_id=secret_id)
            return {
                "code": totp.code,
                "remaining_seconds": totp.remaining_seconds,
                "period": totp.period,
            }

        async def list_identities() -> List[Dict[str, Any]]:
            """List all available Sentry Relay Identities and their assigned credentials.

            Returns:
                List of identities with id, name, slug, email_address, and sms_phone_number.
            """
            identities = await relay.identities.list()
            return [
                {
                    "id": item.id,
                    "name": item.name,
                    "slug": item.slug,
                    "email_address": item.email_address,
                    "sms_phone_number": item.sms_phone_number,
                }
                for item in identities.items
            ]

        return [wait_for_verification_code, get_totp_code, list_identities]

    else:
        def wait_for_verification_code(
            identity: str,
            sender: Optional[str] = None,
            channel: Optional[str] = None,
            timeout_seconds: int = 30,
        ) -> Dict[str, Any]:
            """Wait for an incoming Email or SMS 2FA verification code or magic login link.

            Args:
                identity: The unique Identity ID or slug (e.g. 'checkout-bot').
                sender: Optional sender domain filter (e.g. 'stripe.com').
                channel: Optional channel: 'email' or 'sms'.
                timeout_seconds: Max seconds to hold the connection (1..45, default: 30).

            Returns:
                Dictionary with matched, timed_out, otp_code, magic_link, sender, and channel.
            """
            res = relay.wait(
                id_or_slug=identity,
                sender=sender,
                channel=channel,  # type: ignore
                timeout=timeout_seconds,
            )
            return {
                "matched": res.matched,
                "timed_out": res.timed_out,
                "otp_code": res.otp_code,
                "magic_link": res.magic_link,
                "sender": res.event.sender if res.event else None,
                "channel": res.event.channel if res.event else None,
            }

        def get_totp_code(
            identity: str,
            secret_id: str,
        ) -> Dict[str, Any]:
            """Generate a live RFC 6238 TOTP authenticator code with auto-rollover protection.

            Args:
                identity: The Identity ID or slug holding the vaulted secret.
                secret_id: The identifier of the vaulted TOTP secret (e.g. 'github_ops').

            Returns:
                Dictionary containing code, remaining_seconds, and period.
            """
            totp = relay.totp.get(id_or_slug=identity, secret_id=secret_id)
            return {
                "code": totp.code,
                "remaining_seconds": totp.remaining_seconds,
                "period": totp.period,
            }

        def list_identities() -> List[Dict[str, Any]]:
            """List all available Sentry Relay Identities and their assigned credentials.

            Returns:
                List of identities with id, name, slug, email_address, and sms_phone_number.
            """
            identities = relay.identities.list()
            return [
                {
                    "id": item.id,
                    "name": item.name,
                    "slug": item.slug,
                    "email_address": item.email_address,
                    "sms_phone_number": item.sms_phone_number,
                }
                for item in identities.items
            ]

        return [wait_for_verification_code, get_totp_code, list_identities]


def register_sentryrelay_tools(agent: Any, relay: Union[SentryRelay, AsyncSentryRelay]) -> None:
    """
    Registers Sentry Relay tools directly onto a `pydantic_ai.Agent` instance using `tool_plain`.

    Example:
    ```python
    from pydantic_ai import Agent
    from sentryrelay import AsyncSentryRelay
    from sentryrelay.integrations.pydantic_ai import register_sentryrelay_tools

    agent = Agent('openai:gpt-4o', system_prompt="Automate portal login challenges.")
    relay = AsyncSentryRelay()
    register_sentryrelay_tools(agent, relay)
    ```
    """
    tools = create_pydantic_ai_tools(relay)

    if hasattr(agent, "tool_plain"):
        for tool_fn in tools:
            agent.tool_plain(tool_fn)
    elif hasattr(agent, "tool"):
        for tool_fn in tools:
            agent.tool(tool_fn)
    else:
        raise AttributeError(f"Provided agent object {type(agent)} does not support tool_plain or tool registration.")
