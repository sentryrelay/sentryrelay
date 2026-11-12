export const PRODUCT_NAME = 'Sentry Relay';
export const PRIMARY_DOMAIN = 'sentryrelay.com';
export const DEFAULT_INBOUND_EMAIL_DOMAIN = 'in.sentryrelay.com';
export const CLI_BINARY_NAME = 'srelay';

const API_KEY_REGEX = /^sr_(live|test)_[0-9A-Za-z]{32}$/;

/**
 * Validates whether a candidate token matches `sr_(live|test)_<32_base62>`.
 */
export function isValidApiKeyFormat(token: string): boolean {
  return API_KEY_REGEX.test(token);
}

export const API_ERROR_CODES = [
  'UNAUTHORIZED',
  'INVALID_API_KEY',
  'API_KEY_REVOKED',
  'API_KEY_EXPIRED',
  'INSUFFICIENT_SCOPE',
  'IDENTITY_OUT_OF_SCOPE',
  'FORBIDDEN',
  'NOT_FOUND',
  'IDENTITY_NOT_FOUND',
  'TOTP_SECRET_NOT_FOUND',
  'WEBHOOK_NOT_FOUND',
  'VALIDATION_ERROR',
  'CONFLICT',
  'EMAIL_HANDLE_TAKEN',
  'MONTHLY_QUOTA_EXCEEDED',
  'DAILY_QUOTA_EXCEEDED',
  'PLAN_LIMIT_EXCEEDED',
  'WORKSPACE_GRACE_SUSPENDED',
  'RATE_LIMIT_EXCEEDED',
  'INVALID_WEBHOOK_SIGNATURE',
  'TELNYX_PROVISIONING_FAILED',
  'KMS_CRYPTO_ERROR',
  'INTERNAL_ERROR',
] as const;

export type ApiErrorCode = (typeof API_ERROR_CODES)[number];

export const ERROR_HTTP_STATUS: Record<ApiErrorCode, number> = {
  UNAUTHORIZED: 401,
  INVALID_API_KEY: 401,
  API_KEY_REVOKED: 401,
  API_KEY_EXPIRED: 401,
  INVALID_WEBHOOK_SIGNATURE: 401,
  WORKSPACE_GRACE_SUSPENDED: 402,
  INSUFFICIENT_SCOPE: 403,
  IDENTITY_OUT_OF_SCOPE: 403,
  FORBIDDEN: 403,
  PLAN_LIMIT_EXCEEDED: 403,
  NOT_FOUND: 404,
  IDENTITY_NOT_FOUND: 404,
  TOTP_SECRET_NOT_FOUND: 404,
  WEBHOOK_NOT_FOUND: 404,
  CONFLICT: 409,
  EMAIL_HANDLE_TAKEN: 409,
  VALIDATION_ERROR: 422,
  MONTHLY_QUOTA_EXCEEDED: 429,
  DAILY_QUOTA_EXCEEDED: 429,
  RATE_LIMIT_EXCEEDED: 429,
  TELNYX_PROVISIONING_FAILED: 502,
  KMS_CRYPTO_ERROR: 500,
  INTERNAL_ERROR: 500,
};

export interface ApiErrorDetail {
  code: ApiErrorCode;
  message: string;
  details?: Record<string, unknown>;
  requestId?: string;
}

export interface ApiSuccessEnvelope<T> {
  data: T;
  error: null;
}

export interface ApiErrorEnvelope {
  data: null;
  error: ApiErrorDetail;
}

export type ApiEnvelope<T> = ApiSuccessEnvelope<T> | ApiErrorEnvelope;

export class SentryRelayApiError extends Error {
  public readonly code: ApiErrorCode;
  public readonly statusCode: number;
  public readonly details?: Record<string, unknown>;
  public readonly requestId?: string;

  constructor(
    code: ApiErrorCode,
    message: string,
    options?: {
      statusCode?: number;
      details?: Record<string, unknown>;
      requestId?: string;
      cause?: unknown;
    },
  ) {
    super(message, options?.cause ? { cause: options.cause } : undefined);
    this.name = 'SentryRelayApiError';
    this.code = code;
    this.statusCode = options?.statusCode ?? ERROR_HTTP_STATUS[code];
    this.details = options?.details;
    this.requestId = options?.requestId;
  }

  public toEnvelope(): ApiErrorEnvelope {
    return {
      data: null,
      error: {
        code: this.code,
        message: this.message,
        ...(this.details ? { details: this.details } : {}),
        ...(this.requestId ? { requestId: this.requestId } : {}),
      },
    };
  }
}

export type IdentityStatus = 'active' | 'paused' | 'grace_suspended';
export type ChannelType = 'email' | 'sms';
export type ExtractionClassification = 'otp' | 'magic_link' | 'otp_and_link' | 'non_auth';
export type TotpAlgorithm = 'SHA1' | 'SHA256' | 'SHA512';
export type TotpDigits = 6 | 8;
export type TotpPeriod = 30 | 60;

