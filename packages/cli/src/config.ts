import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import {
  isValidApiKeyFormat,
  PRIMARY_DOMAIN,
  SentryRelay,
  SentryRelayApiError,
} from '@sentryrelay/sdk';

export interface CliCredentials {
  apiKey: string;
  baseUrl?: string;
  savedAt: string;
}

export function getDefaultConfigDir(): string {
  return path.join(os.homedir(), '.config', 'sentryrelay');
}

export function getCredentialsFilePath(): string {
  if (process.env.SENTRY_RELAY_CONFIG_PATH) {
    return process.env.SENTRY_RELAY_CONFIG_PATH;
  }
  return path.join(getDefaultConfigDir(), 'credentials.json');
}

/**
 * Saves Sentry Relay credentials securely with 0600 file permissions.
 */
export function saveCredentials(creds: { apiKey: string; baseUrl?: string }): string {
  if (!isValidApiKeyFormat(creds.apiKey)) {
    throw new SentryRelayApiError(
      'INVALID_API_KEY',
      'API key must match sr_live_<32_base62> or sr_test_<32_base62>',
    );
  }

  const filePath = getCredentialsFilePath();
  const dirPath = path.dirname(filePath);

  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true, mode: 0o700 });
  }

  const payload: CliCredentials = {
    apiKey: creds.apiKey,
    baseUrl: creds.baseUrl,
    savedAt: new Date().toISOString(),
  };

  fs.writeFileSync(filePath, JSON.stringify(payload, null, 2), {
    mode: 0o600,
  });

  try {
    fs.chmodSync(filePath, 0o600);
  } catch {
    // Best effort on platforms with limited chmod support
  }

  return filePath;
}

/**
 * Reads credentials from credentials.json if it exists.
 */
export function loadCredentials(): CliCredentials | null {
  const filePath = getCredentialsFilePath();
  if (!fs.existsSync(filePath)) {
    return null;
  }

  try {
    const raw = fs.readFileSync(filePath, 'utf-8');
    const parsed = JSON.parse(raw) as CliCredentials;
    if (parsed && typeof parsed.apiKey === 'string') {
      return parsed;
    }
  } catch {
    return null;
  }
  return null;
}

/**
 * Deletes credentials.json on logout.
 */
export function clearCredentials(): boolean {
  const filePath = getCredentialsFilePath();
  if (fs.existsSync(filePath)) {
    fs.unlinkSync(filePath);
    return true;
  }
  return false;
}

/**
 * Resolves SentryRelay client instance checking options, env vars, and saved config.
 */
export function resolveClient(options?: {
  key?: string;
  url?: string;
  fetch?: typeof fetch;
}): SentryRelay {
  const saved = loadCredentials();
  const apiKey = options?.key ?? process.env.SENTRY_RELAY_API_KEY ?? saved?.apiKey;

  if (!apiKey) {
    throw new SentryRelayApiError(
      'UNAUTHORIZED',
      'Not authenticated. Run "srelay login" or pass --key / set SENTRY_RELAY_API_KEY.',
    );
  }

  const baseUrl =
    options?.url ??
    process.env.SENTRY_RELAY_BASE_URL ??
    saved?.baseUrl ??
    `https://${PRIMARY_DOMAIN}`;

  return new SentryRelay({
    apiKey,
    baseUrl,
    fetch: options?.fetch,
  });
}

/**
 * Masks an API key for safe terminal display (e.g. sr_live_...4812).
 */
export function maskApiKey(apiKey: string): string {
  if (apiKey.length < 12) return '***';
  const prefix = apiKey.slice(0, 8);
  const suffix = apiKey.slice(-4);
  return `${prefix}${'*'.repeat(Math.max(4, apiKey.length - 12))}${suffix}`;
}
