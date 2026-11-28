"""
Official Sentry Relay Python SDK Client (Sync & Async)
"""

import asyncio
import os
import random
import time
from typing import Any, Dict, Literal, Optional, Union

import httpx

from sentryrelay.constants import (
    API_KEY_REGEX,
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
)
from sentryrelay.errors import SentryRelayApiError, raise_for_api_error
from sentryrelay.models import LatestResponse, WaitResponse
from sentryrelay.resources.audit_logs import AsyncAuditLogsResource, AuditLogsResource
from sentryrelay.resources.identities import AsyncIdentitiesResource, IdentitiesResource
from sentryrelay.resources.totp import AsyncTotpResource, TotpResource
from sentryrelay.resources.webhooks import AsyncWebhooksResource, WebhooksResource

SDK_VERSION = "0.2.0"


def _validate_api_key(api_key: Optional[str]) -> str:
    key = api_key or os.environ.get("SENTRY_RELAY_API_KEY")
    if not key or not API_KEY_REGEX.match(key):
        raise SentryRelayApiError(
            code="INVALID_API_KEY",
            message="API key must match sr_live_<32_base62> or sr_test_<32_base62>",
            status_code=401,
        )
    return key


def _normalize_base_url(base_url: Optional[str]) -> str:
    url = base_url or os.environ.get("SENTRY_RELAY_BASE_URL") or DEFAULT_BASE_URL
    return url.rstrip("/")


class SentryRelay:
    """
    Official Sentry Relay Synchronous Client.
    Zero-retention 2FA, OTP & Magic-Link Vault client for autonomous software.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self.api_key: str = _validate_api_key(api_key)
        self.base_url: str = _normalize_base_url(base_url)
        self.max_retries: int = max_retries
        self.retry_delay_seconds: float = retry_delay_seconds
        self.timeout: float = timeout

        self._owns_http_client: bool = http_client is None
        self._http_client: httpx.Client = http_client or httpx.Client(
            timeout=httpx.Timeout(self.timeout),
        )

        self.identities: IdentitiesResource = IdentitiesResource(self)
        self.totp: TotpResource = TotpResource(self)
        self.webhooks: WebhooksResource = WebhooksResource(self)
        self.audit_logs: AuditLogsResource = AuditLogsResource(self)

    def get_auth_headers(self) -> Dict[str, str]:
        """Headers required for all authenticated API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"sentryrelay-python/{SDK_VERSION}",
        }

    def sleep(self, seconds: float) -> None:
        """Internal sleep helper, overridable in tests."""
        time.sleep(seconds)

    def request(
        self,
        method: str,
        path: str,
        query: Optional[Dict[str, Any]] = None,
        body: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        skip_retry: bool = False,
    ) -> Any:
        """
        Execute an HTTP request with automatic exponential backoff for transient errors.
        """
        url = f"{self.base_url}{path}"
        req_headers = {**self.get_auth_headers(), **(headers or {})}

        params: Dict[str, str] = {}
        if query:
            for k, v in query.items():
                if v is not None:
                    params[k] = str(v)

        method_upper = method.upper()
        is_mutating = method_upper != "GET"
        effective_max_retries = 0 if skip_retry else self.max_retries

        attempt = 0
        while True:
            try:
                response = self._http_client.request(
                    method=method_upper,
                    url=url,
                    params=params or None,
                    json=body if body is not None else None,
                    headers=req_headers,
                )

                content_type = response.headers.get("content-type", "")
                is_json = "application/json" in content_type

                if response.is_success:
                    if is_json:
                        payload = response.json()
                        if isinstance(payload, dict) and "data" in payload:
                            return payload["data"]
                        return payload
                    return response.text

                # Parse error response
                error_code = "INTERNAL_ERROR"
                error_message = f"HTTP {response.status_code} {response.reason_phrase}"
                error_details: Optional[Dict[str, Any]] = None
                request_id: Optional[str] = response.headers.get("x-request-id")

                if is_json:
                    try:
                        err_payload = response.json()
                        if isinstance(err_payload, dict) and "error" in err_payload:
                            err_info = err_payload["error"]
                            if isinstance(err_info, dict):
                                error_code = err_info.get("code", error_code)
                                error_message = err_info.get("message", error_message)
                                error_details = err_info.get("details")
                                request_id = err_info.get("requestId", request_id)
                    except Exception:
                        pass

                is_transient_status = response.status_code >= 500 or response.status_code == 429
                can_retry = not is_mutating and is_transient_status and attempt < effective_max_retries

                if can_retry:
                    attempt += 1
                    delay = min(
                        1.0,
                        self.retry_delay_seconds * (2 ** attempt) + random.uniform(0, 0.02),
                    )
                    self.sleep(delay)
                    continue

                raise_for_api_error(
                    code=error_code,
                    message=error_message,
                    status_code=response.status_code,
                    details=error_details,
                    request_id=request_id,
                )

            except SentryRelayApiError:
                raise
            except (httpx.NetworkError, httpx.TimeoutException) as exc:
                can_retry = not is_mutating and attempt < effective_max_retries
                if can_retry:
                    attempt += 1
                    delay = min(
                        1.0,
                        self.retry_delay_seconds * (2 ** attempt) + random.uniform(0, 0.02),
                    )
                    self.sleep(delay)
                    continue

                raise SentryRelayApiError(
                    code="INTERNAL_ERROR",
                    message=f"Network error during Sentry Relay request: {exc}",
                    status_code=500,
                ) from exc
            except Exception as exc:
                raise SentryRelayApiError(
                    code="INTERNAL_ERROR",
                    message=f"Unexpected error during Sentry Relay request: {exc}",
                    status_code=500,
                ) from exc

    # Top-level ergonomic aliases
    def wait(
        self,
        id_or_slug: str,
        timeout: Optional[int] = 30,
        since: Optional[int] = None,
        channel: Optional[Literal["email", "sms"]] = None,
        sender: Optional[str] = None,
        subject: Optional[str] = None,
        consume: Optional[bool] = True,
        include_non_auth: Optional[bool] = None,
    ) -> WaitResponse:
        """
        Long-polling wait primitive for Email OTPs, Magic Links, and SMS verification codes.
        Blocks up to `timeout` seconds until a matching auth event arrives.
        """
        return self.identities.wait(
            id_or_slug=id_or_slug,
            timeout=timeout,
            since=since,
            channel=channel,
            sender=sender,
            subject=subject,
            consume=consume,
            include_non_auth=include_non_auth,
        )

    def latest(
        self,
        id_or_slug: str,
        lookback_seconds: Optional[int] = 60,
        since: Optional[int] = None,
        channel: Optional[Literal["email", "sms"]] = None,
        sender: Optional[str] = None,
        subject: Optional[str] = None,
        consume: Optional[bool] = True,
        include_non_auth: Optional[bool] = None,
    ) -> LatestResponse:
        """Instant non-blocking check against the Redis timeline for received codes."""
        return self.identities.latest(
            id_or_slug=id_or_slug,
            lookback_seconds=lookback_seconds,
            since=since,
            channel=channel,
            sender=sender,
            subject=subject,
            consume=consume,
            include_non_auth=include_non_auth,
        )

    def close(self) -> None:
        """Close the underlying HTTP client session if owned by this instance."""
        if self._owns_http_client:
            self._http_client.close()

    def __enter__(self) -> "SentryRelay":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


