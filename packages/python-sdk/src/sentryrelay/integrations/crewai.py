"""
Sentry Relay CrewAI Integration Tools
"""

from typing import Any, Optional, Type
from pydantic import BaseModel, Field


class WaitToolSchema(BaseModel):
    identity: str = Field(description="The Identity ID or slug to wait on")
    sender: Optional[str] = Field(default=None, description="Optional sender domain filter (e.g. 'stripe.com')")
    channel: Optional[str] = Field(default=None, description="Channel filter: 'email' or 'sms'")
    timeout_seconds: int = Field(default=30, description="Max seconds to wait (1..45)")


class TotpToolSchema(BaseModel):
    identity: str = Field(description="The Identity ID or slug holding the secret")
    secret_id: str = Field(description="The secret ID of the vaulted TOTP token")


def create_crewai_tools(relay: Any) -> list:
    """
    Creates CrewAI BaseTool instances for 2FA wait and TOTP retrieval.
    Requires `crewai` (`pip install sentryrelay-sdk[crewai]`).
    """
    try:
        from crewai.tools import BaseTool
    except ImportError as exc:
        raise ImportError(
            "crewai is required to use CrewAI integration tools. "
            "Install it via: pip install crewai or pip install sentryrelay-sdk[crewai]"
        ) from exc

    class SentryRelayWaitTool(BaseTool):
        name: str = "wait_for_2fa_code"
        description: str = (
            "Wait for an inbound Email or SMS 2FA verification OTP code or magic link. "
            "Returns the extracted code or link once delivered."
        )
        args_schema: Type[BaseModel] = WaitToolSchema

        def _run(
            self,
            identity: str,
            sender: Optional[str] = None,
            channel: Optional[str] = None,
            timeout_seconds: int = 30,
        ) -> str:
            res = relay.wait(
                id_or_slug=identity,
                sender=sender,
                channel=channel,
                timeout=timeout_seconds,
            )
            if not res.matched:
                return f"Timed out waiting for 2FA code on identity '{identity}'"
            if res.otp_code:
                return f"OTP Code: {res.otp_code}"
            if res.magic_link:
                return f"Magic Link: {res.magic_link}"
            return "Event received with no code or link."

    class SentryRelayTotpTool(BaseTool):
        name: str = "get_totp_token"
        description: str = (
            "Retrieve an RFC 6238 TOTP authenticator 6-digit code. "
            "Automatically handles expiring windows so the code remains valid."
        )
        args_schema: Type[BaseModel] = TotpToolSchema

        def _run(self, identity: str, secret_id: str) -> str:
            totp = relay.totp.get(id_or_slug=identity, secret_id=secret_id)
            return f"TOTP Code: {totp.code} ({totp.remaining_seconds}s remaining)"

    return [SentryRelayWaitTool(), SentryRelayTotpTool()]