export type OutboundWebhookEvent =
  | 'otp.extracted'
  | 'magic_link.extracted'
  | 'sms.fallback_triggered'
  | 'email.fallback_triggered';

export type AuditEventType =
  | 'email.otp_extracted'
  | 'email.magic_link_extracted'
  | 'email.ignored_non_auth'
  | 'email.fallback_forwarded'
  | 'sms.otp_extracted'
  | 'sms.fallback_forwarded'
  | 'voice.call_bridged'
  | 'totp.generated'
  | 'totp.secret_created'
  | 'totp.secret_deleted'
  | 'api_key.created'
  | 'api_key.revoked'
  | 'did.provisioned'
  | 'did.released'
  | 'ephemeral_event.burned';

export interface ExtractedLinkItem {
  text: string;
  href: string;
}

export interface CustomExtractionRule {
  id: string;
  name: string;
  senderContains?: string;
  subjectContains?: string;
  otpRegex?: string;
  magicLinkRegex?: string;
  enabled: boolean;
}

export interface HumanFallbackConfig {
  enabled: boolean;
  fallbackEmail: string | null;
  fallbackWebhookUrl: string | null;
  voiceForwardToE164: string | null;
}

export interface IdentityDocument {
  id: string;
  workspaceId: string;
  name: string;
  slug: string;
  status: IdentityStatus;

  emailHandle: string;
  emailDomain: string;
  emailAddress: string;

  smsPhoneNumber: string | null;
  telnyxPhoneNumberId: string | null;
  smsAssignedAt: string | null;

  fallback: HumanFallbackConfig;
  customRules: CustomExtractionRule[];

  totpSecretCount: number;
  lastEventAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface TotpSecretMetadata {
  id: string;
  workspaceId: string;
  identityId: string;
  issuer: string;
  accountLabel: string;
  algorithm: TotpAlgorithm;
  digits: TotpDigits;
  period: TotpPeriod;
  lastUsedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface GeneratedTotpCode {
  code: string;
  remainingSeconds: number;
  nextCode?: string;
  period: number;
  digits: number;
  algorithm: string;
}

export interface OutboundWebhookDocument {
  id: string;
  workspaceId: string;
  targetUrl: string;
  signingSecret: string;
  events: OutboundWebhookEvent[];
  scopedIdentityIds: string[] | null;
  enabled: boolean;
  failureCount: number;
  lastDeliveredAt: string | null;
  createdAt: string;
}

export interface AuditLogDocument {
  id: string;
  workspaceId: string;
  identityId: string | null;
  eventType: AuditEventType;
  actor: {
    type: 'api_key' | 'user' | 'system_webhook';
    id: string;
  };
  metadata: {
    channel?: 'email' | 'sms' | 'voice' | 'totp';
    senderMasked?: string;
    classification?: string;
    latencyMs?: number;
  };
  createdAt: string;
  expireAtIso: string;
}

export interface CreateIdentityRequestInput {
  name: string;
  slug?: string;
  emailHandle?: string;
  fallback?: Partial<HumanFallbackConfig>;
  customRules?: Array<Omit<CustomExtractionRule, 'enabled'> & { enabled?: boolean }>;
}

export interface UpdateIdentityRequestInput {
  name?: string;
  status?: 'active' | 'paused';
  fallback?: Partial<HumanFallbackConfig>;
  customRules?: Array<Omit<CustomExtractionRule, 'enabled'> & { enabled?: boolean }>;
}

export interface WaitQueryInput {
  timeout?: number;
  since?: number;
  channel?: ChannelType;
  sender?: string;
  subject?: string;
  consume?: boolean;
  includeNonAuth?: boolean;
}

export interface LatestQueryInput {
  lookbackSeconds?: number;
  since?: number;
  channel?: ChannelType;
  sender?: string;
  subject?: string;
  consume?: boolean;
  includeNonAuth?: boolean;
}

export type CreateTotpSecretRequestInput =
  | {
      id?: string;
      otpauthUri: string;
    }
  | {
      id?: string;
      secret: string;
      issuer: string;
      accountLabel?: string;
      algorithm?: TotpAlgorithm;
      digits?: TotpDigits;
      period?: TotpPeriod;
    };

export interface ProvisionSmsDidRequestInput {
  areaCode?: string;
  phoneNumberE164?: string;
}

export interface CreateWebhookRequestInput {
  targetUrl: string;
  events: OutboundWebhookEvent[];
  scopedIdentityIds?: string[] | null;
}

export interface AuditLogQueryInput {
  identityId?: string;
  eventType?: string;
  from?: string;
  to?: string;
  limit?: number;
  cursor?: string;
}
