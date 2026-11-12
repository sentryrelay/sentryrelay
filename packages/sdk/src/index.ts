import {
  PRIMARY_DOMAIN,
  SentryRelayApiError,
  isValidApiKeyFormat,
  type AuditLogDocument,
  type AuditLogQueryInput,
  type CreateIdentityRequestInput,
  type CreateTotpSecretRequestInput,
  type CreateWebhookRequestInput,
  type GeneratedTotpCode,
  type IdentityDocument,
  type LatestQueryInput,
  type OutboundWebhookDocument,
  type ProvisionSmsDidRequestInput,
  type TotpSecretMetadata,
  type UpdateIdentityRequestInput,
  type WaitQueryInput,
} from './types.js';

export * from './types.js';

export type WaitOptions = Partial<WaitQueryInput>;
export type LatestOptions = Partial<LatestQueryInput>;

export interface WaitResponseData {
  matched: boolean;
  timedOut: boolean;
  event: {
    id: string;
    identityId: string;
    workspaceId: string;
    channel: 'email' | 'sms';
    classification: string;
    otpCode: string | null;
    magicLink: string | null;
    sender: string;
    subject: string | null;
    matchedRule: string | null;
    confidence: number;
    receivedAtMs: number;
    receivedAtIso: string;
    receivedAt: string;
    consumed: boolean;
    consumedAtMs?: number;
    textBody?: string | null;
    htmlBody?: string | null;
    links?: Array<{ text: string; href: string }>;
    expiresAtMs?: number;
    waitDurationMs: number;
  } | null;
  waitDurationMs: number;
}

export interface LatestResponseData extends WaitResponseData {}

export interface SentryRelayClientOptions {
  apiKey: string;
  baseUrl?: string;
  maxRetries?: number;
  retryDelayMs?: number;
  fetch?: typeof fetch;
  sleepFn?: (ms: number) => Promise<void>;
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  path: string;
  query?: Record<string, string | number | boolean | undefined | null>;
  body?: unknown;
  headers?: Record<string, string>;
  skipRetry?: boolean;
}

const DEFAULT_MAX_RETRIES = 2;
const DEFAULT_RETRY_DELAY_MS = 150;

/**
 * Official Sentry Relay TypeScript SDK.
 * Zero-dependency fetch-based client for autonomous agents, tests, and backends.
 */
export class SentryRelay {
  public readonly baseUrl: string;
  public readonly maxRetries: number;
  public readonly retryDelayMs: number;
  private readonly apiKey: string;
  private readonly customFetch: typeof fetch;
  private readonly sleepFn: (ms: number) => Promise<void>;

  public readonly identities: IdentitiesResource;
  public readonly totp: TotpResource;
  public readonly webhooks: WebhooksResource;
  public readonly auditLogs: AuditLogsResource;

  constructor(options: SentryRelayClientOptions) {
    if (!isValidApiKeyFormat(options.apiKey)) {
      throw new SentryRelayApiError(
        'INVALID_API_KEY',
        'API key must match sr_live_<32_base62> or sr_test_<32_base62>',
      );
    }
    this.apiKey = options.apiKey;
    this.baseUrl = (options.baseUrl ?? `https://${PRIMARY_DOMAIN}`).replace(/\/+$/, '');
    this.maxRetries = options.maxRetries ?? DEFAULT_MAX_RETRIES;
    this.retryDelayMs = options.retryDelayMs ?? DEFAULT_RETRY_DELAY_MS;
    this.customFetch = options.fetch ?? globalThis.fetch;
    this.sleepFn =
      options.sleepFn ?? ((ms: number) => new Promise((resolve) => setTimeout(resolve, ms)));

    this.identities = new IdentitiesResource(this);
    this.totp = new TotpResource(this);
    this.webhooks = new WebhooksResource(this);
    this.auditLogs = new AuditLogsResource(this);
  }