class AsyncSentryRelay:
    """
    Official Sentry Relay Asynchronous Client.
    Zero-retention 2FA, OTP & Magic-Link Vault client for async autonomous software
    (Browser Use, Playwright Python async, LangGraph, CrewAI).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.api_key: str = _validate_api_key(api_key)
        self.base_url: str = _normalize_base_url(base_url)
        self.max_retries: int = max_retries
        self.retry_delay_seconds: float = retry_delay_seconds
        self.timeout: float = timeout

        self._owns_http_client: bool = http_client is None
        self._http_client: httpx.AsyncClient = http_client or httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
        )

        self.identities: AsyncIdentitiesResource = AsyncIdentitiesResource(self)
        self.totp: AsyncTotpResource = AsyncTotpResource(self)
        self.webhooks: AsyncWebhooksResource = AsyncWebhooksResource(self)
        self.audit_logs: AsyncAuditLogsResource = AsyncAuditLogsResource(self)

    def get_auth_headers(self) -> Dict[str, str]:
        """Headers required for all authenticated API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"sentryrelay-python/{SDK_VERSION}",
        }

    async def sleep(self, seconds: float) -> None:
        """Internal async sleep helper, overridable in tests."""
        await asyncio.sleep(seconds)

    async def request(
        self,
        method: str,
        path: str,
        query: Optional[Dict[str, Any]] = None,
        body: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        skip_retry: bool = False,
    ) -> Any:
        """
        Execute an asynchronous HTTP request with automatic exponential backoff.
        """
        url = f"{self.base_url}{path}"
        req_headers = {**self.get_auth_headers(), **(headers or {})}

        params: Dict[str, str] = {}
        if query:
            for k, v in query.items():
                if v is not None:
                    params[k] = str(v)

        method_upper = method.upper()
        is_mutating = method_upper != "GET"
        effective_max_retries = 0 if skip_retry else self.max_retries

        attempt = 0
        while True:
            try:
                response = await self._http_client.request(
                    method=method_upper,
                    url=url,
                    params=params or None,
                    json=body if body is not None else None,
                    headers=req_headers,
                )

                content_type = response.headers.get("content-type", "")
                is_json = "application/json" in content_type

                if response.is_success:
                    if is_json:
                        payload = response.json()
                        if isinstance(payload, dict) and "data" in payload:
                            return payload["data"]
                        return payload
                    return response.text

                # Parse error response
                error_code = "INTERNAL_ERROR"
                error_message = f"HTTP {response.status_code} {response.reason_phrase}"
                error_details: Optional[Dict[str, Any]] = None
                request_id: Optional[str] = response.headers.get("x-request-id")

                if is_json:
                    try:
                        err_payload = response.json()
                        if isinstance(err_payload, dict) and "error" in err_payload:
                            err_info = err_payload["error"]
                            if isinstance(err_info, dict):
                                error_code = err_info.get("code", error_code)
                                error_message = err_info.get("message", error_message)
                                error_details = err_info.get("details")
                                request_id = err_info.get("requestId", request_id)
                    except Exception:
                        pass

                is_transient_status = response.status_code >= 500 or response.status_code == 429
                can_retry = not is_mutating and is_transient_status and attempt < effective_max_retries

                if can_retry:
                    attempt += 1
                    delay = min(
                        1.0,
                        self.retry_delay_seconds * (2 ** attempt) + random.uniform(0, 0.02),
                    )
                    await self.sleep(delay)
                    continue

                raise_for_api_error(
                    code=error_code,
                    message=error_message,
                    status_code=response.status_code,
                    details=error_details,
                    request_id=request_id,
                )

            except SentryRelayApiError:
                raise
            except (httpx.NetworkError, httpx.TimeoutException) as exc:
                can_retry = not is_mutating and attempt < effective_max_retries
                if can_retry:
                    attempt += 1
                    delay = min(
                        1.0,
                        self.retry_delay_seconds * (2 ** attempt) + random.uniform(0, 0.02),
                    )
                    await self.sleep(delay)
                    continue

                raise SentryRelayApiError(
                    code="INTERNAL_ERROR",
                    message=f"Network error during Sentry Relay request: {exc}",
                    status_code=500,
                ) from exc
            except Exception as exc:
                raise SentryRelayApiError(
                    code="INTERNAL_ERROR",
                    message=f"Unexpected error during Sentry Relay request: {exc}",
                    status_code=500,
                ) from exc

    # Top-level ergonomic aliases
    async def wait(
        self,
        id_or_slug: str,
        timeout: Optional[int] = 30,
        since: Optional[int] = None,
        channel: Optional[Literal["email", "sms"]] = None,
        sender: Optional[str] = None,
        subject: Optional[str] = None,
        consume: Optional[bool] = True,
        include_non_auth: Optional[bool] = None,
    ) -> WaitResponse:
        """
        Long-polling wait primitive for Email OTPs, Magic Links, and SMS verification codes.
        Blocks up to `timeout` seconds until a matching auth event arrives.
        """
        return await self.identities.wait(
            id_or_slug=id_or_slug,
            timeout=timeout,
            since=since,
            channel=channel,
            sender=sender,
            subject=subject,
            consume=consume,
            include_non_auth=include_non_auth,
        )

    async def latest(
        self,
        id_or_slug: str,
        lookback_seconds: Optional[int] = 60,
        since: Optional[int] = None,
        channel: Optional[Literal["email", "sms"]] = None,
        sender: Optional[str] = None,
        subject: Optional[str] = None,
        consume: Optional[bool] = True,
        include_non_auth: Optional[bool] = None,
    ) -> LatestResponse:
        """Instant non-blocking check against the Redis timeline for received codes."""
        return await self.identities.latest(
            id_or_slug=id_or_slug,
            lookback_seconds=lookback_seconds,
            since=since,
            channel=channel,
            sender=sender,
            subject=subject,
            consume=consume,
            include_non_auth=include_non_auth,
        )

    async def aclose(self) -> None:
        """Close the underlying HTTP client session if owned by this instance."""
        if self._owns_http_client:
            await self._http_client.aclose()

    async def close(self) -> None:
        """Alias for aclose()."""
        await self.aclose()

    async def __aenter__(self) -> "AsyncSentryRelay":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.aclose()


# Backward-compatible and conversational aliases
SentryRelayClient = SentryRelay
AsyncSentryRelayClient = AsyncSentryRelay
