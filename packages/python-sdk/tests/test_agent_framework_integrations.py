"""
Unit and Integration Tests for Sentry Relay AI Agent Framework Integrations:
- Google ADK
- Microsoft Agent Framework
- PydanticAI
- OpenAI Agents SDK
- Claude Agent SDK / Anthropic Tool Use
- Strands Agents
- Agno
- Smolagents
"""

import httpx
import pytest
import respx
from sentryrelay import AsyncSentryRelay, SentryRelay
from sentryrelay.integrations.agno import SentryRelayTools as AgnoTools, create_agno_tools
from sentryrelay.integrations.claude_agent import (
    ClaudeSentryRelayTools,
    create_claude_agent_tools,
)
from sentryrelay.integrations.google_adk import create_google_adk_tools
from sentryrelay.integrations.microsoft_agent import create_microsoft_agent_tools
from sentryrelay.integrations.openai_agents import create_openai_agents_tools
from sentryrelay.integrations.pydantic_ai import (
    create_pydantic_ai_tools,
    register_sentryrelay_tools,
)
from sentryrelay.integrations.smolagents import (
    SentryRelayIdentitiesTool,
    SentryRelayTotpTool,
    SentryRelayWaitTool,
    create_smolagents_tools,
)
from sentryrelay.integrations.strands import create_strands_tools

BASE_URL = "https://sentryrelay.com"


@pytest.fixture
def mock_relay_api():
    """Mock standard Sentry Relay endpoints for wait, totp, and identities."""
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as respx_mock:
        # Wait endpoint
        respx_mock.get(url__regex=r"/api/v1/identities/.+/wait.*").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": {
                        "matched": True,
                        "timedOut": False,
                        "event": {
                            "id": "evt_test_999",
                            "identityId": "id_test_bot",
                            "channel": "email",
                            "classification": "otp",
                            "otpCode": "123456",
                            "magicLink": "https://auth.stripe.com/verify?token=xyz",
                            "sender": "auth@stripe.com",
                            "receivedAtMs": 1700000000000,
                            "receivedAtIso": "2026-11-02T12:00:00Z",
                        },
                        "waitDurationMs": 850,
                    }
                },
            )
        )

        # TOTP endpoint
        respx_mock.get(url__regex=r"/api/v1/identities/.+/totp/.+").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": {
                        "code": "849201",
                        "remainingSeconds": 24,
                        "period": 30,
                        "digits": 6,
                        "algorithm": "SHA1",
                    }
                },
            )
        )

        # Identities list endpoint
        respx_mock.get(url__regex=r"/api/v1/identities.*").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": {
                        "items": [
                            {
                                "id": "id_test_bot",
                                "name": "Test Bot",
                                "slug": "test-bot",
                                "emailHandle": "test-bot",
                                "emailDomain": "in.sentryrelay.com",
                                "emailAddress": "test-bot@in.sentryrelay.com",
                                "phoneNumber": "+18005550199",
                            }
                        ]
                    }
                },
            )
        )
        yield respx_mock


# ==========================================
# 1. Google ADK Tests
# ==========================================

def test_google_adk_sync_tools(mock_relay_api, live_api_key: str):
    relay = SentryRelay(api_key=live_api_key)
    tools = create_google_adk_tools(relay)
    assert len(tools) == 3

    tool_dict = {fn.__name__: fn for fn in tools}
    assert "wait_for_verification_code" in tool_dict
    assert "get_totp_code" in tool_dict
    assert "list_identities" in tool_dict

    # Test tool invocation
    wait_fn = tool_dict["wait_for_verification_code"]
    res = wait_fn(identity="test-bot", sender="stripe.com")
    assert res["matched"] is True
    assert res["otp_code"] == "123456"

    totp_fn = tool_dict["get_totp_code"]
    totp_res = totp_fn(identity="test-bot", secret_id="sec_1")
    assert totp_res["code"] == "849201"

    list_fn = tool_dict["list_identities"]
    identities = list_fn()
    assert len(identities) == 1
    assert identities[0]["slug"] == "test-bot"


@pytest.mark.asyncio
async def test_google_adk_async_tools(mock_relay_api, live_api_key: str):
    relay = AsyncSentryRelay(api_key=live_api_key)
    tools = create_google_adk_tools(relay)
    assert len(tools) == 3

    tool_dict = {fn.__name__: fn for fn in tools}
    wait_fn = tool_dict["wait_for_verification_code"]
    res = await wait_fn(identity="test-bot")
    assert res["matched"] is True
    assert res["otp_code"] == "123456"
    await relay.close()


# ==========================================
# 2. Microsoft Agent Framework Tests
# ==========================================

def test_microsoft_agent_sync_tools(mock_relay_api, live_api_key: str):
    relay = SentryRelay(api_key=live_api_key)
    tools = create_microsoft_agent_tools(relay)
    assert len(tools) == 3

    tool_names = [getattr(t, "__name__", getattr(t, "name", str(t))) for t in tools]
    assert "wait_for_verification_code" in tool_names
    assert "get_totp_code" in tool_names
    assert "list_identities" in tool_names


@pytest.mark.asyncio
async def test_microsoft_agent_async_tools(mock_relay_api, live_api_key: str):
    relay = AsyncSentryRelay(api_key=live_api_key)
    tools = create_microsoft_agent_tools(relay)
    assert len(tools) == 3
    await relay.close()


