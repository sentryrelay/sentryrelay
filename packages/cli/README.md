# `sentryrelay` (`srelay` CLI)

Official command-line interface (`srelay`) for **[Sentry Relay](https://sentryrelay.com)** (`sentryrelay.com`) — The Out-of-Band 2FA, OTP, Magic-Link & Cloud KMS TOTP Authenticator Relay for Autonomous Agents and CI/CD pipelines.

## Installation

```bash
npm install -g sentryrelay
```

## Quickstart

```bash
# 1. Authenticate (stores key in ~/.config/sentryrelay/credentials.json with 0600 permissions)
srelay login --key sr_live_...
# Or set SENTRY_RELAY_API_KEY in your environment:
export SENTRY_RELAY_API_KEY="sr_live_..."

# 2. List and create Identities (@in.sentryrelay.com)
srelay identities list
srelay identities create --name "Staging Bot" --handle staging-bot

# 3. Wait for an incoming Email or SMS OTP (--raw outputs ONLY the code + newline to stdout)
CODE=$(srelay wait staging-bot --sender github.com --timeout 30 --raw)
echo "Extracted OTP: $CODE"

# Inspect full sanitized message body & links (including non-auth onboarding/forwarding emails)
srelay wait staging-bot --include-non-auth --show-body

# 4. Vault and generate live RFC 6238 TOTP codes
srelay totp add staging-bot github_ops "otpauth://totp/GitHub:bot?secret=JBSWY3DPEHPK3PXP&issuer=GitHub"
TOTP=$(srelay totp get staging-bot github_ops --raw)
```

## Documentation

- **Docs:** [https://sentryrelay.com/docs](https://sentryrelay.com/docs)
- **LLM Reference:** [https://sentryrelay.com/llms-full.txt](https://sentryrelay.com/llms-full.txt)

## License

MIT © [Sentry Relay](https://sentryrelay.com)
