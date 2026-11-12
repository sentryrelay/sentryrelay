"""
Sentry Relay Google ADK (Agent Development Kit) Integration

Provides ready-to-use tools for Google ADK (`google-adk`) agents using Gemini
and Vertex AI models.
"""

import inspect
from typing import Any, Callable, Dict, List, Optional, Union
from sentryrelay.client import AsyncSentryRelay, SentryRelay


def create_google_adk_tools(relay: Union[SentryRelay, AsyncSentryRelay]) -> List[Callable[..., Any]]:
    """
    Creates tool functions for Google Agent Development Kit (`google-adk`) agents.

    Example:
    ```python
    from google.adk.agents.llm_agent import Agent
    from sentryrelay import SentryRelay
    from sentryrelay.integrations.google_adk import create_google_adk_tools

    relay = SentryRelay()
    adk_tools = create_google_adk_tools(relay)

    agent = Agent(
        model="gemini-2.5-flash",
        name="auth_verifier",
        instruction="Use Sentry Relay tools to wait for 2FA verification codes.",
        tools=adk_tools,
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
        ) -> Dict[str, Any]:
            """Wait for an incoming 2FA verification code, OTP, or magic link for an Identity.

            Blocks up to timeout_seconds until a matching verification event arrives in <200ms.

            Args:
                identity: The unique Identity ID or slug (e.g. 'checkout-bot' or 'id_01JAZ8...').
                sender: Optional sender email or SMS domain filter (e.g. 'stripe.com').
                channel: Optional delivery channel filter: 'email' or 'sms'.
                timeout_seconds: Maximum seconds to wait (1 to 45, default: 30).

            Returns:
                Dictionary with matched (bool), timed_out (bool), otp_code (str or None),
                magic_link (str or None), sender (str), and wait_duration_ms (int).
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
                "wait_duration_ms": res.wait_duration_ms,
            }

        async def get_totp_code(
            identity: str,
            secret_id: str,
        ) -> Dict[str, Any]:
            """Generate a live RFC 6238 TOTP authenticator code with auto-rollover protection.

            If <=4 seconds remain in the 30-second window, automatically waits out the rollover
            so the agent never inputs an expired code.

            Args:
                identity: The Identity ID or slug holding the vaulted secret.
                secret_id: The identifier of the vaulted TOTP secret (e.g. 'github_ops').

            Returns:
                Dictionary containing code (6-digit string), remaining_seconds (int), and period (int).
            """
            totp = await relay.totp.get(id_or_slug=identity, secret_id=secret_id)
            return {
                "code": totp.code,
                "remaining_seconds": totp.remaining_seconds,
                "period": totp.period,
                "digits": totp.digits,
            }

        async def list_identities() -> List[Dict[str, Any]]:
            """List all available Sentry Relay Identities and their assigned email addresses and phone numbers.

            Returns:
                List of identity summaries with id, name, slug, email_address, and sms_phone_number.
            """
            identities = await relay.identities.list()
            return [
                {
                    "id": item.id,
                    "name": item.name,
                    "slug": item.slug,
                    "email_address": item.email_address,
                    "sms_phone_number": item.sms_phone_number,
                    "status": item.status,
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
            """Wait for an incoming 2FA verification code, OTP, or magic link for an Identity.

            Blocks up to timeout_seconds until a matching verification event arrives in <200ms.

            Args:
                identity: The unique Identity ID or slug (e.g. 'checkout-bot' or 'id_01JAZ8...').
                sender: Optional sender email or SMS domain filter (e.g. 'stripe.com').
                channel: Optional delivery channel filter: 'email' or 'sms'.
                timeout_seconds: Maximum seconds to wait (1 to 45, default: 30).

            Returns:
                Dictionary with matched (bool), timed_out (bool), otp_code (str or None),
                magic_link (str or None), sender (str), and wait_duration_ms (int).
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
                "wait_duration_ms": res.wait_duration_ms,
            }

        def get_totp_code(
            identity: str,
            secret_id: str,
        ) -> Dict[str, Any]:
            """Generate a live RFC 6238 TOTP authenticator code with auto-rollover protection.

            If <=4 seconds remain in the 30-second window, automatically waits out the rollover
            so the agent never inputs an expired code.

            Args:
                identity: The Identity ID or slug holding the vaulted secret.
                secret_id: The identifier of the vaulted TOTP secret (e.g. 'github_ops').

            Returns:
                Dictionary containing code (6-digit string), remaining_seconds (int), and period (int).
            """
            totp = relay.totp.get(id_or_slug=identity, secret_id=secret_id)
            return {
                "code": totp.code,
                "remaining_seconds": totp.remaining_seconds,
                "period": totp.period,
                "digits": totp.digits,
            }

        def list_identities() -> List[Dict[str, Any]]:
            """List all available Sentry Relay Identities and their assigned email addresses and phone numbers.

            Returns:
                List of identity summaries with id, name, slug, email_address, and sms_phone_number.
            """
            identities = relay.identities.list()
            return [
                {
                    "id": item.id,
                    "name": item.name,
                    "slug": item.slug,
                    "email_address": item.email_address,
                    "sms_phone_number": item.sms_phone_number,
                    "status": item.status,
                }
                for item in identities.items
            ]

        return [wait_for_verification_code, get_totp_code, list_identities]
