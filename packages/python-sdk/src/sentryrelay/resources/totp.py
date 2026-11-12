"""
Sentry Relay RFC 6238 TOTP Authenticator Resource (Sync & Async)
"""

from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional
from urllib.parse import quote

from sentryrelay.constants import TOTP_AUTO_WAIT_THRESHOLD_SECONDS
from sentryrelay.models import (
    DeleteTotpSecretResponse,
    GeneratedTotpCode,
    TotpSecretMetadata,
)

if TYPE_CHECKING:
    from sentryrelay.client import AsyncSentryRelay, SentryRelay


class TotpResource:
    """Synchronous TOTP Authenticator API resource."""

    def __init__(self, client: "SentryRelay") -> None:
        self._client = client

    def list(self, id_or_slug: str) -> List[TotpSecretMetadata]:
        """List vaulted TOTP secrets for an Identity (metadata only, seeds are never exposed)."""
        encoded = quote(id_or_slug, safe="")
        data = self._client.request("GET", f"/api/v1/identities/{encoded}/totp")
        return [TotpSecretMetadata.model_validate(item) for item in data.get("items", [])]

    def create(
        self,
        id_or_slug: str,
        otpauth_uri: Optional[str] = None,
        secret: Optional[str] = None,
        issuer: Optional[str] = None,
        account_label: str = "default",
        algorithm: Literal["SHA1", "SHA256", "SHA512"] = "SHA1",
        digits: Literal[6, 8] = 6,
        period: Literal[30, 60] = 30,
        id: Optional[str] = None,
    ) -> TotpSecretMetadata:
        """
        Vault a new TOTP secret for an Identity.
        Accepts either an `otpauth://totp/...` URI or manual Base32 secret parameters.
        """
        encoded = quote(id_or_slug, safe="")
        body: Dict[str, Any] = {}
        if id is not None:
            body["id"] = id

        if otpauth_uri is not None:
            body["otpauthUri"] = otpauth_uri
        elif secret is not None and issuer is not None:
            body["secret"] = secret
            body["issuer"] = issuer
            body["accountLabel"] = account_label
            body["algorithm"] = algorithm
            body["digits"] = digits
            body["period"] = period
        else:
            raise ValueError("Must provide either otpauth_uri or both secret and issuer")

        data = self._client.request("POST", f"/api/v1/identities/{encoded}/totp", body=body)
        return TotpSecretMetadata.model_validate(data["secret"])

    def get(
        self,
        id_or_slug: str,
        secret_id: str,
        auto_wait_fresh_window: bool = True,
        now_ms: Optional[int] = None,
    ) -> GeneratedTotpCode:
        """
        Generate a live RFC 6238 TOTP code.

        If `auto_wait_fresh_window` is True (default) and `remaining_seconds < 4`,
        transparently sleeps through the rollover and fetches a guaranteed fresh code
        so autonomous browser agents never fail due to mid-keystroke expiration.
        """
        encoded_id = quote(id_or_slug, safe="")
        encoded_secret = quote(secret_id, safe="")
        path = f"/api/v1/identities/{encoded_id}/totp/{encoded_secret}"

        query: Dict[str, Any] = {}
        if now_ms is not None:
            query["nowMs"] = now_ms

        initial_data = self._client.request("GET", path, query=query)
        code_obj = GeneratedTotpCode.model_validate(initial_data)

        if auto_wait_fresh_window and code_obj.remaining_seconds < TOTP_AUTO_WAIT_THRESHOLD_SECONDS:
            # Sleep until rollover plus 200ms buffer so next period is active
            sleep_ms = max(100, int(code_obj.remaining_seconds * 1000 + 200))
            self._client.sleep(sleep_ms / 1000.0)

            next_now_ms = now_ms + sleep_ms if now_ms is not None else None
            next_query = {"nowMs": next_now_ms} if next_now_ms is not None else None
            fresh_data = self._client.request("GET", path, query=next_query)
            return GeneratedTotpCode.model_validate(fresh_data)

        return code_obj

    def delete(self, id_or_slug: str, secret_id: str) -> DeleteTotpSecretResponse:
        """Permanently delete a vaulted TOTP secret."""
        encoded_id = quote(id_or_slug, safe="")
        encoded_secret = quote(secret_id, safe="")
        data = self._client.request(
            "DELETE", f"/api/v1/identities/{encoded_id}/totp/{encoded_secret}"
        )
        return DeleteTotpSecretResponse.model_validate(data)


