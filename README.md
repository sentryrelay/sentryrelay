# Sentry Relay — Official SDKs, MCP Server, CLI & Agent Skill

[![Website](https://img.shields.io/badge/sentryrelay.com-000000?style=flat&logo=vercel&logoColor=white)](https://sentryrelay.com)
[![Docs](https://img.shields.io/badge/docs-sentryrelay.com%2Fdocs-emerald)](https://sentryrelay.com/docs)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)

**Sentry Relay** ([sentryrelay.com](https://sentryrelay.com)) is the Out-of-Band 2FA, OTP, Magic-Link & Cloud KMS TOTP Authenticator Relay engineered for unattended AI browser agents (Playwright, Stagehand, Browser Use, Skyvern), multi-agent frameworks, and RPA agencies—featuring a 60s–600s Ephemeral RAM Inbox (`includeNonAuth`, `textBody`, `links[]`) with Zero Persistent Disk Storage and the Email + SMS + Voice Human-Fallback Safety Bridge™.

This repository contains the official open-source client ecosystem for Sentry Relay:

| Package / Directory | Registry | Description |
| :--- | :--- | :--- |
| [`packages/sdk`](./packages/sdk) | `@sentryrelay/sdk` (npm) | Official zero-dependency TypeScript & Node.js SDK with Playwright/Stagehand `fillOtpCode` helpers |
| [`packages/python-sdk`](./packages/python-sdk) | `sentryrelay-sdk` (PyPI) | Official Python SDK (Sync & Async) with 12 native AI agent framework integrations |
| [`packages/mcp`](./packages/mcp) | `@sentryrelay/mcp` (npm / MCP Registry) | Official Model Context Protocol (MCP) server exposing 6 canonical 2FA/TOTP tools |
| [`packages/cli`](./packages/cli) | `sentryrelay` (npm — `srelay` binary) | Command-line interface for headless CI/CD scripts (`srelay wait --raw`, `srelay totp get --raw`) |
| [`skills/sentryrelay`](./skills/sentryrelay) | `SKILL.md` | Installable Agent Skill for Claude Code, Cursor, Codex, and Windsurf |

---

## Quick Install

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

## License

MIT © [Sentry Relay](https://sentryrelay.com)
