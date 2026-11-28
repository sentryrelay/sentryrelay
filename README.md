# Sentry Relay — Official SDKs, MCP Server, CLI & Multi-Agent Plugin

[![Website](https://img.shields.io/badge/sentryrelay.com-000000?style=flat&logo=vercel&logoColor=white)](https://sentryrelay.com)
[![Docs](https://img.shields.io/badge/docs-sentryrelay.com%2Fdocs-emerald)](https://sentryrelay.com/docs)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Sentry Relay MCP connector – tool definition quality and endpoint health on Glama](https://glama.ai/mcp/connectors/io.github.sentryrelay/sentryrelay/badges/score.svg)](https://glama.ai/mcp/connectors/io.github.sentryrelay/sentryrelay)

**Sentry Relay** ([sentryrelay.com](https://sentryrelay.com)) is the Out-of-Band 2FA, OTP, Magic-Link & Cloud KMS TOTP Authenticator Relay engineered for unattended AI browser agents (Playwright, Stagehand, Browser Use, Skyvern, Steel, Kernel), multi-agent frameworks, and RPA agencies—featuring a 60s–600s Ephemeral RAM Inbox (`includeNonAuth`, `textBody`, `links[]`) with Zero Persistent Disk Storage and the Email + SMS + Voice Human-Fallback Safety Bridge™.

This repository is packaged both as our open-source client monorepo **and** as a **universal coding-agent plugin** compatible with **Antigravity, Claude Code, OpenAI Codex, Cursor, Gemini CLI, and `skills.sh`**.

| Package / Directory | Registry / Surface | Description |
| :--- | :--- | :--- |
| [`packages/sdk`](./packages/sdk) | `@sentryrelay/sdk` (npm) | Official zero-dependency TypeScript & Node.js SDK (`relay.wait()`, `relay.totp.get()`) |
| [`packages/python-sdk`](./packages/python-sdk) | `sentryrelay-sdk` (PyPI) | Official Python SDK (Sync & Async) with `fill_otp_code` and 12 native AI agent framework integrations |
| [`packages/mcp`](./packages/mcp) | `@sentryrelay/mcp` (npm / MCP Registry) | Official Model Context Protocol (MCP) server exposing 6 annotated 2FA/TOTP tools |
| [`packages/cli`](./packages/cli) | `sentryrelay` (npm — `srelay` binary) | Command-line interface for headless CI/CD scripts (`srelay wait --raw`, `srelay totp get --raw`) |
| [`skills/`](./skills) | `sentryrelay`, `sentryrelay-browser-2fa`, `sentryrelay-agency-forwarding` | 3 Agent Skills covering core auth, headless browser 2FA recovery, and multi-client agency forwarding |
| [`agents/`](./agents) & [`rules/`](./rules) | Universal Agent Plugin | `2fa-integration-architect` subagent + best-practices ruleset |
| `.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`, `plugin.json` | Coding Agent Marketplaces | Native plugin & marketplace manifests for Claude Code, OpenAI Codex, Antigravity, Cursor & Gemini CLI |

---

## Install as a Coding-Agent Plugin

Set `export SENTRY_RELAY_API_KEY="sr_live_..."` (or `sr_test_...`) in your environment, then install with one command:

```bash
# Claude Code (Plugin + Marketplace)
/plugin marketplace add sentryrelay/sentryrelay
/plugin install sentryrelay@sentryrelay

# OpenAI Codex / Universal Agent Skills
npx skills add sentryrelay/sentryrelay

# Gemini CLI Extension
gemini extensions install https://github.com/sentryrelay/sentryrelay
```

Or add the plugin directly from `https://github.com/sentryrelay/sentryrelay` in **Antigravity Plugins Manager**, **Cursor**, or **OpenAI Codex** (`/plugins`, backed by `.codex-plugin/plugin.json` and `.agents/plugins/marketplace.json`).

---

## Quick Install (Individual Packages & MCP)

### 1. Model Context Protocol (MCP) Server

```bash
# Claude Code CLI (One-Liner)
claude mcp add sentryrelay \
  -e SENTRY_RELAY_API_KEY=sr_live_... \
  -- npx -y @sentryrelay/mcp
```

Or connect any Streamable HTTP MCP client directly to `https://sentryrelay.com/api/mcp` with `Authorization: Bearer $SENTRY_RELAY_API_KEY`.

### 2. Agent Skill (`SKILL.md`)

```bash
npx skills add https://sentryrelay.com/skills/sentryrelay/SKILL.md
```

### 3. TypeScript / Playwright / Stagehand SDK

```bash
npm install @sentryrelay/sdk
```

### 4. Python SDK

```bash
pip install sentryrelay-sdk
```

### 5. `srelay` CLI

```bash
npm install -g sentryrelay
```

---

## Machine-Readable Discovery for AI Agents

- **`/llms.txt`:** [https://sentryrelay.com/llms.txt](https://sentryrelay.com/llms.txt)
- **`/llms-full.txt`:** [https://sentryrelay.com/llms-full.txt](https://sentryrelay.com/llms-full.txt)
- **OpenAPI 3.1 Spec:** [https://sentryrelay.com/openapi.json](https://sentryrelay.com/openapi.json)
- **MCP Discovery Manifest:** [https://sentryrelay.com/.well-known/mcp.json](https://sentryrelay.com/.well-known/mcp.json)
- **Vendor 2FA Recipes (15 Vendors):** [https://sentryrelay.com/docs/guides/vendors](https://sentryrelay.com/docs/guides/vendors)

## License

MIT © [Sentry Relay](https://sentryrelay.com)
