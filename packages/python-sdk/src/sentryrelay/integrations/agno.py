"""
Sentry Relay Agno Integration

Provides a Toolkit for Agno (`agno`) agents.
"""

from typing import Any, Callable, Dict, List, Optional, Union
from sentryrelay.client import AsyncSentryRelay, SentryRelay

try:
    from agno.tools import Toolkit  # type: ignore
except ImportError:
    class Toolkit:  # type: ignore
        """Fallback Toolkit base class when agno is not installed."""
        def __init__(self, name: str = "toolkit"):
            self.name = name
            self._tools: Dict[str, Callable[..., Any]] = {}

        def register(self, func: Callable[..., Any]) -> None:
            self._tools[func.__name__] = func

        @property
        def tools(self) -> List[Callable[..., Any]]:
            return list(self._tools.values())


class SentryRelayTools(Toolkit):
    """
    Agno Toolkit providing Sentry Relay 2FA, OTP, and TOTP authentication tools.

    Example:
    ```python
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    from sentryrelay import SentryRelay
    from sentryrelay.integrations.agno import SentryRelayTools

    relay = SentryRelay()
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        tools=[SentryRelayTools(relay)],
        instructions="Resolve 2FA verification challenges using Sentry Relay tools.",
    )
    ```
    """

    def __init__(self, relay: Union[SentryRelay, AsyncSentryRelay]) -> None:
        super().__init__(name="sentryrelay")
        self.relay = relay
        self.is_async = isinstance(relay, AsyncSentryRelay)

        self.register(self.wait_for_verification_code)
        self.register(self.get_totp_code)
        self.register(self.list_identities)

    def wait_for_verification_code(
        self,
        identity: str,
        sender: Optional[str] = None,
        channel: Optional[str] = None,
        timeout_seconds: int = 30,
    ) -> str:
        """Wait for an incoming 2FA verification code, OTP, or magic link for an Identity.

        Args:
            identity: The unique Identity ID or slug (e.g. 'checkout-bot' or 'id_01JAZ8...').
            sender: Optional sender domain or email filter (e.g. 'stripe.com').
            channel: Optional delivery channel filter: 'email' or 'sms'.
            timeout_seconds: Maximum seconds to wait (1 to 45, default: 30).

        Returns:
            Human-readable string containing the extracted OTP code, magic link, or timeout status.
        """
        if self.is_async:
            raise RuntimeError("Use a synchronous SentryRelay client with synchronous Agno agents.")

        client: SentryRelay = self.relay  # type: ignore
        res = client.wait(
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
        self,
        identity: str,
        secret_id: str,
    ) -> str:
        """Generate a live RFC 6238 TOTP authenticator code with auto-rollover protection.

        If <=4 seconds remain in the 30-second window, automatically waits out the rollover
        so the agent never inputs an expired code.

        Args:
            identity: The Identity ID or slug holding the vaulted secret.
            secret_id: The identifier of the vaulted TOTP secret (e.g. 'github_ops').

        Returns:
            String containing the 6-digit TOTP code and remaining valid seconds.
        """
        if self.is_async:
            raise RuntimeError("Use a synchronous SentryRelay client with synchronous Agno agents.")

        client: SentryRelay = self.relay  # type: ignore
        totp = client.totp.get(id_or_slug=identity, secret_id=secret_id)
        return f"TOTP Code: {totp.code} (valid for {totp.remaining_seconds}s)"

    def list_identities(self) -> str:
        """List all available Sentry Relay Identities and their assigned inbox addresses and phone numbers.

        Returns:
            Formatted string of identity slugs, email addresses, and phone numbers.
        """
        if self.is_async:
            raise RuntimeError("Use a synchronous SentryRelay client with synchronous Agno agents.")

        client: SentryRelay = self.relay  # type: ignore
        identities = client.identities.list()
        if not identities:
            return "No identities found."

        lines = ["Sentry Relay Identities:"]
        for idn in identities:
            lines.append(f"- {idn.slug} ({idn.id}): email={idn.email_address or 'none'}, phone={idn.phone_number or 'none'}")
        return "\n".join(lines)


def create_agno_tools(relay: Union[SentryRelay, AsyncSentryRelay]) -> SentryRelayTools:
    """
    Creates an Agno Toolkit instance configured with Sentry Relay tools.
    """
    return SentryRelayTools(relay)