# ==========================================
# 3. PydanticAI Tests
# ==========================================

def test_pydantic_ai_tools(mock_relay_api, live_api_key: str):
    relay = SentryRelay(api_key=live_api_key)
    tools = create_pydantic_ai_tools(relay)
    assert len(tools) == 3

    tool_dict = {fn.__name__: fn for fn in tools}
    wait_res = tool_dict["wait_for_verification_code"]("test-bot")
    assert wait_res["otp_code"] == "123456"

    class MockAgent:
        def __init__(self):
            self.registered = []

        def tool_plain(self, fn):
            self.registered.append(fn)
            return fn

    agent = MockAgent()
    register_sentryrelay_tools(agent, relay)
    assert len(agent.registered) == 3


# ==========================================
# 4. OpenAI Agents SDK Tests
# ==========================================

def test_openai_agents_sync_tools(mock_relay_api, live_api_key: str):
    relay = SentryRelay(api_key=live_api_key)
    tools = create_openai_agents_tools(relay)
    assert len(tools) == 3

    tool_dict = {getattr(fn, "__name__", getattr(fn, "name", str(fn))): fn for fn in tools}
    wait_fn = tool_dict["wait_for_verification_code"]
    res = wait_fn(identity="test-bot")
    assert "123456" in res


@pytest.mark.asyncio
async def test_openai_agents_async_tools(mock_relay_api, live_api_key: str):
    relay = AsyncSentryRelay(api_key=live_api_key)
    tools = create_openai_agents_tools(relay)
    assert len(tools) == 3
    await relay.close()


# ==========================================
# 5. Claude Agent SDK / Anthropic Tool Use Tests
# ==========================================

def test_claude_agent_sync_tools(mock_relay_api, live_api_key: str):
    relay = SentryRelay(api_key=live_api_key)
    tools = create_claude_agent_tools(relay)

    # Verify tool schemas
    assert len(tools.definitions) == 3
    names = [d["name"] for d in tools.definitions]
    assert "wait_for_verification_code" in names
    assert "get_totp_code" in names
    assert "list_identities" in names

    # Iterable support
    assert len(list(tools)) == 3

    # Dispatch execution
    wait_output = tools.execute("wait_for_verification_code", {"identity": "test-bot"})
    assert "123456" in wait_output

    totp_output = tools.execute("get_totp_code", {"identity": "test-bot", "secret_id": "sec_1"})
    assert "849201" in totp_output

    identities_output = tools.execute("list_identities", {})
    assert len(identities_output) == 1
    assert identities_output[0]["slug"] == "test-bot"


@pytest.mark.asyncio
async def test_claude_agent_async_tools(mock_relay_api, live_api_key: str):
    relay = AsyncSentryRelay(api_key=live_api_key)
    tools = create_claude_agent_tools(relay)

    wait_output = await tools.execute("wait_for_verification_code", {"identity": "test-bot"})
    assert "123456" in wait_output
    await relay.close()


# ==========================================
# 6. Strands Agents Tests
# ==========================================

def test_strands_sync_tools(mock_relay_api, live_api_key: str):
    relay = SentryRelay(api_key=live_api_key)
    tools = create_strands_tools(relay)
    assert len(tools) == 3

    tool_dict = {fn.__name__: fn for fn in tools}
    assert "wait_for_verification_code" in tool_dict
    assert "get_totp_code" in tool_dict
    assert "list_identities" in tool_dict

    res = tool_dict["wait_for_verification_code"]("test-bot")
    assert "123456" in res


@pytest.mark.asyncio
async def test_strands_async_tools(mock_relay_api, live_api_key: str):
    relay = AsyncSentryRelay(api_key=live_api_key)
    tools = create_strands_tools(relay)
    assert len(tools) == 3
    await relay.close()


# ==========================================
# 7. Agno Integration Tests
# ==========================================

def test_agno_tools(mock_relay_api, live_api_key: str):
    relay = SentryRelay(api_key=live_api_key)
    toolkit = create_agno_tools(relay)
    assert isinstance(toolkit, AgnoTools)

    # Check registered tools
    registered = toolkit.tools
    assert len(registered) == 3

    # Call toolkit methods
    wait_res = toolkit.wait_for_verification_code("test-bot")
    assert "123456" in wait_res

    totp_res = toolkit.get_totp_code("test-bot", "sec_1")
    assert "849201" in totp_res

    list_res = toolkit.list_identities()
    assert "test-bot" in list_res


# ==========================================
# 8. Smolagents Integration Tests
# ==========================================

def test_smolagents_tools(mock_relay_api, live_api_key: str):
    relay = SentryRelay(api_key=live_api_key)
    tools = create_smolagents_tools(relay)
    assert len(tools) == 3

    wait_tool, totp_tool, identities_tool = tools
    assert isinstance(wait_tool, SentryRelayWaitTool)
    assert isinstance(totp_tool, SentryRelayTotpTool)
    assert isinstance(identities_tool, SentryRelayIdentitiesTool)

    # Test forward calls
    wait_res = wait_tool.forward(identity="test-bot")
    assert "123456" in wait_res

    totp_res = totp_tool.forward(identity="test-bot", secret_id="sec_1")
    assert "849201" in totp_res

    identities_res = identities_tool.forward()
    assert "test-bot" in identities_res
