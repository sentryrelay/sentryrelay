"""
Sentry Relay Smolagents Integration

Provides Tool subclasses for Hugging Face's Smolagents (`smolagents`).
"""

from typing import Any, Dict, List, Optional, Union
from sentryrelay.client import AsyncSentryRelay, SentryRelay

try:
    from smolagents import Tool  # type: ignore
except ImportError:
    class Tool:  # type: ignore
        """Fallback Tool base class when smolagents is not installed."""
        name: str = ""
        description: str = ""
        inputs: Dict[str, Any] = {}
        output_type: str = "string"

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def forward(self, *args: Any, **kwargs: Any) -> Any:
            raise NotImplementedError

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            return self.forward(*args, **kwargs)


class SentryRelayWaitTool(Tool):
    """
    Smolagents Tool for waiting on inbound 2FA verification codes, OTPs, or magic links.
    """
    name = "wait_for_verification_code"
    description = (
        "Wait for an incoming 2FA verification code, OTP, or magic link for a Sentry Relay Identity. "
        "Blocks until a matching verification event arrives within the timeout."
    )
    inputs = {
        "identity": {
            "type": "string",
            "description": "The unique Identity ID or slug (e.g. 'checkout-bot').",
        },
        "sender": {
            "type": "string",
            "description": "Optional sender domain or email filter (e.g. 'stripe.com').",
            "nullable": True,
        },
        "channel": {
            "type": "string",
            "description": "Optional delivery channel filter: 'email' or 'sms'.",
            "nullable": True,
        },
        "timeout_seconds": {
            "type": "integer",
            "description": "Maximum seconds to hold connection (1..45, default: 30).",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, relay: Union[SentryRelay, AsyncSentryRelay], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.relay = relay

    def forward(
        self,
        identity: str,
        sender: Optional[str] = None,
        channel: Optional[str] = None,
        timeout_seconds: Optional[int] = 30,
    ) -> str:
        timeout = timeout_seconds or 30
        if isinstance(self.relay, AsyncSentryRelay):
            raise RuntimeError("Use a synchronous SentryRelay client with smolagents.")

        client: SentryRelay = self.relay  # type: ignore
        res = client.wait(
            id_or_slug=identity,
            sender=sender,
            channel=channel,  # type: ignore
            timeout=timeout,
        )
        if not res.matched:
            return f"Timed out waiting for verification code on identity '{identity}'."
        if res.otp_code:
            return f"OTP Code: {res.otp_code} (sender: {res.event.sender if res.event else 'unknown'})"
        if res.magic_link:
            return f"Magic Link: {res.magic_link} (sender: {res.event.sender if res.event else 'unknown'})"
        return "Event received without OTP or magic link."


class SentryRelayTotpTool(Tool):
    """
    Smolagents Tool for generating RFC 6238 TOTP authenticator codes with auto-rollover protection.
    """
    name = "get_totp_code"
    description = (
        "Generate a live RFC 6238 TOTP authenticator code with auto-rollover protection. "
        "If <=4 seconds remain in the 30-second window, automatically waits out rollover."
    )
    inputs = {
        "identity": {
            "type": "string",
            "description": "The Identity ID or slug holding the vaulted secret.",
        },
        "secret_id": {
            "type": "string",
            "description": "The identifier of the vaulted TOTP secret (e.g. 'github_ops').",
        },
    }
    output_type = "string"

    def __init__(self, relay: Union[SentryRelay, AsyncSentryRelay], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.relay = relay

    def forward(
        self,
        identity: str,
        secret_id: str,
    ) -> str:
        if isinstance(self.relay, AsyncSentryRelay):
            raise RuntimeError("Use a synchronous SentryRelay client with smolagents.")

        client: SentryRelay = self.relay  # type: ignore
        totp = client.totp.get(id_or_slug=identity, secret_id=secret_id)
        return f"TOTP Code: {totp.code} (valid for {totp.remaining_seconds}s)"


class SentryRelayIdentitiesTool(Tool):
    """
    Smolagents Tool for listing all available Sentry Relay Identities.
    """
    name = "list_identities"
    description = "List all available Sentry Relay Identities and their assigned inbox addresses and phone numbers."
    inputs = {}
    output_type = "string"

    def __init__(self, relay: Union[SentryRelay, AsyncSentryRelay], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.relay = relay

    def forward(self) -> str:
        if isinstance(self.relay, AsyncSentryRelay):
            raise RuntimeError("Use a synchronous SentryRelay client with smolagents.")

        client: SentryRelay = self.relay  # type: ignore
        identities = client.identities.list()
        if not identities:
            return "No identities found."

        lines = ["Sentry Relay Identities:"]
        for idn in identities:
            lines.append(f"- {idn.slug} ({idn.id}): email={idn.email_address or 'none'}, phone={idn.phone_number or 'none'}")
        return "\n".join(lines)


def create_smolagents_tools(relay: Union[SentryRelay, AsyncSentryRelay]) -> List[Tool]:
    """
    Creates Smolagents Tool instances for Sentry Relay (wait, totp, identities).

    Example:
    ```python
    from smolagents import CodeAgent, HfApiModel
    from sentryrelay import SentryRelay
    from sentryrelay.integrations.smolagents import create_smolagents_tools

    relay = SentryRelay()
    tools = create_smolagents_tools(relay)

    agent = CodeAgent(
        tools=tools,
        model=HfApiModel(),
    )
    ```
    """
    return [
        SentryRelayWaitTool(relay),
        SentryRelayTotpTool(relay),
        SentryRelayIdentitiesTool(relay),
    ]
