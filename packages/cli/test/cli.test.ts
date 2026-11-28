import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { buildCliProgram, CLI_VERSION, getCliBanner } from '../src/index.js';

function generateApiKey(env: 'live' | 'test' = 'live'): { rawKey: string } {
  return { rawKey: `sr_${env}_0123456789ABCDEFabcdef0123456789` };
}

describe('srelay CLI', () => {
  let tmpConfigDir: string;
  let tmpConfigFile: string;

  beforeEach(() => {
    tmpConfigDir = fs.mkdtempSync(path.join(os.tmpdir(), 'srelay-test-'));
    tmpConfigFile = path.join(tmpConfigDir, 'credentials.json');
    process.env.SENTRY_RELAY_CONFIG_PATH = tmpConfigFile;
  });

  afterEach(() => {
    delete process.env.SENTRY_RELAY_CONFIG_PATH;
    try {
      fs.rmSync(tmpConfigDir, { recursive: true, force: true });
    } catch {
      // Ignore cleanup error
    }
  });

  it('exposes the srelay binary banner', () => {
    expect(getCliBanner()).toBe(`Sentry Relay CLI (srelay) v${CLI_VERSION}`);
  });

  it('saves credentials with mode 0600 on login and deletes them on logout', async () => {
    const { rawKey } = generateApiKey('live');

    let outText = '';
    const outStream = {
      write: (str: string) => {
        outText += str;
        return true;
      },
    };
    const errStream = { write: vi.fn() };

    const program = buildCliProgram({ stdout: outStream, stderr: errStream });
    await program.parseAsync([
      'node',
      'srelay',
      'login',
      '--key',
      rawKey,
      '--url',
      'https://sentryrelay.com',
    ]);

    expect(fs.existsSync(tmpConfigFile)).toBe(true);
    const stat = fs.statSync(tmpConfigFile);
    // Mode should have owner read/write (0600)
    expect(stat.mode & 0o777).toBe(0o600);
    expect(outText).toContain('Successfully authenticated');

    // Test logout
    outText = '';
    const logoutProgram = buildCliProgram({ stdout: outStream, stderr: errStream });
    await logoutProgram.parseAsync(['node', 'srelay', 'logout']);
    expect(fs.existsSync(tmpConfigFile)).toBe(false);
    expect(outText).toContain('Logged out');
  });

  it('runs whoami showing masked key', async () => {
    const { rawKey } = generateApiKey('live');
    fs.writeFileSync(
      tmpConfigFile,
      JSON.stringify({ apiKey: rawKey, baseUrl: 'https://sentryrelay.com' }),
      { mode: 0o600 },
    );

    let outText = '';
    const outStream = {
      write: (str: string) => {
        outText += str;
        return true;
      },
    };
    const program = buildCliProgram({ stdout: outStream });
    await program.parseAsync(['node', 'srelay', 'whoami']);

    expect(outText).toContain('Sentry Relay Configuration:');
    expect(outText).toContain('sr_live_');
    expect(outText).toContain('https://sentryrelay.com');
  });

  it('pipes raw OTP code on stdout when srelay wait --raw is passed', async () => {
    const { rawKey } = generateApiKey('live');

    const mockFetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            matched: true,
            timedOut: false,
            event: {
              id: 'evt_100',
              otpCode: '849201',
              channel: 'email',
              sender: 'noreply@github.com',
            },
            waitDurationMs: 120,
          },
          error: null,
        }),
        { status: 200, headers: { 'content-type': 'application/json' } },
      ),
    );

    let outText = '';
    const outStream = {
      write: (str: string) => {
        outText += str;
        return true;
      },
    };
    const program = buildCliProgram({ stdout: outStream, fetch: mockFetch });

    await program.parseAsync(['node', 'srelay', 'wait', 'github-bot', '--key', rawKey, '--raw']);

    // --raw mode must output ONLY the OTP code plus newline
    expect(outText).toBe('849201\n');
  });

  it('pipes raw TOTP code on stdout when srelay totp get --raw is passed', async () => {
    const { rawKey } = generateApiKey('live');

    const mockFetch = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            code: '654321',
            remainingSeconds: 25,
            period: 30,
            digits: 6,
            algorithm: 'SHA1',
          },
          error: null,
        }),
        { status: 200, headers: { 'content-type': 'application/json' } },
      ),
    );

    let outText = '';
    const outStream = {
      write: (str: string) => {
        outText += str;
        return true;
      },
    };
    const program = buildCliProgram({ stdout: outStream, fetch: mockFetch });

    await program.parseAsync([
      'node',
      'srelay',
      'totp',
      'get',
      'github-bot',
      'gh_ops',
      '--key',
      rawKey,
      '--raw',
    ]);

    // --raw mode must output ONLY the 6-digit code plus newline
    expect(outText).toBe('654321\n');
  });

  it('handles identities list and create commands', async () => {
    const { rawKey } = generateApiKey('live');

    const mockFetch = vi.fn().mockImplementation(async (url: string, init?: RequestInit) => {
      const parsedUrl = new URL(url);
      if (parsedUrl.pathname === '/api/v1/identities' && (!init?.method || init.method === 'GET')) {
        return new Response(
          JSON.stringify({
            data: {
              items: [
                {
                  id: 'id_1',
                  name: 'Worker Alpha',
                  emailAddress: 'alpha@sentryrelay.com',
                  smsPhoneNumber: '+12065550100',
                },
              ],
              nextCursor: null,
            },
            error: null,
          }),
          { status: 200, headers: { 'content-type': 'application/json' } },
        );
      }
      if (parsedUrl.pathname === '/api/v1/identities' && init?.method === 'POST') {
        return new Response(
          JSON.stringify({
            data: {
              identity: {
                id: 'id_2',
                name: 'Worker Beta',
                emailAddress: 'beta@sentryrelay.com',
              },
            },
            error: null,
          }),
          { status: 201, headers: { 'content-type': 'application/json' } },
        );
      }
      return new Response('Not found', { status: 404 });
    });

    let outText = '';
    const outStream = {
      write: (str: string) => {
        outText += str;
        return true;
      },
    };

    const listProgram = buildCliProgram({ stdout: outStream, fetch: mockFetch });
    await listProgram.parseAsync(['node', 'srelay', 'identities', 'list', '--key', rawKey]);
    expect(outText).toContain('Worker Alpha');
    expect(outText).toContain('+12065550100');

    outText = '';
    const createProgram = buildCliProgram({ stdout: outStream, fetch: mockFetch });
    await createProgram.parseAsync([
      'node',
      'srelay',
      'identities',
      'create',
      'Worker Beta',
      '--key',
      rawKey,
    ]);
    expect(outText).toContain('Identity created successfully');
    expect(outText).toContain('beta@sentryrelay.com');
  });
});
