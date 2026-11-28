---
name: sentryrelay-browser-2fa
description: Automate Email OTPs, unwrapped Magic Links, dedicated US SMS DIDs, and rollover-safe Cloud KMS TOTP inside Playwright, Stagehand, Browserbase Contexts, Browser Use, Steel, and Kernel workflows—including self-healing 2FA recovery when cookies expire and 1Password co-deployment.
license: MIT
metadata:
  author: sentryrelay
  version: "0.2.1"
  homepage: https://sentryrelay.com/docs/guides/vendors
  source: https://github.com/sentryrelay/sentryrelay
---

# Sentry Relay Browser Automation 2FA Skill

Use this skill when building or fixing headless browser logins across **Playwright**, **Stagehand**, **Browserbase**, **Browser Use**, **Steel**, or **Kernel** that hit Email OTP, Magic-Link, Carrier SMS, or TOTP challenges.

## 1. Self-Healing Browserbase Context / Profile Pattern

Persistent cookies (`Browserbase Contexts`, Playwright `storageState`, Steel sessions, Kernel profiles) speed up warm runs but still invalidate due to forced server logouts, concurrent runs, read-only `Authenticated Fetch` rolling cookies, OS mismatches, or proxy ASN shifts. Keep Contexts as L1 cache and add Sentry Relay as L2 automatic recovery:

```typescript
import { Stagehand } from '@browserbasehq/stagehand';
import { SentryRelay } from '@sentryrelay/sdk';

const relay = new SentryRelay({ apiKey: process.env.SENTRY_RELAY_API_KEY! });

export async function runWithSelfHealingContext(contextId: string) {
  const stagehand = new Stagehand({
    env: 'BROWSERBASE',
    browserbaseSessionCreateParams: {
      browserSettings: { context: { id: contextId, persist: true } },
    },
  });

  await stagehand.init();
  const page = stagehand.page;
  await page.goto('https://portal.vendor.com/dashboard');

  if (/login|signin|verify/i.test(page.url())) {
    const since = Date.now();
    await page.act({ action: 'Submit login email and password' });

    const auth = await relay.wait('vendor-bot', {
      sender: 'vendor.com',
      since,
      timeout: 35,
    });

    if (auth.event?.otpCode) {
      await page.act({ action: `Enter verification code ${auth.event.otpCode} and submit` });
    } else if (auth.event?.magicLink) {
      await page.goto(auth.event.magicLink);
    }
  }

  await stagehand.close();
}
```

## 2. Browser Use (Python) Native Actions

```python
from browser_use import Agent, Controller
from sentryrelay import AsyncSentryRelay
from sentryrelay.integrations.browser_use import register_sentryrelay_actions

controller = Controller()
relay = AsyncSentryRelay()
register_sentryrelay_actions(controller, relay)

agent = Agent(
    task=(
        "Log into https://dashboard.stripe.com/login for identity 'stripe-ops'. "
        "Call wait_for_2fa_code(identity='stripe-ops', sender='stripe.com') for SMS/Email OTP, "
        "or get_totp_token(identity='stripe-ops', secret_id='stripe_totp') for Authenticator codes."
    ),
    controller=controller,
)
```

## 3. Curated Stage 4 Vendor Rules (15+ SaaS & Auth Providers)

Sentry Relay deterministically extracts codes in `<8ms` (filtering out invoices, receipts, and PR noise) for:
- `github` (`github.com`) — device OTPs, `/sessions/verified-device`, TOTP
- `google` (`google.com`, `accounts.google.com`) — strips `G-` SMS prefix, Gmail Forwarding 9-digit verification
- `aws` (`amazon.com`, `amazonaws.com`, `aws.amazon.com`, `signin.aws`) — IAM/Root TOTP, Email OTP
- `stripe` (`stripe.com`) — collapses `123-456` hyphenated codes, SMS, magic links
- `shopify` (`shopify.com`), `cloudflare` (`cloudflare.com`, `notify.cloudflare.com`)
- `clerk` (`clerk.com`, `clerk.dev`, `accounts.dev`, `__clerk_ticket` unwrapping)
- `auth0` (`auth0.com`), `okta` (`okta.com`, `oktapreview.com`), `vercel` (`vercel.com`)
- `microsoft` (`microsoft.com`, `accountprotection.microsoft.com`, `live.com`, `office.com`) — 6–8 digit single-use codes
- `openai` (`openai.com`, `tm.openai.com`), `anthropic` (`anthropic.com`, `mail.anthropic.com`, `claude.ai`)
- `discord` (`discord.com`, `discordapp.com` — unwraps `/authorize-ip`), `slack` (`slack.com` — preserves `A4B-9K2` codes)

Full copy-paste recipes & Gmail forwarding filters: `https://sentryrelay.com/docs/guides/vendors`.

## 4. Rollover-Safe Cloud KMS TOTP

Never call raw TOTP generators right before an LLM browser step (`stagehand.act` takes 2–4s). Always use `relay.totp.get(identity, secretId)` (`autoWaitFreshWindow: true` by default), which automatically waits out `<=4s` period rollovers so the agent receives a fresh 26–30s code.
