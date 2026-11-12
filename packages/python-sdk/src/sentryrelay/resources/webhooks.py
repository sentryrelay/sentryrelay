"""
Sentry Relay Outbound Webhooks Resource (Sync & Async)
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from urllib.parse import quote

from sentryrelay.models import DeleteWebhookResponse, OutboundWebhook

if TYPE_CHECKING:
    from sentryrelay.client import AsyncSentryRelay, SentryRelay


class WebhooksResource:
    """Synchronous Outbound Webhooks API resource."""

    def __init__(self, client: "SentryRelay") -> None:
        self._client = client

    def list(self) -> List[OutboundWebhook]:
        """List configured outbound webhooks for the workspace."""
        data = self._client.request("GET", "/api/v1/webhooks")
        return [OutboundWebhook.model_validate(item) for item in data.get("items", [])]

    def create(
        self,
        target_url: str,
        events: List[str],
        scoped_identity_ids: Optional[List[str]] = None,
    ) -> OutboundWebhook:
        """Register a new outbound webhook with HMAC-SHA256 signature dispatch."""
        body: Dict[str, Any] = {
            "targetUrl": target_url,
            "events": events,
        }
        if scoped_identity_ids is not None:
            body["scopedIdentityIds"] = scoped_identity_ids

        data = self._client.request("POST", "/api/v1/webhooks", body=body)
        return OutboundWebhook.model_validate(data["webhook"])

    def delete(self, webhook_id: str) -> DeleteWebhookResponse:
        """Permanently delete an outbound webhook."""
        encoded = quote(webhook_id, safe="")
        data = self._client.request("DELETE", f"/api/v1/webhooks/{encoded}")
        return DeleteWebhookResponse.model_validate(data)


class AsyncWebhooksResource:
    """Asynchronous Outbound Webhooks API resource."""

    def __init__(self, client: "AsyncSentryRelay") -> None:
        self._client = client

    async def list(self) -> List[OutboundWebhook]:
        """List configured outbound webhooks for the workspace."""
        data = await self._client.request("GET", "/api/v1/webhooks")
        return [OutboundWebhook.model_validate(item) for item in data.get("items", [])]

    async def create(
        self,
        target_url: str,
        events: List[str],
        scoped_identity_ids: Optional[List[str]] = None,
    ) -> OutboundWebhook:
        """Register a new outbound webhook with HMAC-SHA256 signature dispatch."""
        body: Dict[str, Any] = {
            "targetUrl": target_url,
            "events": events,
        }
        if scoped_identity_ids is not None:
            body["scopedIdentityIds"] = scoped_identity_ids

        data = await self._client.request("POST", "/api/v1/webhooks", body=body)
        return OutboundWebhook.model_validate(data["webhook"])

    async def delete(self, webhook_id: str) -> DeleteWebhookResponse:
        """Permanently delete an outbound webhook."""
        encoded = quote(webhook_id, safe="")
        data = await self._client.request("DELETE", f"/api/v1/webhooks/{encoded}")
        return DeleteWebhookResponse.model_validate(data)