class AsyncTotpResource:
    """Asynchronous TOTP Authenticator API resource."""

    def __init__(self, client: "AsyncSentryRelay") -> None:
        self._client = client

    async def list(self, id_or_slug: str) -> List[TotpSecretMetadata]:
        """List vaulted TOTP secrets for an Identity (metadata only, seeds are never exposed)."""
        encoded = quote(id_or_slug, safe="")
        data = await self._client.request("GET", f"/api/v1/identities/{encoded}/totp")
        return [TotpSecretMetadata.model_validate(item) for item in data.get("items", [])]

    async def create(
        self,
        id_or_slug: str,
        otpauth_uri: Optional[str] = None,
        secret: Optional[str] = None,
        issuer: Optional[str] = None,
        account_label: str = "default",
        algorithm: Literal["SHA1", "SHA256", "SHA512"] = "SHA1",
        digits: Literal[6, 8] = 6,
        period: Literal[30, 60] = 30,
        id: Optional[str] = None,
    ) -> TotpSecretMetadata:
        """
        Vault a new TOTP secret for an Identity.
        Accepts either an `otpauth://totp/...` URI or manual Base32 secret parameters.
        """
        encoded = quote(id_or_slug, safe="")
        body: Dict[str, Any] = {}
        if id is not None:
            body["id"] = id

        if otpauth_uri is not None:
            body["otpauthUri"] = otpauth_uri
        elif secret is not None and issuer is not None:
            body["secret"] = secret
            body["issuer"] = issuer
            body["accountLabel"] = account_label
            body["algorithm"] = algorithm
            body["digits"] = digits
            body["period"] = period
        else:
            raise ValueError("Must provide either otpauth_uri or both secret and issuer")

        data = await self._client.request("POST", f"/api/v1/identities/{encoded}/totp", body=body)
        return TotpSecretMetadata.model_validate(data["secret"])

    async def get(
        self,
        id_or_slug: str,
        secret_id: str,
        auto_wait_fresh_window: bool = True,
        now_ms: Optional[int] = None,
    ) -> GeneratedTotpCode:
        """
        Generate a live RFC 6238 TOTP code.

        If `auto_wait_fresh_window` is True (default) and `remaining_seconds < 4`,
        transparently sleeps through the rollover and fetches a guaranteed fresh code
        so autonomous browser agents never fail due to mid-keystroke expiration.
        """
        encoded_id = quote(id_or_slug, safe="")
        encoded_secret = quote(secret_id, safe="")
        path = f"/api/v1/identities/{encoded_id}/totp/{encoded_secret}"

        query: Dict[str, Any] = {}
        if now_ms is not None:
            query["nowMs"] = now_ms

        initial_data = await self._client.request("GET", path, query=query)
        code_obj = GeneratedTotpCode.model_validate(initial_data)

        if auto_wait_fresh_window and code_obj.remaining_seconds < TOTP_AUTO_WAIT_THRESHOLD_SECONDS:
            sleep_ms = max(100, int(code_obj.remaining_seconds * 1000 + 200))
            await self._client.sleep(sleep_ms / 1000.0)

            next_now_ms = now_ms + sleep_ms if now_ms is not None else None
            next_query = {"nowMs": next_now_ms} if next_now_ms is not None else None
            fresh_data = await self._client.request("GET", path, query=next_query)
            return GeneratedTotpCode.model_validate(fresh_data)

        return code_obj

    async def delete(self, id_or_slug: str, secret_id: str) -> DeleteTotpSecretResponse:
        """Permanently delete a vaulted TOTP secret."""
        encoded_id = quote(id_or_slug, safe="")
        encoded_secret = quote(secret_id, safe="")
        data = await self._client.request(
            "DELETE", f"/api/v1/identities/{encoded_id}/totp/{encoded_secret}"
        )
        return DeleteTotpSecretResponse.model_validate(data)