  public getAuthHeaders(): Record<string, string> {
    return {
      Authorization: `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
  }

  /**
   * Internal sleep helper.
   */
  public async sleep(ms: number): Promise<void> {
    await this.sleepFn(ms);
  }

  /**
   * Low-level fetch wrapper with automatic exponential backoff for transient errors.
   */
  public async request<T>(options: RequestOptions): Promise<T> {
    const url = new URL(`${this.baseUrl}${options.path}`);
    if (options.query) {
      for (const [key, val] of Object.entries(options.query)) {
        if (val !== undefined && val !== null) {
          url.searchParams.set(key, String(val));
        }
      }
    }

    const method = options.method ?? 'GET';
    const headers: Record<string, string> = {
      ...this.getAuthHeaders(),
      ...(options.headers ?? {}),
    };

    const isMutating = method !== 'GET';
    const effectiveMaxRetries = options.skipRetry ? 0 : this.maxRetries;

    let attempt = 0;
    while (true) {
      try {
        const response = await this.customFetch(url.toString(), {
          method,
          headers,
          body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
        });

        const contentType = response.headers.get('content-type') ?? '';
        const isJson = contentType.includes('application/json');

        if (response.ok) {
          if (isJson) {
            const envelope = (await response.json()) as {
              data?: T;
              error?: { code: string; message: string; details?: unknown };
            };
            if (envelope && typeof envelope === 'object' && 'data' in envelope) {
              return envelope.data as T;
            }
            return envelope as unknown as T;
          }
          return (await response.text()) as unknown as T;
        }

        // Handle error status
        let errorCode = 'INTERNAL_ERROR';
        let errorMessage = `HTTP ${response.status} ${response.statusText}`;
        let errorDetails: unknown = undefined;

        if (isJson) {
          try {
            const errorPayload = (await response.json()) as {
              error?: { code?: string; message?: string; details?: unknown };
            };
            if (errorPayload?.error) {
              errorCode = errorPayload.error.code ?? errorCode;
              errorMessage = errorPayload.error.message ?? errorMessage;
              errorDetails = errorPayload.error.details;
            }
          } catch {
            // Keep default message
          }
        }

        const isTransientStatus = response.status >= 500 || response.status === 429;
        const canRetry = !isMutating && isTransientStatus && attempt < effectiveMaxRetries;

        if (canRetry) {
          attempt++;
          const delay = Math.min(
            1000,
            this.retryDelayMs * Math.pow(2, attempt) + Math.random() * 20,
          );
          await this.sleep(delay);
          continue;
        }

        throw new SentryRelayApiError(errorCode as any, errorMessage, {
          details: errorDetails as Record<string, unknown> | undefined,
        });
      } catch (err) {
        if (err instanceof SentryRelayApiError) {
          throw err;
        }

        const isNetworkError =
          err instanceof Error &&
          (err.name === 'TypeError' || err.name === 'FetchError' || err.message.includes('fetch'));
        const canRetry = (!isMutating || isNetworkError) && attempt < effectiveMaxRetries;

        if (canRetry) {
          attempt++;
          const delay = Math.min(
            1000,
            this.retryDelayMs * Math.pow(2, attempt) + Math.random() * 20,
          );
          await this.sleep(delay);
          continue;
        }

        throw new SentryRelayApiError(
          'INTERNAL_ERROR',
          err instanceof Error
            ? err.message
            : 'Unknown network failure during Sentry Relay request',
        );
      }
    }
  }

  // Top-level aliases for convenient ergonomics
  public async wait(idOrSlug: string, options?: WaitOptions): Promise<WaitResponseData> {
    return this.identities.wait(idOrSlug, options);
  }

  public async latest(idOrSlug: string, options?: LatestOptions): Promise<LatestResponseData> {
    return this.identities.latest(idOrSlug, options);
  }
}

/**
 * Identities API resource.
 */
export class IdentitiesResource {
  constructor(private readonly client: SentryRelay) {}

  public async list(params?: {
    limit?: number;
    cursor?: string;
  }): Promise<{ items: IdentityDocument[]; nextCursor: string | null }> {
    return this.client.request<{ items: IdentityDocument[]; nextCursor: string | null }>({
      method: 'GET',
      path: '/api/v1/identities',
      query: {
        limit: params?.limit,
        cursor: params?.cursor,
      },
    });
  }

  public async get(idOrSlug: string): Promise<IdentityDocument> {
    const res = await this.client.request<{ identity: IdentityDocument }>({
      method: 'GET',
      path: `/api/v1/identities/${encodeURIComponent(idOrSlug)}`,
    });
    return res.identity;
  }

  public async create(input: CreateIdentityRequestInput): Promise<IdentityDocument> {
    const res = await this.client.request<{ identity: IdentityDocument }>({
      method: 'POST',
      path: '/api/v1/identities',
      body: input,
    });
    return res.identity;
  }

  public async update(
    idOrSlug: string,
    input: UpdateIdentityRequestInput,
  ): Promise<IdentityDocument> {
    const res = await this.client.request<{ identity: IdentityDocument }>({
      method: 'PATCH',
      path: `/api/v1/identities/${encodeURIComponent(idOrSlug)}`,
      body: input,
    });
    return res.identity;
  }

  public async delete(idOrSlug: string): Promise<{ deleted: boolean; id: string }> {
    return this.client.request<{ deleted: boolean; id: string }>({
      method: 'DELETE',
      path: `/api/v1/identities/${encodeURIComponent(idOrSlug)}`,
    });
  }

  public async wait(idOrSlug: string, options?: WaitOptions): Promise<WaitResponseData> {
    return this.client.request<WaitResponseData>({
      method: 'GET',
      path: `/api/v1/identities/${encodeURIComponent(idOrSlug)}/wait`,
      query: {
        timeout: options?.timeout,
        since: options?.since,
        channel: options?.channel,
        sender: options?.sender,
        subject: options?.subject,
        consume: options?.consume,
        includeNonAuth: options?.includeNonAuth,
      },
    });
  }

  public async latest(idOrSlug: string, options?: LatestOptions): Promise<LatestResponseData> {
    return this.client.request<LatestResponseData>({
      method: 'GET',
      path: `/api/v1/identities/${encodeURIComponent(idOrSlug)}/latest`,
      query: {
        lookbackSeconds: options?.lookbackSeconds,
        since: options?.since,
        channel: options?.channel,
        sender: options?.sender,
        subject: options?.subject,
        consume: options?.consume,
        includeNonAuth: options?.includeNonAuth,
      },
    });
  }

  public async provisionSmsDid(
    idOrSlug: string,
    input?: ProvisionSmsDidRequestInput,
  ): Promise<{ identity: IdentityDocument; phoneNumber: string; telnyxPhoneNumberId: string }> {
    return this.client.request<{
      identity: IdentityDocument;
      phoneNumber: string;
      telnyxPhoneNumberId: string;
    }>({
      method: 'POST',
      path: `/api/v1/identities/${encodeURIComponent(idOrSlug)}/sms/provision`,
      body: input ?? {},
    });
  }

  public async releaseSmsDid(
    idOrSlug: string,
  ): Promise<{ released: boolean; phoneNumber: string; identityId: string }> {
    return this.client.request<{
      released: boolean;
      phoneNumber: string;
      identityId: string;
    }>({
      method: 'DELETE',
      path: `/api/v1/identities/${encodeURIComponent(idOrSlug)}/sms`,
    });
  }
}

/**
 * TOTP Authenticator API resource.
 */
export class TotpResource {
  constructor(private readonly client: SentryRelay) {}

  public async list(idOrSlug: string): Promise<TotpSecretMetadata[]> {
    const res = await this.client.request<{ items: TotpSecretMetadata[] }>({
      method: 'GET',
      path: `/api/v1/identities/${encodeURIComponent(idOrSlug)}/totp`,
    });
    return res.items;
  }

  public async create(
    idOrSlug: string,
    input: CreateTotpSecretRequestInput,
  ): Promise<TotpSecretMetadata> {
    const res = await this.client.request<{ secret: TotpSecretMetadata }>({
      method: 'POST',
      path: `/api/v1/identities/${encodeURIComponent(idOrSlug)}/totp`,
      body: input,
    });
    return res.secret;
  }

  /**
   * Generates a live RFC 6238 TOTP code.
   * If autoWaitFreshWindow is true (default) and remainingSeconds < 4,
   * transparently waits for the rollover and fetches a guaranteed fresh code.
   */
  public async get(
    idOrSlug: string,
    secretId: string,
    options?: { autoWaitFreshWindow?: boolean; nowMs?: number },
  ): Promise<GeneratedTotpCode> {
    const autoWait = options?.autoWaitFreshWindow ?? true;

    const initial = await this.client.request<GeneratedTotpCode>({
      method: 'GET',
      path: `/api/v1/identities/${encodeURIComponent(idOrSlug)}/totp/${encodeURIComponent(secretId)}`,
      query: options?.nowMs !== undefined ? { nowMs: options.nowMs } : undefined,
    });

    if (autoWait && initial.remainingSeconds < 4) {
      // Sleep until rollover plus 200ms buffer so next period is active
      const sleepTimeMs = Math.max(100, Math.ceil(initial.remainingSeconds * 1000 + 200));
      await this.client.sleep(sleepTimeMs);

      // Re-fetch fresh code
      const nextNowMs = options?.nowMs !== undefined ? options.nowMs + sleepTimeMs : undefined;
      return this.client.request<GeneratedTotpCode>({
        method: 'GET',
        path: `/api/v1/identities/${encodeURIComponent(idOrSlug)}/totp/${encodeURIComponent(secretId)}`,
        query: nextNowMs !== undefined ? { nowMs: nextNowMs } : undefined,
      });
    }

    return initial;
  }

  public async delete(
    idOrSlug: string,
    secretId: string,
  ): Promise<{ deleted: boolean; secretId: string }> {
    return this.client.request<{ deleted: boolean; secretId: string }>({
      method: 'DELETE',
      path: `/api/v1/identities/${encodeURIComponent(idOrSlug)}/totp/${encodeURIComponent(secretId)}`,
    });
  }
}

/**
 * Outbound User Webhooks resource (Pro & Agency tiers).
 */
export class WebhooksResource {
  constructor(private readonly client: SentryRelay) {}

  public async list(): Promise<OutboundWebhookDocument[]> {
    const res = await this.client.request<{ items: OutboundWebhookDocument[] }>({
      method: 'GET',
      path: '/api/v1/webhooks',
    });
    return res.items;
  }

  public async create(input: CreateWebhookRequestInput): Promise<OutboundWebhookDocument> {
    const res = await this.client.request<{ webhook: OutboundWebhookDocument }>({
      method: 'POST',
      path: '/api/v1/webhooks',
      body: input,
    });
    return res.webhook;
  }

  public async delete(webhookId: string): Promise<{ deleted: boolean; id: string }> {
    return this.client.request<{ deleted: boolean; id: string }>({
      method: 'DELETE',
      path: `/api/v1/webhooks/${encodeURIComponent(webhookId)}`,
    });
  }
}

/**
 * Audit Logs resource.
 */
export class AuditLogsResource {
  constructor(private readonly client: SentryRelay) {}

  public async list(query?: AuditLogQueryInput): Promise<AuditLogDocument[]> {
    const res = await this.client.request<{ items: AuditLogDocument[] }>({
      method: 'GET',
      path: '/api/v1/audit-logs',
      query: {
        identityId: query?.identityId,
        eventType: query?.eventType,
        from: query?.from,
        to: query?.to,
        limit: query?.limit,
      },
    });
    return res.items;
  }
}
