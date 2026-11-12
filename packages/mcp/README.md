# `@sentryrelay/mcp` — Official Sentry Relay MCP Server

Official Model Context Protocol (MCP) server for **[Sentry Relay](https://sentryrelay.com)** (`sentryrelay.com`) — giving Claude Code, Claude Desktop, Cursor, Windsurf, and custom MCP agents native tools to intercept 2FA OTPs, magic links, and live RFC 6238 TOTP authenticator codes.

## Quick Setup

### 1. Claude Code CLI (One-Liner)

```bash
claude mcp add sentryrelay \
  -e SENTRY_RELAY_API_KEY=sr_live_your_api_key_here \
  -- npx -y @sentryrelay/mcp
```

### 2. Claude Desktop / Cursor / Windsurf (`stdio`)

```json
{
  "mcpServers": {
    "sentryrelay": {
      "command": "npx",
      "args": ["-y", "@sentryrelay/mcp"],
      "env": {
        "SENTRY_RELAY_API_KEY": "sr_live_your_api_key_here"
      }
    }
  }
}
```

### 3. Hosted Streamable HTTP Endpoint (Zero-Install)

Connect any Streamable HTTP MCP client directly to:
- **Endpoint:** `https://sentryrelay.com/api/mcp`
- **Header:** `Authorization: Bearer sr_live_your_api_key_here`

## Available MCP Tools (6 Canonical Tools)

| Tool Name | Description |
| :--- | :--- |
| `wait_for_verification_code` | Long-poll up to 45s (`<200ms` push delivery) for an incoming Email or SMS OTP, magic link, or signup message (`identity`, `channel`, `sender`, `subject`, `timeoutSeconds`, `consume`, `includeNonAuth`). Returns `otpCode`, `magicLink`, `textBody`, and `links[]`. |
| `get_latest_verification_code` | Instant non-blocking Redis ZSET timeline check (`lookbackSeconds`, default 60s, `includeNonAuth`). |
| `get_totp_code` | Generate a live 6- or 8-digit RFC 6238 authenticator code with automatic expiring-window rollover (`autoWaitFreshWindow: true`). |
| `list_identities` | List accessible agent Identities (`@in.sentryrelay.com` email addresses, Telnyx US DIDs, and TOTP secret counts). |
| `create_identity` | Provision a new isolated Identity inbox (`<handle>@in.sentryrelay.com`). |
| `store_totp_secret` | Vault an `otpauth://totp/...` URI or Base32 secret into Cloud KMS envelope encryption. |

## Documentation

- **MCP Reference:** [https://sentryrelay.com/docs/mcp](https://sentryrelay.com/docs/mcp)
- **Discovery Manifest:** [https://sentryrelay.com/.well-known/mcp.json](https://sentryrelay.com/.well-known/mcp.json)
- **LLM Reference:** [https://sentryrelay.com/llms-full.txt](https://sentryrelay.com/llms-full.txt)

## License

MIT © [Sentry Relay](https://sentryrelay.com)
