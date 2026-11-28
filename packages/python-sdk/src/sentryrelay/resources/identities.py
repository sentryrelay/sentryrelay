"""
Sentry Relay Identities Resource (Sync & Async)
"""

from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Union
from urllib.parse import quote

from sentryrelay.models import (
    CustomExtractionRule,
    DeleteIdentityResponse,
    HumanFallbackConfig,
    Identity,
    IdentityListResponse,
    LatestResponse,
    ProvisionSmsDidResponse,
    ReleaseSmsDidResponse,
    WaitResponse,
)

if TYPE_CHECKING:
    from sentryrelay.client import AsyncSentryRelay, SentryRelay


def _format_identity_body(
    name: Optional[str] = None,
    slug: Optional[str] = None,
    email_handle: Optional[str] = None,
    status: Optional[str] = None,
    fallback: Optional[Union[HumanFallbackConfig, Dict[str, Any]]] = None,
    custom_rules: Optional[List[Union[CustomExtractionRule, Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    if name is not None:
        body["name"] = name
    if slug is not None:
        body["slug"] = slug
    if email_handle is not None:
        body["emailHandle"] = email_handle
    if status is not None:
        body["status"] = status
    if fallback is not None:
        body["fallback"] = (
            fallback.model_dump(by_alias=True, exclude_none=True)
            if hasattr(fallback, "model_dump")
            else fallback
        )
    if custom_rules is not None:
        body["customRules"] = [
            r.model_dump(by_alias=True, exclude_none=True) if hasattr(r, "model_dump") else r
            for r in custom_rules
        ]
    return body


class IdentitiesResource:
    """Synchronous Identities API resource."""

    def __init__(self, client: "SentryRelay") -> None:
        self._client = client

    def list(
        self,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> IdentityListResponse:
        """List accessible Identities with optional pagination."""
        query: Dict[str, Any] = {}
        if limit is not None:
            query["limit"] = limit
        if cursor is not None:
            query["cursor"] = cursor

        data = self._client.request("GET", "/api/v1/identities", query=query)
        return IdentityListResponse.model_validate(data)

    def get(self, id_or_slug: str) -> Identity:
        """Fetch Identity configuration and attached credentials."""
        encoded = quote(id_or_slug, safe="")
        data = self._client.request("GET", f"/api/v1/identities/{encoded}")
        return Identity.model_validate(data["identity"])

    def create(
        self,
        name: str,
        slug: Optional[str] = None,
        email_handle: Optional[str] = None,
        fallback: Optional[Union[HumanFallbackConfig, Dict[str, Any]]] = None,
        custom_rules: Optional[List[Union[CustomExtractionRule, Dict[str, Any]]]] = None,
    ) -> Identity:
        """Create a new Identity profile."""
        body = _format_identity_body(
            name=name,
            slug=slug,
            email_handle=email_handle,
            fallback=fallback,
            custom_rules=custom_rules,
        )
        data = self._client.request("POST", "/api/v1/identities", body=body)
        return Identity.model_validate(data["identity"])

    def update(
        self,
        id_or_slug: str,
        name: Optional[str] = None,
        status: Optional[str] = None,
        fallback: Optional[Union[HumanFallbackConfig, Dict[str, Any]]] = None,
        custom_rules: Optional[List[Union[CustomExtractionRule, Dict[str, Any]]]] = None,
    ) -> Identity:
        """Update Identity settings, fallback routing, or custom regex rules."""
        encoded = quote(id_or_slug, safe="")
        body = _format_identity_body(
            name=name,
            status=status,
            fallback=fallback,
            custom_rules=custom_rules,
        )
        data = self._client.request("PATCH", f"/api/v1/identities/{encoded}", body=body)
        return Identity.model_validate(data["identity"])

    def delete(self, id_or_slug: str) -> DeleteIdentityResponse:
        """Delete an Identity and release its inbound routes."""
        encoded = quote(id_or_slug, safe="")
        data = self._client.request("DELETE", f"/api/v1/identities/{encoded}")
        return DeleteIdentityResponse.model_validate(data)

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
        Returns a clean WaitResponse (timed_out=True on normal timeout).
        """
        encoded = quote(id_or_slug, safe="")
        query: Dict[str, Any] = {}
        if timeout is not None:
            query["timeout"] = timeout
        if since is not None:
            query["since"] = since
        if channel is not None:
            query["channel"] = channel
        if sender is not None:
            query["sender"] = sender
        if subject is not None:
            query["subject"] = subject
        if consume is not None:
            query["consume"] = "true" if consume else "false"
        if include_non_auth is not None:
            query["includeNonAuth"] = "true" if include_non_auth else "false"

        data = self._client.request("GET", f"/api/v1/identities/{encoded}/wait", query=query)
        return WaitResponse.model_validate(data)

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
        encoded = quote(id_or_slug, safe="")
        query: Dict[str, Any] = {}
        if lookback_seconds is not None:
            query["lookbackSeconds"] = lookback_seconds
        if since is not None:
            query["since"] = since
        if channel is not None:
            query["channel"] = channel
        if sender is not None:
            query["sender"] = sender
        if subject is not None:
            query["subject"] = subject
        if consume is not None:
            query["consume"] = "true" if consume else "false"
        if include_non_auth is not None:
            query["includeNonAuth"] = "true" if include_non_auth else "false"

        data = self._client.request("GET", f"/api/v1/identities/{encoded}/latest", query=query)
        return LatestResponse.model_validate(data)

    def provision_sms_did(
        self,
        id_or_slug: str,
        area_code: Optional[str] = None,
        phone_number_e164: Optional[str] = None,
    ) -> ProvisionSmsDidResponse:
        """Provision and attach a dedicated US carrier phone number (Telnyx) to this Identity."""
        encoded = quote(id_or_slug, safe="")
        body: Dict[str, Any] = {}
        if area_code is not None:
            body["areaCode"] = area_code
        if phone_number_e164 is not None:
            body["phoneNumberE164"] = phone_number_e164

        data = self._client.request("POST", f"/api/v1/identities/{encoded}/sms/provision", body=body)
        return ProvisionSmsDidResponse.model_validate(data)

    def release_sms_did(self, id_or_slug: str) -> ReleaseSmsDidResponse:
        """Release the attached phone number back to the carrier pool."""
        encoded = quote(id_or_slug, safe="")
        data = self._client.request("DELETE", f"/api/v1/identities/{encoded}/sms")
        return ReleaseSmsDidResponse.model_validate(data)


class AsyncIdentitiesResource:
    """Asynchronous Identities API resource."""

    def __init__(self, client: "AsyncSentryRelay") -> None:
        self._client = client

    async def list(
        self,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> IdentityListResponse:
        """List accessible Identities with optional pagination."""
        query: Dict[str, Any] = {}
        if limit is not None:
            query["limit"] = limit
        if cursor is not None:
            query["cursor"] = cursor

        data = await self._client.request("GET", "/api/v1/identities", query=query)
        return IdentityListResponse.model_validate(data)

    async def get(self, id_or_slug: str) -> Identity:
        """Fetch Identity configuration and attached credentials."""
        encoded = quote(id_or_slug, safe="")
        data = await self._client.request("GET", f"/api/v1/identities/{encoded}")
        return Identity.model_validate(data["identity"])

    async def create(
        self,
        name: str,
        slug: Optional[str] = None,
        email_handle: Optional[str] = None,
        fallback: Optional[Union[HumanFallbackConfig, Dict[str, Any]]] = None,
        custom_rules: Optional[List[Union[CustomExtractionRule, Dict[str, Any]]]] = None,
    ) -> Identity:
        """Create a new Identity profile."""
        body = _format_identity_body(
            name=name,
            slug=slug,
            email_handle=email_handle,
            fallback=fallback,
            custom_rules=custom_rules,
        )
        data = await self._client.request("POST", "/api/v1/identities", body=body)
        return Identity.model_validate(data["identity"])

    async def update(
        self,
        id_or_slug: str,
        name: Optional[str] = None,
        status: Optional[str] = None,
        fallback: Optional[Union[HumanFallbackConfig, Dict[str, Any]]] = None,
        custom_rules: Optional[List[Union[CustomExtractionRule, Dict[str, Any]]]] = None,
    ) -> Identity:
        """Update Identity settings, fallback routing, or custom regex rules."""
        encoded = quote(id_or_slug, safe="")
        body = _format_identity_body(
            name=name,
            status=status,
            fallback=fallback,
            custom_rules=custom_rules,
        )
        data = await self._client.request("PATCH", f"/api/v1/identities/{encoded}", body=body)
        return Identity.model_validate(data["identity"])

    async def delete(self, id_or_slug: str) -> DeleteIdentityResponse:
        """Delete an Identity and release its inbound routes."""
        encoded = quote(id_or_slug, safe="")
        data = await self._client.request("DELETE", f"/api/v1/identities/{encoded}")
        return DeleteIdentityResponse.model_validate(data)

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
        Returns a clean WaitResponse (timed_out=True on normal timeout).
        """
        encoded = quote(id_or_slug, safe="")
        query: Dict[str, Any] = {}
        if timeout is not None:
            query["timeout"] = timeout
        if since is not None:
            query["since"] = since
        if channel is not None:
            query["channel"] = channel
        if sender is not None:
            query["sender"] = sender
        if subject is not None:
            query["subject"] = subject
        if consume is not None:
            query["consume"] = "true" if consume else "false"
        if include_non_auth is not None:
            query["includeNonAuth"] = "true" if include_non_auth else "false"

        data = await self._client.request("GET", f"/api/v1/identities/{encoded}/wait", query=query)
        return WaitResponse.model_validate(data)

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
        encoded = quote(id_or_slug, safe="")
        query: Dict[str, Any] = {}
        if lookback_seconds is not None:
            query["lookbackSeconds"] = lookback_seconds
        if since is not None:
            query["since"] = since
        if channel is not None:
            query["channel"] = channel
        if sender is not None:
            query["sender"] = sender
        if subject is not None:
            query["subject"] = subject
        if consume is not None:
            query["consume"] = "true" if consume else "false"
        if include_non_auth is not None:
            query["includeNonAuth"] = "true" if include_non_auth else "false"

        data = await self._client.request("GET", f"/api/v1/identities/{encoded}/latest", query=query)
        return LatestResponse.model_validate(data)

    async def provision_sms_did(
        self,
        id_or_slug: str,
        area_code: Optional[str] = None,
        phone_number_e164: Optional[str] = None,
    ) -> ProvisionSmsDidResponse:
        """Provision and attach a dedicated US carrier phone number (Telnyx) to this Identity."""
        encoded = quote(id_or_slug, safe="")
        body: Dict[str, Any] = {}
        if area_code is not None:
            body["areaCode"] = area_code
        if phone_number_e164 is not None:
            body["phoneNumberE164"] = phone_number_e164

        data = await self._client.request("POST", f"/api/v1/identities/{encoded}/sms/provision", body=body)
        return ProvisionSmsDidResponse.model_validate(data)

    async def release_sms_did(self, id_or_slug: str) -> ReleaseSmsDidResponse:
        """Release the attached phone number back to the carrier pool."""
        encoded = quote(id_or_slug, safe="")
        data = await self._client.request("DELETE", f"/api/v1/identities/{encoded}/sms")
        return ReleaseSmsDidResponse.model_validate(data)
