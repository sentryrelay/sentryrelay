"""
Sentry Relay SDK Exception Classes and Error Codes
"""

from typing import Any, Dict, Optional

API_ERROR_CODES = (
    "UNAUTHORIZED",
    "INVALID_API_KEY",
    "API_KEY_REVOKED",
    "API_KEY_EXPIRED",
    "INSUFFICIENT_SCOPE",
    "IDENTITY_OUT_OF_SCOPE",
    "FORBIDDEN",
    "NOT_FOUND",
    "IDENTITY_NOT_FOUND",
    "TOTP_SECRET_NOT_FOUND",
    "WEBHOOK_NOT_FOUND",
    "VALIDATION_ERROR",
    "CONFLICT",
    "EMAIL_HANDLE_TAKEN",
    "MONTHLY_QUOTA_EXCEEDED",
    "DAILY_QUOTA_EXCEEDED",
    "PLAN_LIMIT_EXCEEDED",
    "WORKSPACE_GRACE_SUSPENDED",
    "RATE_LIMIT_EXCEEDED",
    "INVALID_WEBHOOK_SIGNATURE",
    "TELNYX_PROVISIONING_FAILED",
    "KMS_CRYPTO_ERROR",
    "INTERNAL_ERROR",
)

ERROR_HTTP_STATUS: Dict[str, int] = {
    "UNAUTHORIZED": 401,
    "INVALID_API_KEY": 401,
    "API_KEY_REVOKED": 401,
    "API_KEY_EXPIRED": 401,
    "INVALID_WEBHOOK_SIGNATURE": 401,
    "WORKSPACE_GRACE_SUSPENDED": 402,
    "INSUFFICIENT_SCOPE": 403,
    "IDENTITY_OUT_OF_SCOPE": 403,
    "FORBIDDEN": 403,
    "PLAN_LIMIT_EXCEEDED": 403,
    "NOT_FOUND": 404,
    "IDENTITY_NOT_FOUND": 404,
    "TOTP_SECRET_NOT_FOUND": 404,
    "WEBHOOK_NOT_FOUND": 404,
    "CONFLICT": 409,
    "EMAIL_HANDLE_TAKEN": 409,
    "VALIDATION_ERROR": 422,
    "MONTHLY_QUOTA_EXCEEDED": 429,
    "DAILY_QUOTA_EXCEEDED": 429,
    "RATE_LIMIT_EXCEEDED": 429,
    "TELNYX_PROVISIONING_FAILED": 502,
    "KMS_CRYPTO_ERROR": 500,
    "INTERNAL_ERROR": 500,
}


class SentryRelayError(Exception):
    """Base exception for all Sentry Relay errors."""
    pass


class SentryRelayApiError(SentryRelayError):
    """
    Standard exception raised when the Sentry Relay API returns an error response
    or an HTTP failure occurs.
    """

    def __init__(
        self,
        code: str,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.status_code = status_code if status_code is not None else ERROR_HTTP_STATUS.get(code, 500)
        self.details = details or {}
        self.request_id = request_id


class AuthenticationError(SentryRelayApiError):
    """Raised on 401 Unauthorized / Invalid API Key errors."""
    pass


class PaymentRequiredError(SentryRelayApiError):
    """Raised on 402 Payment Required / Grace Suspended errors."""
    pass


class PermissionDeniedError(SentryRelayApiError):
    """Raised on 403 Forbidden / Insufficient Scope errors."""
    pass


class NotFoundError(SentryRelayApiError):
    """Raised on 404 Not Found errors."""
    pass


class ConflictError(SentryRelayApiError):
    """Raised on 409 Conflict errors (e.g. email handle taken)."""
    pass


class ValidationError(SentryRelayApiError):
    """Raised on 422 Validation Error responses."""
    pass


class RateLimitError(SentryRelayApiError):
    """Raised on 429 Rate Limit Exceeded responses."""
    pass


class QuotaExceededError(SentryRelayApiError):
    """Raised on 429 Monthly or Daily Quota Exceeded responses."""
    pass


class InternalServerError(SentryRelayApiError):
    """Raised on 500 Internal Server Error responses."""
    pass


class BadGatewayError(SentryRelayApiError):
    """Raised on 502 Bad Gateway / Upstream errors."""
    pass


def raise_for_api_error(
    code: str,
    message: str,
    status_code: int,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> None:
    """Instantiate and raise the most specific SentryRelayApiError subclass."""
    kwargs = {
        "code": code,
        "message": message,
        "status_code": status_code,
        "details": details,
        "request_id": request_id,
    }

    if code in ("MONTHLY_QUOTA_EXCEEDED", "DAILY_QUOTA_EXCEEDED"):
        raise QuotaExceededError(**kwargs)

    if status_code == 401 or code in ("INVALID_API_KEY", "UNAUTHORIZED", "API_KEY_REVOKED", "API_KEY_EXPIRED"):
        raise AuthenticationError(**kwargs)
    elif status_code == 402 or code == "WORKSPACE_GRACE_SUSPENDED":
        raise PaymentRequiredError(**kwargs)
    elif status_code == 403 or code in ("FORBIDDEN", "INSUFFICIENT_SCOPE", "IDENTITY_OUT_OF_SCOPE", "PLAN_LIMIT_EXCEEDED"):
        raise PermissionDeniedError(**kwargs)
    elif status_code == 404 or code in ("NOT_FOUND", "IDENTITY_NOT_FOUND", "TOTP_SECRET_NOT_FOUND", "WEBHOOK_NOT_FOUND"):
        raise NotFoundError(**kwargs)
    elif status_code == 409 or code in ("CONFLICT", "EMAIL_HANDLE_TAKEN"):
        raise ConflictError(**kwargs)
    elif status_code == 422 or code == "VALIDATION_ERROR":
        raise ValidationError(**kwargs)
    elif status_code == 429:
        raise RateLimitError(**kwargs)
    elif status_code == 502 or code == "TELNYX_PROVISIONING_FAILED":
        raise BadGatewayError(**kwargs)
    elif status_code >= 500:
        raise InternalServerError(**kwargs)

    raise SentryRelayApiError(**kwargs)
