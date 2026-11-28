"""
Sentry Relay Claude Agent SDK & Anthropic Tool Use Integration

Provides tools for the Claude Agent SDK (`claude-agent-sdk`) and Anthropic Claude
tool-use workflows with Sonnet, Haiku, and Opus models.
"""

from typing import Any, Callable, Dict, Iterator, List, Optional, Union
from sentryrelay.client import AsyncSentryRelay, SentryRelay

CLAUDE_TOOL_DEFINITIONS = [
    {
        "name": "wait_for_verification_code",
        "description": (
            "Wait for an incoming 2FA verification code, OTP, or magic link for a Sentry Relay Identity. "
            "Blocks up to timeout_seconds until a matching verification event arrives in <200ms."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "identity": {
                    "type": "string",
                    "description": "The unique Identity ID or slug (e.g. 'checkout-bot' or 'id_01JAZ8...').",
                },
                "sender": {
                    "type": "string",
                    "description": "Optional sender domain or email filter (e.g. 'stripe.com' or 'auth@okta.com').",
                },
                "channel": {
                    "type": "string",
                    "enum": ["email", "sms"],
                    "description": "Optional delivery channel filter: 'email' or 'sms'.",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Maximum seconds to hold connection (1..45, default: 30).",
                    "default": 30,
                },
            },
            "required": ["identity"],
        },
    },
    {
        "name": "get_totp_code",
        "description": (
            "Generate a live RFC 6238 TOTP authenticator code with auto-rollover protection. "
            "If <=4 seconds remain in the 30-second window, automatically waits out the rollover "
            "so the agent never inputs an expired code."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "identity": {
                    "type": "string",
                    "description": "The Identity ID or slug holding the vaulted secret.",
                },
                "secret_id": {
                    "type": "string",
                    "description": "The identifier of the vaulted TOTP secret (e.g. 'github_ops').",
                },
            },
            "required": ["identity", "secret_id"],
        },
    },
    {
        "name": "list_identities",
        "description": (
            "List all available Sentry Relay Identities and their assigned email addresses and phone numbers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


class ClaudeSentryRelayTools:
    """
    Tool manager for Anthropic Claude and the Claude Agent SDK (`claude-agent-sdk`).

    Provides tool schema definitions adhering to Anthropic's tool specifications,
    plus a direct execution dispatcher.

    Example with Anthropic SDK:
    ```python
    import anthropic
    from sentryrelay import SentryRelay
    from sentryrelay.integrations.claude_agent import ClaudeSentryRelayTools

    relay = SentryRelay()
    tools = ClaudeSentryRelayTools(relay)
    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=1024,
        tools=tools.definitions,
        messages=[{"role": "user", "content": "Sign in with identity checkout-bot and get the OTP."}],
    )

    for block in response.content:
        if block.type == "tool_use":
            tool_result = tools.execute(block.name, block.input)
    ```
    """

    def __init__(self, relay: Union[SentryRelay, AsyncSentryRelay]) -> None:
        self.relay = relay
        self.is_async = isinstance(relay, AsyncSentryRelay)
        self.definitions = [dict(d) for d in CLAUDE_TOOL_DEFINITIONS]

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        return iter(self.definitions)

    def __len__(self) -> int:
        return len(self.definitions)

    def execute(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a tool by name with arguments.

        If the underlying relay client is `AsyncSentryRelay`, this returns a coroutine.
        """
        args = arguments or {}
        name = tool_name.replace("sentryrelay_", "")

        if self.is_async:
            return self._async_execute(name, args)
        return self._sync_execute(name, args)

    def _sync_execute(self, name: str, args: Dict[str, Any]) -> Any:
        client: SentryRelay = self.relay  # type: ignore

        if name == "wait_for_verification_code":
            res = client.wait(
                id_or_slug=args["identity"],
                sender=args.get("sender"),
                channel=args.get("channel"),
                timeout=args.get("timeout_seconds", 30),
            )
            if not res.matched:
                return f"Timed out waiting for verification code on identity '{args['identity']}'."
            if res.otp_code:
                return f"OTP Code: {res.otp_code} (sender: {res.event.sender if res.event else 'unknown'})"
            if res.magic_link:
                return f"Magic Link: {res.magic_link} (sender: {res.event.sender if res.event else 'unknown'})"
            return "Event received without OTP code or magic link."

        elif name == "get_totp_code":
            totp = client.totp.get(id_or_slug=args["identity"], secret_id=args["secret_id"])
            return f"TOTP Code: {totp.code} (remaining: {totp.remaining_seconds}s)"

        elif name == "list_identities":
            identities = client.identities.list()
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

        raise ValueError(f"Unknown tool name: {name}")

    async def _async_execute(self, name: str, args: Dict[str, Any]) -> Any:
        client: AsyncSentryRelay = self.relay  # type: ignore

        if name == "wait_for_verification_code":
            res = await client.wait(
                id_or_slug=args["identity"],
                sender=args.get("sender"),
                channel=args.get("channel"),
                timeout=args.get("timeout_seconds", 30),
            )
            if not res.matched:
                return f"Timed out waiting for verification code on identity '{args['identity']}'."
            if res.otp_code:
                return f"OTP Code: {res.otp_code} (sender: {res.event.sender if res.event else 'unknown'})"
            if res.magic_link:
                return f"Magic Link: {res.magic_link} (sender: {res.event.sender if res.event else 'unknown'})"
            return "Event received without OTP code or magic link."

        elif name == "get_totp_code":
            totp = await client.totp.get(id_or_slug=args["identity"], secret_id=args["secret_id"])
            return f"TOTP Code: {totp.code} (remaining: {totp.remaining_seconds}s)"

        elif name == "list_identities":
            identities = await client.identities.list()
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

        raise ValueError(f"Unknown tool name: {name}")


def create_claude_agent_tools(relay: Union[SentryRelay, AsyncSentryRelay]) -> ClaudeSentryRelayTools:
    """
    Creates Claude / Anthropic tool manager with tool specifications and dispatcher.

    Returns:
        ClaudeSentryRelayTools instance with `.definitions` and `.execute(...)`.
    """
    return ClaudeSentryRelayTools(relay)
