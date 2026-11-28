"""
Sentry Relay Browser-Use Integration Helper

Enables autonomous Browser Use agents (https://browser-use.com) to seamlessly
wait for 2FA/OTP codes and TOTP authenticators inside browser actions.
"""

from typing import Any, Dict, Optional, Union
from sentryrelay.client import AsyncSentryRelay, SentryRelay


def create_browser_use_actions(relay: Union[SentryRelay, AsyncSentryRelay]) -> Dict[str, Any]:
    """
    Returns action functions suitable for registration on a Browser Use `Controller`.

    Example:
    ```python
    from browser_use import Controller
    from sentryrelay import AsyncSentryRelay
    from sentryrelay.integrations.browser_use import register_sentryrelay_actions

    controller = Controller()
    relay = AsyncSentryRelay()
    register_sentryrelay_actions(controller, relay)
    ```
    """
    is_async = isinstance(relay, AsyncSentryRelay)

    if is_async:
        async def wait_for_2fa_code(
            identity: str,
            channel: Optional[str] = None,
            sender: Optional[str] = None,
            timeout_seconds: int = 30,
        ) -> Dict[str, Any]:
            """Wait for an Email or SMS verification OTP code or magic link."""
            res = await relay.wait(
                id_or_slug=identity,
                channel=channel,  # type: ignore
                sender=sender,
                timeout=timeout_seconds,
            )
            return {
                "matched": res.matched,
                "timed_out": res.timed_out,
                "otp_code": res.otp_code,
                "magic_link": res.magic_link,
            }

        async def get_totp_token(
            identity: str,
            secret_id: str,
        ) -> Dict[str, Any]:
            """Retrieve an RFC 6238 TOTP authenticator code with auto-rollover protection."""
            totp = await relay.totp.get(id_or_slug=identity, secret_id=secret_id)
            return {
                "code": totp.code,
                "remaining_seconds": totp.remaining_seconds,
            }

        return {
            "wait_for_2fa_code": wait_for_2fa_code,
            "get_totp_token": get_totp_token,
        }

    else:
        def wait_for_2fa_code(
            identity: str,
            channel: Optional[str] = None,
            sender: Optional[str] = None,
            timeout_seconds: int = 30,
        ) -> Dict[str, Any]:
            """Wait for an Email or SMS verification OTP code or magic link."""
            res = relay.wait(
                id_or_slug=identity,
                channel=channel,  # type: ignore
                sender=sender,
                timeout=timeout_seconds,
            )
            return {
                "matched": res.matched,
                "timed_out": res.timed_out,
                "otp_code": res.otp_code,
                "magic_link": res.magic_link,
            }

        def get_totp_token(
            identity: str,
            secret_id: str,
        ) -> Dict[str, Any]:
            """Retrieve an RFC 6238 TOTP authenticator code with auto-rollover protection."""
            totp = relay.totp.get(id_or_slug=identity, secret_id=secret_id)
            return {
                "code": totp.code,
                "remaining_seconds": totp.remaining_seconds,
            }

        return {
            "wait_for_2fa_code": wait_for_2fa_code,
            "get_totp_token": get_totp_token,
        }


def register_sentryrelay_actions(
    controller: Any,
    relay: Union[SentryRelay, AsyncSentryRelay],
) -> None:
    """
    Registers `wait_for_2fa_code` and `get_totp_token` actions onto a `browser_use.Controller`.
    """
    actions = create_browser_use_actions(relay)

    if hasattr(controller, "action"):
        for name, fn in actions.items():
            controller.action(name)(fn)
    elif hasattr(controller, "registry") and hasattr(controller.registry, "register_action"):
        for name, fn in actions.items():
            controller.registry.register_action(name, fn)
    else:
        # Fallback: attach directly
        for name, fn in actions.items():
            setattr(controller, name, fn)
