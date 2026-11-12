# Sentry Relay Python SDK

[![PyPI version](https://img.shields.io/pypi/v/sentryrelay-sdk.svg)](https://pypi.org/project/sentryrelay-sdk/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](https://opensource.org/licenses/MIT)

Official Python SDK for **[Sentry Relay](https://sentryrelay.com)** (`sentryrelay.com`) — The zero-retention 2FA, OTP, Magic-Link & Authenticator (TOTP) Vault API engineered specifically for autonomous software, AI browser agents, and multi-agent frameworks.

---

## Key Features

- **⚡ Sub-200ms Long-Polling (`/wait`):** Deterministic OTP & magic-link extraction from incoming email and carrier-grade SMS shortcodes via Redis pub/sub push.
- **🛡️ Expiring-Window TOTP Rollover (`auto_wait_fresh_window`):** When `<=4s` remain in an RFC 6238 TOTP window, the SDK automatically pauses and fetches a freshly rolled code so browser agents never fail mid-keystroke.
- **🔄 Sync & Async Support:** Native support for both synchronous (`SentryRelay`) and asynchronous (`AsyncSentryRelay`) workflows.
- **🤖 Native Multi-Framework Agent Integrations:** Turnkey tools for **Google ADK**, **Microsoft Agent Framework**, **PydanticAI**, **OpenAI Agents SDK**, **Claude Agent SDK**, **Strands Agents**, **Agno**, **Smolagents**, **LangGraph**, **CrewAI**, **Browser Use**, and **Playwright**.
- **🔒 Zero Persistent Disk Storage & Ephemeral RAM Inbox:** Ephemeral in-memory queueing (`60s–600s` Redis TTL) with automatic purge or atomic burn-after-read, plus `include_non_auth=True` support exposing sanitized `text_body` and `links` for Gmail/Yahoo forwarding confirmations and 3rd-party SaaS signup verification emails.

---

## Installation

```bash
# Core SDK (httpx + pydantic)
pip install sentryrelay-sdk

# Or using uv:
uv add sentryrelay-sdk
```

### Framework Optional Extras

Install with specialized dependencies for your favorite agent framework:

```bash
pip install "sentryrelay-sdk[google-adk]"        # Google ADK (Gemini & Vertex AI)
pip install "sentryrelay-sdk[microsoft-agents]"   # Microsoft Agent Framework
pip install "sentryrelay-sdk[pydantic-ai]"        # PydanticAI
pip install "sentryrelay-sdk[openai-agents]"      # OpenAI Agents SDK
pip install "sentryrelay-sdk[claude-agent]"       # Claude Agent SDK / Anthropic
pip install "sentryrelay-sdk[strands]"            # Strands Agents
pip install "sentryrelay-sdk[agno]"               # Agno (formerly Phidata)
pip install "sentryrelay-sdk[smolagents]"         # Smolagents (Hugging Face)
pip install "sentryrelay-sdk[langchain]"          # LangGraph / LangChain
pip install "sentryrelay-sdk[crewai]"             # CrewAI
```

---

## Authentication

Set your API key as an environment variable:

```bash
export SENTRY_RELAY_API_KEY="sr_live_..."
# Or test sandbox environment:
export SENTRY_RELAY_API_KEY="sr_test_..."
```

Or pass it directly when instantiating the client:

```python
from sentryrelay import SentryRelay

relay = SentryRelay(api_key="sr_live_...")
```

---

## Quickstart

### 1. Synchronous Client

```python
from sentryrelay import SentryRelay

relay = SentryRelay()

# Wait up to 30s for an inbound OTP (Email or SMS)
auth = relay.wait("checkout-bot", sender="stripe.com", timeout=30)

if auth.matched:
    print(f"Received OTP: {auth.otp_code} in {auth.wait_duration_ms}ms")
    if auth.magic_link:
        print(f"Magic Link: {auth.magic_link}")
```

### 2. Asynchronous Client

```python
import asyncio
from sentryrelay import AsyncSentryRelay

async def main():
    async with AsyncSentryRelay() as relay:
        auth = await relay.wait("checkout-bot", channel="email", timeout=30)
        if auth.matched:
            print(f"OTP Code: {auth.otp_code}")

asyncio.run(main())
```

---

## Agent Framework Integrations

Sentry Relay includes dedicated integration modules in `sentryrelay.integrations` for all major AI agent frameworks.

### 1. Google ADK (Agent Development Kit)

For Gemini and Vertex AI agents built with `google-adk`:

```python
from google.adk.agents.llm_agent import Agent
from sentryrelay import SentryRelay
from sentryrelay.integrations.google_adk import create_google_adk_tools

relay = SentryRelay()
tools = create_google_adk_tools(relay)

agent = Agent(
    model="gemini-2.5-flash",
    name="auth_verifier",
    instruction="Resolve 2FA verification challenges by waiting for codes or retrieving TOTPs.",
    tools=tools,
)
```

### 2. Microsoft Agent Framework

For Microsoft Agent Framework (`agent-framework`) and Azure AI Projects:

```python
from agent_framework import ChatAgent
from sentryrelay import SentryRelay
from sentryrelay.integrations.microsoft_agent import create_microsoft_agent_tools

relay = SentryRelay()
tools = create_microsoft_agent_tools(relay)

agent = ChatAgent(
    name="SecurityAgent",
    tools=tools,
    instructions="Handle 2FA and OTP authentication challenges autonomously.",
)
```

### 3. PydanticAI

Type-safe agent tools with structured schemas for `pydantic-ai`:

```python
from pydantic_ai import Agent
from sentryrelay import SentryRelay
from sentryrelay.integrations.pydantic_ai import register_sentryrelay_tools

relay = SentryRelay()
agent = Agent('openai:gpt-4o', system_prompt="Handle automated authentication.")

# Registers wait_for_verification_code, get_totp_code, and list_identities
register_sentryrelay_tools(agent, relay)

result = agent.run_sync("Log into Okta using identity dev-agent and provide the OTP.")
print(result.data)
```

### 4. OpenAI Agents SDK

For the official OpenAI Agents SDK (`openai-agents` / `agents`):

```python
from agents import Agent, Runner
from sentryrelay import SentryRelay
from sentryrelay.integrations.openai_agents import create_openai_agents_tools

relay = SentryRelay()
tools = create_openai_agents_tools(relay)

agent = Agent(
    name="LoginAssistant",
    instructions="You automate account sign-ins. Use Sentry Relay tools to solve 2FA challenges.",
    tools=tools,
)

result = Runner.run_sync(agent, "Sign in using checkout-bot and retrieve the incoming SMS code.")
print(result.final_output)
```

### 5. Claude Agent SDK & Anthropic Tool Use

For Claude models (`claude-3-7-sonnet`, `claude-3-5-haiku`) and `claude-agent-sdk`:

```python
import anthropic
from sentryrelay import SentryRelay
from sentryrelay.integrations.claude_agent import create_claude_agent_tools

relay = SentryRelay()
tools = create_claude_agent_tools(relay)
client = anthropic.Anthropic()

# Pass tools.definitions directly to messages.create
response = client.messages.create(
    model="claude-3-7-sonnet-20250219",
    max_tokens=1024,
    tools=tools.definitions,
    messages=[{"role": "user", "content": "Wait for OTP code on identity 'checkout-bot'"}],
)

# Dispatch execution
for block in response.content:
    if block.type == "tool_use":
        result = tools.execute(block.name, block.input)
        print("Tool Output:", result)
```

### 6. Strands Agents

For agents built with `strands-agents`:

```python
from strands import Agent
from sentryrelay import SentryRelay
from sentryrelay.integrations.strands import create_strands_tools

relay = SentryRelay()
tools = create_strands_tools(relay)

agent = Agent(
    model="claude-3-7-sonnet-20250219",
    name="browser_auth_agent",
    system_prompt="Resolve OTP and TOTP verification challenges using Sentry Relay.",
    tools=tools,
)
```

### 7. Agno (formerly Phidata)

Integrated `Toolkit` subclass for Agno agents:

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from sentryrelay import SentryRelay
from sentryrelay.integrations.agno import SentryRelayTools

relay = SentryRelay()

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[SentryRelayTools(relay)],
    instructions="Solve 2FA challenges by waiting on inbound codes or generating live TOTPs.",
)

agent.print_response("Wait for the 2FA code sent to identity 'checkout-bot'")
```

### 8. Smolagents (Hugging Face)

Native `Tool` classes for Hugging Face `smolagents`:

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

agent.run("Fetch the latest TOTP authenticator code for identity 'checkout-bot' with secret 'github_ops'")
```

### 9. LangGraph & LangChain

```python
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from sentryrelay import SentryRelay
from sentryrelay.integrations.langgraph import create_sentryrelay_tools

relay = SentryRelay()
tools = create_sentryrelay_tools(relay)
llm = ChatOpenAI(model="gpt-4o")

app = create_react_agent(llm, tools=tools)
```

### 10. CrewAI

```python
from crewai import Agent, Task, Crew
from sentryrelay import SentryRelay
from sentryrelay.integrations.crewai import create_crewai_tools

relay = SentryRelay()
tools = create_crewai_tools(relay)

auth_specialist = Agent(
    role="Authentication Specialist",
    goal="Handle 2FA and MFA verification challenges",
    backstory="Expert at retrieving inbound OTP codes and managing TOTP credentials",
    tools=tools,
)
```

### 11. Browser Use

Integrate Sentry Relay actions into your [Browser Use](https://browser-use.com) controller:

```python
from browser_use import Agent, Controller
from sentryrelay import AsyncSentryRelay
from sentryrelay.integrations.browser_use import register_sentryrelay_actions

controller = Controller()
relay = AsyncSentryRelay()

# Registers 'wait_for_2fa_code' and 'get_totp_token'
register_sentryrelay_actions(controller, relay)

agent = Agent(
    task="Log into Stripe, enter credentials, and supply 2FA verification code using identity 'checkout-bot'",
    controller=controller,
)
```

### 12. Playwright Python (Async)

```python
import asyncio
from playwright.async_api import async_playwright
from sentryrelay import AsyncSentryRelay, fill_otp_code

async def test_login():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        async with AsyncSentryRelay() as relay:
            # 1. Trigger login form
            await page.goto("https://app.target.com/login")
            await page.fill('input[type="email"]', "checkout-bot@in.sentryrelay.com")
            await page.click('button[type="submit"]')

            # 2. Intercept OTP in <200ms of arrival
            auth = await relay.wait("checkout-bot", sender="target.com", timeout=30)

            # 3. Fill the OTP code into the challenge prompt
            await fill_otp_code(page, 'input[name="otp"]', auth)
            await page.click('button#verify')

            await browser.close()

asyncio.run(test_login())
```

---

## RFC 6238 TOTP Authenticator Vault

```python
from sentryrelay import SentryRelay

relay = SentryRelay()

# Generate a live 6-digit TOTP code
# auto_wait_fresh_window=True automatically waits <4s if the current 30s period is expiring
totp = relay.totp.get("checkout-bot", "github_ops")

print(f"Code: {totp.code} ({totp.remaining_seconds}s remaining)")
```

---

## API Reference

### `relay.identities`

- `relay.identities.list(limit=None, cursor=None)`
- `relay.identities.get(id_or_slug)`
- `relay.identities.create(name, slug=None, email_handle=None, fallback=None, custom_rules=None)`
- `relay.identities.update(id_or_slug, name=None, status=None, fallback=None, custom_rules=None)`
- `relay.identities.delete(id_or_slug)`
- `relay.identities.wait(id_or_slug, timeout=30, since=None, channel=None, sender=None, subject=None, consume=True)`
- `relay.identities.latest(id_or_slug, lookback_seconds=60, since=None, channel=None, sender=None, subject=None, consume=True)`
- `relay.identities.provision_sms_did(id_or_slug, area_code=None)`
- `relay.identities.release_sms_did(id_or_slug)`

### `relay.totp`

- `relay.totp.list(id_or_slug)`
- `relay.totp.create(id_or_slug, otpauth_uri=None, secret=None, issuer=None, ...)`
- `relay.totp.get(id_or_slug, secret_id, auto_wait_fresh_window=True, now_ms=None)`
- `relay.totp.delete(id_or_slug, secret_id)`

### `relay.webhooks`

- `relay.webhooks.list()`
- `relay.webhooks.create(target_url, events, scoped_identity_ids=None)`
- `relay.webhooks.delete(webhook_id)`

### `relay.audit_logs`

- `relay.audit_logs.list(identity_id=None, event_type=None, from_time=None, to_time=None, limit=None)`

---

## License

MIT © [Sentry Relay](https://sentryrelay.com)
