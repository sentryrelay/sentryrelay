# `@sentryrelay/sdk` — Official TypeScript & Node.js SDK

Official TypeScript & Node.js SDK for **[Sentry Relay](https://sentryrelay.com)** (`sentryrelay.com`) — The Out-of-Band 2FA, OTP, Magic-Link & Cloud KMS TOTP Authenticator Relay for Autonomous Agents and Headless Browsers (Playwright, Stagehand, Browserbase).

## Installation

```bash
npm install @sentryrelay/sdk
```

## Authentication

Set your API key via the `SENTRY_RELAY_API_KEY` environment variable:

```bash
export SENTRY_RELAY_API_KEY="sr_live_..."
```

## Quickstart (Playwright / Stagehand)

```typescript
import { SentryRelay, fillOtpCode } from '@sentryrelay/sdk';

const relay = new SentryRelay({
  apiKey: process.env.SENTRY_RELAY_API_KEY!,
});

// 1. Trigger login challenge and record start timestamp
const since = Date.now();
await page.fill('input[type="email"]', 'checkout-bot@in.sentryrelay.com');
await page.click('button[type="submit"]');

// 2. Wait up to 30s (<200ms Redis Pub/Sub push delivery, atomic burn-after-read)
// Pass includeNonAuth: true to also receive non-auth onboarding/signup emails (auth.event.textBody & auth.event.links)
const auth = await relay.identities.wait('checkout-bot', {
  channel: 'email',
  sender: 'stripe.com',
  since,
  timeout: 30,
});

if (!auth.matched || !auth.event) {
  throw new Error(`Timed out waiting for OTP after ${auth.waitDurationMs}ms`);
}

// Automatically fills single-field or 6-box split OTP inputs
await fillOtpCode(page, 'input[name="otp"]', auth);

// 3. Generate live RFC 6238 TOTP code (auto-waits <4s if window is expiring)
const totp = await relay.totp.get('checkout-bot', 'github_ops');
console.log(totp.code, totp.remainingSeconds);
```

## Documentation

- **Full Docs:** [https://sentryrelay.com/docs](https://sentryrelay.com/docs)
- **LLM Reference:** [https://sentryrelay.com/llms-full.txt](https://sentryrelay.com/llms-full.txt)
- **OpenAPI 3.1 Spec:** [https://sentryrelay.com/openapi.json](https://sentryrelay.com/openapi.json)

## License

MIT © [Sentry Relay](https://sentryrelay.com)
