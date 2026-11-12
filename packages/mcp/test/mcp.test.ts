import { describe, expect, it, vi } from 'vitest';
import { SentryRelay } from '@sentryrelay/sdk';

function generateApiKey(env: 'live' | 'test' = 'live'): { rawKey: string } {
  return { rawKey: `sr_${env}_0123456789ABCDEFabcdef0123456789` };
}
import {
  createSentryRelayMcpServer,
  dispatchMcpJsonRpc,
  executeMcpTool,
  MCP_TOOL_DEFINITIONS,
  SENTRY_RELAY_MCP_TOOLS,
} from '../src/index.js';

describe('@sentryrelay/mcp tool registry & execution', () => {
  it('registers all 6 canonical MCP tools with input schemas', () => {
    expect(SENTRY_RELAY_MCP_TOOLS).toHaveLength(6);
    expect(MCP_TOOL_DEFINITIONS.map((t) => t.name)).toEqual(SENTRY_RELAY_MCP_TOOLS);

    for (const tool of MCP_TOOL_DEFINITIONS) {
      expect(tool.description).toBeTruthy();
      expect(tool.inputSchema.type).toBe('object');
      expect(tool.inputSchema.properties).toBeDefined();
    }
  });

  it('executes wait_for_verification_code successfully', async () => {
    const { rawKey } = generateApiKey('live');
    const mockWait = vi.fn().mockResolvedValue({
      matched: true,
      timedOut: false,
      event: {
        id: 'evt_1',
        otpCode: '123456',
        channel: 'email',
        sender: 'security@stripe.com',
      },
      waitDurationMs: 45,
    });

    const mockClient = {
      identities: { wait: mockWait },
    } as unknown as SentryRelay;

    const res = await executeMcpTool(mockClient, 'wait_for_verification_code', {
      identity: 'stripe-agent',
      sender: 'stripe.com',
      timeoutSeconds: 20,
    });

    expect(res.isError).toBeFalsy();
    expect(mockWait).toHaveBeenCalledWith('stripe-agent', {
      channel: undefined,
      sender: 'stripe.com',
      subject: undefined,
      timeout: 20,
      since: undefined,
    });
    const parsed = JSON.parse(res.content[0].text);
    expect(parsed.matched).toBe(true);
    expect(parsed.event.otpCode).toBe('123456');
  });

  it('executes get_latest_verification_code successfully', async () => {
    const mockLatest = vi.fn().mockResolvedValue({
      matched: true,
      timedOut: false,
      event: {
        id: 'evt_2',
        otpCode: '654321',
        channel: 'sms',
      },
      waitDurationMs: 10,
    });

    const mockClient = {
      identities: { latest: mockLatest },
    } as unknown as SentryRelay;

    const res = await executeMcpTool(mockClient, 'get_latest_verification_code', {
      identity: 'sms-agent',
      lookbackSeconds: 30,
      consume: true,
    });

    expect(res.isError).toBeFalsy();
    const parsed = JSON.parse(res.content[0].text);
    expect(parsed.event.otpCode).toBe('654321');
  });

  it('executes get_totp_code with autoWaitFreshWindow', async () => {
    const mockTotpGet = vi.fn().mockResolvedValue({
      code: '888999',
      remainingSeconds: 28,
      period: 30,
      digits: 6,
      algorithm: 'SHA1',
    });

    const mockClient = {
      totp: { get: mockTotpGet },
    } as unknown as SentryRelay;

    const res = await executeMcpTool(mockClient, 'get_totp_code', {
      identity: 'bot-1',
      secretId: 'github_ops',
      autoWaitFreshWindow: true,
    });

    expect(res.isError).toBeFalsy();
    expect(mockTotpGet).toHaveBeenCalledWith('bot-1', 'github_ops', {
      autoWaitFreshWindow: true,
    });
    const parsed = JSON.parse(res.content[0].text);
    expect(parsed.code).toBe('888999');
  });

  it('executes list_identities with search filter', async () => {
    const mockList = vi.fn().mockResolvedValue({
      items: [
        { id: 'id_1', name: 'Alpha Bot', emailHandle: 'alpha' },
        { id: 'id_2', name: 'Beta Bot', emailHandle: 'beta' },
      ],
      nextCursor: null,
    });

    const mockClient = {
      identities: { list: mockList },
    } as unknown as SentryRelay;

    const res = await executeMcpTool(mockClient, 'list_identities', {
      search: 'beta',
    });

    expect(res.isError).toBeFalsy();
    const parsed = JSON.parse(res.content[0].text);
    expect(parsed.items).toHaveLength(1);
    expect(parsed.items[0].name).toBe('Beta Bot');
  });

  it('executes create_identity', async () => {
    const mockCreate = vi.fn().mockResolvedValue({
      id: 'id_new',
      name: 'Gamma Bot',
      emailHandle: 'gamma',
    });

    const mockClient = {
      identities: { create: mockCreate },
    } as unknown as SentryRelay;

    const res = await executeMcpTool(mockClient, 'create_identity', {
      name: 'Gamma Bot',
      emailHandle: 'gamma',
      fallbackEmail: 'alerts@example.com',
    });

    expect(res.isError).toBeFalsy();
    expect(mockCreate).toHaveBeenCalledWith({
      name: 'Gamma Bot',
      emailHandle: 'gamma',
      fallback: {
        enabled: true,
        fallbackEmail: 'alerts@example.com',
      },
    });
    const parsed = JSON.parse(res.content[0].text);
    expect(parsed.identity.id).toBe('id_new');
  });

  it('executes store_totp_secret from uri and raw secret', async () => {
    const mockTotpCreate = vi.fn().mockResolvedValue({
      id: 'vault_sec',
      issuer: 'GitHub',
      accountLabel: 'ops',
    });

    const mockClient = {
      totp: { create: mockTotpCreate },
    } as unknown as SentryRelay;

    // URI mode
    await executeMcpTool(mockClient, 'store_totp_secret', {
      identity: 'bot-1',
      secretId: 'gh_sec',
      otpauthUriOrSecret: 'otpauth://totp/GitHub:ops?secret=JBSWY3DPEHPK3PXP',
    });

    expect(mockTotpCreate).toHaveBeenCalledWith('bot-1', {
      id: 'gh_sec',
      otpauthUri: 'otpauth://totp/GitHub:ops?secret=JBSWY3DPEHPK3PXP',
    });

    // Raw Base32 mode
    await executeMcpTool(mockClient, 'store_totp_secret', {
      identity: 'bot-1',
      secretId: 'gh_manual',
      otpauthUriOrSecret: 'JBSWY3DPEHPK3PXP',
      issuer: 'GitHub',
    });

    expect(mockTotpCreate).toHaveBeenCalledWith('bot-1', {
      id: 'gh_manual',
      secret: 'JBSWY3DPEHPK3PXP',
      issuer: 'GitHub',
      accountLabel: 'gh_manual',
    });
  });

  it('returns clean error payload on missing parameters or exceptions', async () => {
    const mockClient = {} as unknown as SentryRelay;
    const res = await executeMcpTool(mockClient, 'wait_for_verification_code', {});
    expect(res.isError).toBe(true);
    expect(res.content[0].text).toContain('Error [VALIDATION_ERROR]');
  });

  it('handles JSON-RPC protocol messages via dispatchMcpJsonRpc', async () => {
    const { rawKey } = generateApiKey('live');
    const mockClient = {
      identities: {
        wait: vi.fn().mockResolvedValue({
          matched: true,
          timedOut: false,
          event: { otpCode: '445566' },
        }),
      },
    } as unknown as SentryRelay;

    // 1. initialize
    const initRes = await dispatchMcpJsonRpc(
      { jsonrpc: '2.0', id: 1, method: 'initialize', params: {} },
      mockClient,
    );
    expect(initRes).toMatchObject({
      jsonrpc: '2.0',
      id: 1,
      result: {
        serverInfo: { name: 'sentry-relay-mcp' },
      },
    });

    // 2. tools/list
    const listRes = await dispatchMcpJsonRpc(
      { jsonrpc: '2.0', id: 2, method: 'tools/list' },
      mockClient,
    );
    expect(listRes).toMatchObject({
      jsonrpc: '2.0',
      id: 2,
      result: {
        tools: expect.arrayContaining([
          expect.objectContaining({ name: 'wait_for_verification_code' }),
        ]),
      },
    });

    // 3. tools/call
    const callRes = await dispatchMcpJsonRpc(
      {
        jsonrpc: '2.0',
        id: 3,
        method: 'tools/call',
        params: {
          name: 'wait_for_verification_code',
          arguments: { identity: 'checkout-bot' },
        },
      },
      mockClient,
    );
    expect(callRes).toMatchObject({
      jsonrpc: '2.0',
      id: 3,
      result: {
        content: [{ type: 'text', text: expect.stringContaining('445566') }],
      },
    });

    // 4. notifications (no response)
    const notifRes = await dispatchMcpJsonRpc(
      { jsonrpc: '2.0', method: 'notifications/initialized' },
      mockClient,
    );
    expect(notifRes).toBeNull();
  });

  it('creates an MCP Server instance via createSentryRelayMcpServer', () => {
    const { rawKey } = generateApiKey('live');
    const client = new SentryRelay({ apiKey: rawKey });
    const server = createSentryRelayMcpServer({ client });
    expect(server).toBeDefined();
  });
});
