"""
Sentry Relay LangGraph / LangChain Integration Tools
"""

from typing import Any, List, Optional, Union
from sentryrelay.client import AsyncSentryRelay, SentryRelay


def create_sentryrelay_tools(relay: Union[SentryRelay, AsyncSentryRelay]) -> List[Any]:
    """
    Creates LangChain / LangGraph compatible tools for waiting on 2FA codes,
    retrieving TOTP tokens, and listing available identities.

    Requires `langchain-core` (`pip install sentryrelay-sdk[langchain]`).
    """
    try:
        from langchain_core.tools import tool
    except ImportError as exc:
        raise ImportError(
            "langchain-core is required to use LangGraph integration tools. "
            "Install it via: pip install langchain-core or pip install sentryrelay-sdk[langchain]"
        ) from exc

    is_async = isinstance(relay, AsyncSentryRelay)

    if is_async:
        @tool
        async def wait_for_verification_code(
            identity: str,
            sender: Optional[str] = None,
            channel: Optional[str] = None,
            timeout_seconds: int = 30,
        ) -> str:
            """Wait for an inbound Email or SMS 2FA verification code or magic link."""
            res = await relay.wait(
                id_or_slug=identity,
                sender=sender,
                channel=channel,  # type: ignore
                timeout=timeout_seconds,
            )
            if not res.matched:
                return f"Timed out waiting for verification code on identity '{identity}'"
            if res.otp_code:
                return f"OTP Code: {res.otp_code} (from {res.event.sender if res.event else 'unknown'})"
            if res.magic_link:
                return f"Magic Link: {res.magic_link}"
            return "Event received but no OTP or link extracted."

        @tool
        async def get_totp_code(
            identity: str,
            secret_id: str,
        ) -> str:
            """Generate a live RFC 6238 TOTP authenticator code with auto-rollover protection."""
            totp = await relay.totp.get(id_or_slug=identity, secret_id=secret_id)
            return f"TOTP Code: {totp.code} ({totp.remaining_seconds}s remaining in window)"

        @tool
        async def list_identities() -> str:
            """List available Sentry Relay Identities and their assigned email addresses."""
            res = await relay.identities.list()
            summary = [
                f"- {item.name} (id: {item.id}, email: {item.email_address}, sms: {item.sms_phone_number or 'none'})"
                for item in res.items
            ]
            return "\n".join(summary) if summary else "No identities found."

        return [wait_for_verification_code, get_totp_code, list_identities]
    else:
        @tool
        def wait_for_verification_code(
            identity: str,
            sender: Optional[str] = None,
            channel: Optional[str] = None,
            timeout_seconds: int = 30,
        ) -> str:
            """Wait for an inbound Email or SMS 2FA verification code or magic link."""
            res = relay.wait(
                id_or_slug=identity,
                sender=sender,
                channel=channel,  # type: ignore
                timeout=timeout_seconds,
            )
            if not res.matched:
                return f"Timed out waiting for verification code on identity '{identity}'"
            if res.otp_code:
                return f"OTP Code: {res.otp_code} (from {res.event.sender if res.event else 'unknown'})"
            if res.magic_link:
                return f"Magic Link: {res.magic_link}"
            return "Event received but no OTP or link extracted."

        @tool
        def get_totp_code(
            identity: str,
            secret_id: str,
        ) -> str:
            """Generate a live RFC 6238 TOTP authenticator code with auto-rollover protection."""
            totp = relay.totp.get(id_or_slug=identity, secret_id=secret_id)
            return f"TOTP Code: {totp.code} ({totp.remaining_seconds}s remaining in window)"

        @tool
        def list_identities() -> str:
            """List available Sentry Relay Identities and their assigned email addresses."""
            res = relay.identities.list()
            summary = [
                f"- {item.name} (id: {item.id}, email: {item.email_address}, sms: {item.sms_phone_number or 'none'})"
                for item in res.items
            ]
            return "\n".join(summary) if summary else "No identities found."

        return [wait_for_verification_code, get_totp_code, list_identities]


create_langchain_tools = create_sentryrelay_tools

