---
name: sentryrelay-agency-forwarding
description: Set up multi-client B2B automation agencies (n8n, Make, Apify) using Sentry Relay's 60-second Zero-Edit Gmail/Outlook forwarding unwrapper, per-client Scoped API Keys (scopedIdentityIds), and The Human-Fallback Safety Bridge (Resend email, Slack/Discord webhook, and Telnyx TeXML voice Dial).
license: MIT
metadata:
  author: sentryrelay
  version: "0.2.1"
  homepage: https://sentryrelay.com/docs/guides/email-forwarding
  source: https://github.com/sentryrelay/sentryrelay
---

# Sentry Relay Multi-Client Agency & Email Forwarding Skill

Use this skill when connecting existing corporate Gmail/Google Workspace or Microsoft 365 inboxes to Sentry Relay—or architecting multi-tenant n8n, Make.com, or Apify automation fleets across 5–250+ client accounts.

## 1. 60-Second Zero-Vendor-Edit Email Forwarding

Clients rarely want to swap their registered corporate email (`ops@client.com`) on Stripe, AWS, NetSuite, or insurance portals to a bot domain. Instead:
1. Create an isolated Identity (`<client-slug>@in.sentryrelay.com`).
2. Add `<client-slug>@in.sentryrelay.com` as a forwarding address in Gmail (`Settings -> Forwarding and POP/IMAP`) or Outlook Web (`Settings -> Mail -> Rules`).
3. Confirm Gmail forwarding automatically: Sentry Relay's Stage 4 Google rule extracts Gmail's 9-digit confirmation code and `/mail/vf-` confirmation URL—and forwards a copy via Resend to `fallbackEmail` when Human Fallback is enabled.
4. Create a narrow filter forwarding only verification emails (`("verification code" OR "security code" OR "magic link" OR "OTP")`).
5. Sentry Relay's Stage 2 unwrapper strips `---------- Forwarded message ---------` / Outlook headers to recover `originalSender` and `originalSubject`, so `GET /api/v1/identities/{id}/wait?sender=stripe.com` still works seamlessly.

## 2. Multi-Client Isolation & The Human-Fallback Safety Bridge™

Provision each client with an isolated Identity, optional dedicated US carrier Telnyx DID, and Human-Fallback targets (so non-OTP texts like bank fraud alerts or inbound verification voice calls reach the client founder instead of disappearing into API logs):

```typescript
import { SentryRelay } from '@sentryrelay/sdk';

const adminRelay = new SentryRelay({ apiKey: process.env.SENTRY_RELAY_API_KEY! });

const clientIdentity = await adminRelay.identities.create({
  name: 'Client Acme — ERP & Banking Bot',
  slug: 'client-acme',
  emailHandle: 'client-acme',
  fallback: {
    enabled: true,
    fallbackEmail: 'founder@acme-client.com',
    fallbackWebhookUrl: 'https://hooks.slack.com/services/T000/B000/X000',
    voiceForwardToE164: '+14155550199',
  },
});

await adminRelay.identities.provisionSmsDid(clientIdentity.id, { areaCode: '415' });
```

Then issue a **Per-Client Scoped API Key** (`scopedIdentityIds: [clientIdentity.id]`) from the Console (`POST /api/console/keys`). Any attempt by Client Acme's worker to query another client's Identity returns `403 IDENTITY_OUT_OF_SCOPE`.

## 3. n8n & Make Single-Node HTTP Long-Poll

No polling loops needed inside n8n or Make:
- **Method:** `GET`
- **URL:** `https://sentryrelay.com/api/v1/identities/client-acme/wait?sender=stripe.com&timeout=35`
- **Header:** `Authorization: Bearer $ACME_SCOPED_KEY`
- **HTTP Timeout:** `40000` ms
- **Read Token:** `{{$json.data.event.otpCode}}` (or `magicLink`)

For signup/onboarding emails without numeric OTPs, pass `includeNonAuth=true` to receive sanitized `textBody` and `links[]`.
