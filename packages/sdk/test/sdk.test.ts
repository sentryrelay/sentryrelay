import { describe, expect, it, vi } from 'vitest';
import { SentryRelay, SentryRelayApiError } from '../src/index.js';

function generateApiKey(env: 'live' | 'test' = 'live'): { rawKey: string } {
  return { rawKey: `sr_${env}_0123456789ABCDEFabcdef0123456789` };
}

describe('@sentryrelay/sdk', () => {
  it('validates API key format and normalizes baseUrl', () => {
    const { rawKey } = generateApiKey('live');
    const client = new SentryRelay({
      apiKey: rawKey,
      baseUrl: 'https://sentryrelay.com/',
    });

    expect(client.baseUrl).toBe('https://sentryrelay.com');
    expect(client.getAuthHeaders().Authorization).toBe(`Bearer ${rawKey}`);
  });

  it('rejects malformed API keys', () => {
    expect(() => new SentryRelay({ apiKey: 'invalid_key' })).toThrow(/API key must match/);
  });

  it('performs identities CRUD via typed resource', async () => {
    const { rawKey } = generateApiKey('test');

    const mockFetch = vi.fn().mockImplementation(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? 'GET';
      const parsedUrl = new URL(url);

      if (parsedUrl.pathname === '/api/v1/identities' && method === 'GET') {
        return new Response(
          JSON.stringify({
            data: {
              items: [{ id: 'id_123', name: 'Primary Bot', emailHandle: 'bot-1' }],
              nextCursor: null,
            },
            error: null,
          }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        );
      }

      if (parsedUrl.pathname === '/api/v1/identities' && method === 'POST') {
        const body = JSON.parse(init?.body as string);
        return new Response(
          JSON.stringify({
            data: { identity: { id: 'id_456', name: body.name, emailHandle: body.emailHandle } },
            error: null,
          }),
          { status: 201, headers: { 'content-type': 'application/json' } },
        );
      }

      if (parsedUrl.pathname === '/api/v1/identities/id_456' && method === 'GET') {
        return new Response(
          JSON.stringify({
            data: { identity: { id: 'id_456', name: 'Created Bot' } },
            error: null,
          }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        );
      }

      if (parsedUrl.pathname === '/api/v1/identities/id_456' && method === 'PATCH') {
        return new Response(
          JSON.stringify({
            data: { identity: { id: 'id_456', name: 'Updated Bot' } },
            error: null,
          }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        );
      }

      if (parsedUrl.pathname === '/api/v1/identities/id_456' && method === 'DELETE') {
        return new Response(
          JSON.stringify({
            data: { deleted: true, id: 'id_456' },
            error: null,
          }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        );
      }

      return new Response('Not found', { status: 404 });
    });

    const client = new SentryRelay({
      apiKey: rawKey,
      baseUrl: 'http://localhost:3000',
      fetch: mockFetch,
    });

    const listRes = await client.identities.list({ limit: 10 });
    expect(listRes.items).toHaveLength(1);
    expect(listRes.items[0].name).toBe('Primary Bot');

    const created = await client.identities.create({ name: 'New Bot', emailHandle: 'new-bot' });
    expect(created.id).toBe('id_456');

    const fetched = await client.identities.get('id_456');
    expect(fetched.name).toBe('Created Bot');

    const updated = await client.identities.update('id_456', { name: 'Updated Bot' });
    expect(updated.name).toBe('Updated Bot');

    const deleted = await client.identities.delete('id_456');
    expect(deleted.deleted).toBe(true);
  });

  it('performs /wait and /latest queries and top-level aliases', async () => {
    const { rawKey } = generateApiKey('live');

    const mockFetch = vi.fn().mockImplementation(async (url: string) => {
      const parsedUrl = new URL(url);

      if (parsedUrl.pathname === '/api/v1/identities/checkout-bot/wait') {
        expect(parsedUrl.searchParams.get('sender')).toBe('stripe.com');
        return new Response(
          JSON.stringify({
            data: {
              matched: true,
              timedOut: false,
              event: {
                id: 'evt_999',
                identityId: 'id_123',
                otpCode: '582019',
                magicLink: null,
                sender: 'auth@stripe.com',
                channel: 'email',
                receivedAt: new Date().toISOString(),
                waitDurationMs: 85,
              },
              waitDurationMs: 85,
            },
            error: null,
          }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        );
      }

      if (parsedUrl.pathname === '/api/v1/identities/checkout-bot/latest') {
        return new Response(
          JSON.stringify({
            data: {
              matched: true,
              timedOut: false,
              event: {
                id: 'evt_998',
                identityId: 'id_123',
                otpCode: '123456',
                magicLink: null,
                sender: 'auth@github.com',
                channel: 'sms',
                receivedAt: new Date().toISOString(),
                waitDurationMs: 12,
              },
              waitDurationMs: 12,
            },
            error: null,
          }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        );
      }

      return new Response('Not found', { status: 404 });
    });

    const client = new SentryRelay({
      apiKey: rawKey,
      baseUrl: 'http://localhost:3000',
      fetch: mockFetch,
    });

    const waitRes = await client.wait('checkout-bot', { sender: 'stripe.com', timeout: 25 });
    expect(waitRes.matched).toBe(true);
    expect(waitRes.event?.otpCode).toBe('582019');

    const latestRes = await client.latest('checkout-bot');
    expect(latestRes.matched).toBe(true);
    expect(latestRes.event?.otpCode).toBe('123456');
  });

  it('handles TOTP code generation with autoWaitFreshWindow rollover wait', async () => {
    const { rawKey } = generateApiKey('live');

    let callCount = 0;
    const mockSleep = vi.fn().mockResolvedValue(undefined);

    const mockFetch = vi.fn().mockImplementation(async (url: string) => {
      callCount++;
      if (callCount === 1) {
        // First call has remainingSeconds = 2 (< 4s), so it triggers rollover sleep
        return new Response(
          JSON.stringify({
            data: {
              code: '111111',
              remainingSeconds: 2,
              nextCode: '222222',
              period: 30,
              digits: 6,
              algorithm: 'SHA1',
            },
            error: null,
          }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        );
      } else {
        // Second call returns fresh code with 30s remaining
        return new Response(
          JSON.stringify({
            data: {
              code: '222222',
              remainingSeconds: 30,
              period: 30,
              digits: 6,
              algorithm: 'SHA1',
            },
            error: null,
          }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        );
      }
    });

    const client = new SentryRelay({
      apiKey: rawKey,
      baseUrl: 'http://localhost:3000',
      fetch: mockFetch,
      sleepFn: mockSleep,
    });

    const code = await client.totp.get('checkout-bot', 'github_ops');
    expect(mockSleep).toHaveBeenCalledWith(2200); // 2s * 1000 + 200ms
    expect(code.code).toBe('222222');
    expect(code.remainingSeconds).toBe(30);
  });

  it('bypasses autoWaitFreshWindow when autoWaitFreshWindow: false', async () => {
    const { rawKey } = generateApiKey('live');
    const mockSleep = vi.fn().mockResolvedValue(undefined);

    const mockFetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            code: '999888',
            remainingSeconds: 1,
            nextCode: '000111',
            period: 30,
            digits: 6,
            algorithm: 'SHA1',
          },
          error: null,
        }),
        { status: 200, headers: { 'content-type': 'application/json' } },
      ),
    );

    const client = new SentryRelay({
      apiKey: rawKey,
      baseUrl: 'http://localhost:3000',
      fetch: mockFetch,
      sleepFn: mockSleep,
    });

    const code = await client.totp.get('checkout-bot', 'github_ops', {
      autoWaitFreshWindow: false,
    });
    expect(mockSleep).not.toHaveBeenCalled();
    expect(code.code).toBe('999888');
    expect(code.remainingSeconds).toBe(1);
  });

  it('retries transient 5xx errors with exponential backoff on GET requests', async () => {
    const { rawKey } = generateApiKey('live');
    let attempts = 0;
    const mockSleep = vi.fn().mockResolvedValue(undefined);

    const mockFetch = vi.fn().mockImplementation(async () => {
      attempts++;
      if (attempts === 1) {
        return new Response(
          JSON.stringify({ error: { code: 'INTERNAL_ERROR', message: 'Temporary failure' } }),
          {
            status: 500,
            headers: { 'content-type': 'application/json' },
          },
        );
      }
      return new Response(
        JSON.stringify({
          data: { items: [{ id: 'id_1' }] },
          error: null,
        }),
        { status: 200, headers: { 'content-type': 'application/json' } },
      );
    });

    const client = new SentryRelay({
      apiKey: rawKey,
      baseUrl: 'http://localhost:3000',
      fetch: mockFetch,
      sleepFn: mockSleep,
      retryDelayMs: 50,
    });

    const res = await client.identities.list();
    expect(attempts).toBe(2);
    expect(mockSleep).toHaveBeenCalledTimes(1);
    expect(res.items).toHaveLength(1);
  });

  it('does not retry 4xx client errors and throws SentryRelayApiError', async () => {
    const { rawKey } = generateApiKey('live');
    const mockFetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: { code: 'NOT_FOUND', message: 'Identity not found' },
          data: null,
        }),
        { status: 404, headers: { 'content-type': 'application/json' } },
      ),
    );

    const client = new SentryRelay({
      apiKey: rawKey,
      baseUrl: 'http://localhost:3000',
      fetch: mockFetch,
    });

    await expect(client.identities.get('missing-bot')).rejects.toThrowError(SentryRelayApiError);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it('queries audit logs and webhooks', async () => {
    const { rawKey } = generateApiKey('live');
    const mockFetch = vi.fn().mockImplementation(async (url: string) => {
      const parsedUrl = new URL(url);
      if (parsedUrl.pathname === '/api/v1/audit-logs') {
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  id: 'log_1',
                  eventType: 'otp.extracted',
                  actor: { type: 'api_key', id: 'key_1' },
                },
              ],
            },
            error: null,
          }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        );
      }
      if (parsedUrl.pathname === '/api/v1/webhooks') {
        return new Response(
          JSON.stringify({
            data: {
              items: [
                { id: 'wh_1', targetUrl: 'https://example.com/wh', events: ['otp.extracted'] },
              ],
            },
            error: null,
          }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        );
      }
      return new Response('Not found', { status: 404 });
    });

    const client = new SentryRelay({
      apiKey: rawKey,
      baseUrl: 'http://localhost:3000',
      fetch: mockFetch,
    });

    const logs = await client.auditLogs.list({ identityId: 'id_1' });
    expect(logs).toHaveLength(1);
    expect(logs[0].eventType).toBe('otp.extracted');

    const webhooks = await client.webhooks.list();
    expect(webhooks).toHaveLength(1);
    expect(webhooks[0].targetUrl).toBe('https://example.com/wh');
  });
});
