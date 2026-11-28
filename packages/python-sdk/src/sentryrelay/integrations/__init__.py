"""
Sentry Relay Integrations for Agent Runtimes & Frameworks
"""

from sentryrelay.integrations.agno import SentryRelayTools as AgnoSentryRelayTools, create_agno_tools
from sentryrelay.integrations.browser_use import (
    create_browser_use_actions,
    register_sentryrelay_actions,
)
from sentryrelay.integrations.claude_agent import (
    ClaudeSentryRelayTools,
    create_claude_agent_tools,
)
from sentryrelay.integrations.crewai import create_crewai_tools
from sentryrelay.integrations.google_adk import create_google_adk_tools
from sentryrelay.integrations.langgraph import (
    create_langchain_tools,
    create_sentryrelay_tools,
)
from sentryrelay.integrations.microsoft_agent import create_microsoft_agent_tools
from sentryrelay.integrations.openai_agents import create_openai_agents_tools
from sentryrelay.integrations.playwright import fill_otp_code
from sentryrelay.integrations.pydantic_ai import (
    create_pydantic_ai_tools,
    register_sentryrelay_tools,
)
from sentryrelay.integrations.smolagents import (
    SentryRelayIdentitiesTool as SmolagentsIdentitiesTool,
    SentryRelayTotpTool as SmolagentsTotpTool,
    SentryRelayWaitTool as SmolagentsWaitTool,
    create_smolagents_tools,
)
from sentryrelay.integrations.strands import create_strands_tools

__all__ = [
    # Browser Use & Playwright
    "create_browser_use_actions",
    "register_sentryrelay_actions",
    "fill_otp_code",
    # LangGraph & CrewAI
    "create_langchain_tools",
    "create_crewai_tools",
    # Google ADK
    "create_google_adk_tools",
    # Microsoft Agent Framework
    "create_microsoft_agent_tools",
    # PydanticAI
    "create_pydantic_ai_tools",
    "register_sentryrelay_tools",
    # OpenAI Agents SDK
    "create_openai_agents_tools",
    # Claude Agent SDK / Anthropic Tool Use
    "ClaudeSentryRelayTools",
    "create_claude_agent_tools",
    # Strands Agents
    "create_strands_tools",
    # Agno
    "AgnoSentryRelayTools",
    "create_agno_tools",
    # Smolagents
    "SmolagentsWaitTool",
    "SmolagentsTotpTool",
    "SmolagentsIdentitiesTool",
    "create_smolagents_tools",
]
