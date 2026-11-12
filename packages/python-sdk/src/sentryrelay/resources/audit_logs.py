"""
Sentry Relay Sanitized Zero-PII Audit Logs Resource (Sync & Async)
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from sentryrelay.models import AuditLog

if TYPE_CHECKING:
    from sentryrelay.client import AsyncSentryRelay, SentryRelay


def _format_time(t: Optional[Union[str, datetime]]) -> Optional[str]:
    if t is None:
        return None
    if isinstance(t, datetime):
        return t.isoformat()
    return t


class AuditLogsResource:
    """Synchronous Audit Logs API resource."""

    def __init__(self, client: "SentryRelay") -> None:
        self._client = client

    def list(
        self,
        identity_id: Optional[str] = None,
        event_type: Optional[str] = None,
        from_time: Optional[Union[str, datetime]] = None,
        to_time: Optional[Union[str, datetime]] = None,
        limit: Optional[int] = None,
    ) -> List[AuditLog]:
        """Query sanitized Zero-PII audit events."""
        query: Dict[str, Any] = {}
        if identity_id is not None:
            query["identityId"] = identity_id
        if event_type is not None:
            query["eventType"] = event_type
        if from_time is not None:
            query["from"] = _format_time(from_time)
        if to_time is not None:
            query["to"] = _format_time(to_time)
        if limit is not None:
            query["limit"] = limit

        data = self._client.request("GET", "/api/v1/audit-logs", query=query)
        return [AuditLog.model_validate(item) for item in data.get("items", [])]


class AsyncAuditLogsResource:
    """Asynchronous Audit Logs API resource."""

    def __init__(self, client: "AsyncSentryRelay") -> None:
        self._client = client

    async def list(
        self,
        identity_id: Optional[str] = None,
        event_type: Optional[str] = None,
        from_time: Optional[Union[str, datetime]] = None,
        to_time: Optional[Union[str, datetime]] = None,
        limit: Optional[int] = None,
    ) -> List[AuditLog]:
        """Query sanitized Zero-PII audit events."""
        query: Dict[str, Any] = {}
        if identity_id is not None:
            query["identityId"] = identity_id
        if event_type is not None:
            query["eventType"] = event_type
        if from_time is not None:
            query["from"] = _format_time(from_time)
        if to_time is not None:
            query["to"] = _format_time(to_time)
        if limit is not None:
            query["limit"] = limit

        data = await self._client.request("GET", "/api/v1/audit-logs", query=query)
        return [AuditLog.model_validate(item) for item in data.get("items", [])]
