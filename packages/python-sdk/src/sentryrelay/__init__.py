"""
Sentry Relay Official Python SDK
The 2FA, OTP & Magic-Link Inbox API for Autonomous Software.
"""

from sentryrelay.client import (
    AsyncSentryRelay,
    AsyncSentryRelayClient,
    SentryRelay,
    SentryRelayClient,
)
from sentryrelay.errors import (
    AuthenticationError,
    BadGatewayError,
    ConflictError,
    InternalServerError,
    NotFoundError,
    PaymentRequiredError,
    PermissionDeniedError,
    QuotaExceededError,
    RateLimitError,
    SentryRelayApiError,
    SentryRelayError,
    ValidationError,
)
from sentryrelay.integrations.playwright import fill_otp_code
from sentryrelay.models import (
    AuditLog,
    CustomExtractionRule,
    DeleteIdentityResponse,
    DeleteTotpSecretResponse,
    DeleteWebhookResponse,
    ExtractedAuthEvent,
    ExtractedLinkItem,
    GeneratedTotpCode,
    HumanFallbackConfig,
    Identity,
    IdentityListResponse,
    LatestResponse,
    OutboundWebhook,
    ProvisionSmsDidResponse,
    ReleaseSmsDidResponse,
    TotpSecretMetadata,
    WaitResponse,
)

__version__ = "0.2.0"

__all__ = [
    # Clients
    "SentryRelay",
    "AsyncSentryRelay",
    "SentryRelayClient",
    "AsyncSentryRelayClient",
    # Errors
    "SentryRelayError",
    "SentryRelayApiError",
    "AuthenticationError",
    "PaymentRequiredError",
    "PermissionDeniedError",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "RateLimitError",
    "QuotaExceededError",
    "InternalServerError",
    "BadGatewayError",
    # Models
    "Identity",
    "IdentityListResponse",
    "DeleteIdentityResponse",
    "ProvisionSmsDidResponse",
    "ReleaseSmsDidResponse",
    "WaitResponse",
    "LatestResponse",
    "ExtractedAuthEvent",
    "ExtractedLinkItem",
    "GeneratedTotpCode",
    "TotpSecretMetadata",
    "DeleteTotpSecretResponse",
    "OutboundWebhook",
    "DeleteWebhookResponse",
    "AuditLog",
    "HumanFallbackConfig",
    "CustomExtractionRule",
    # Helpers
    "fill_otp_code",
    "__version__",
]
