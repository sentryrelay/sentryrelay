"""
Sentry Relay Data Models (Pydantic v2)
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class SentryRelayModel(BaseModel):
    """Base model configured for camelCase API responses and snake_case Python access."""
    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
        arbitrary_types_allowed=True,
    )


class CustomExtractionRule(SentryRelayModel):
    id: str
    name: str
    sender_contains: Optional[str] = Field(default=None, alias="senderContains")
    subject_contains: Optional[str] = Field(default=None, alias="subjectContains")
    otp_regex: Optional[str] = Field(default=None, alias="otpRegex")
    magic_link_regex: Optional[str] = Field(default=None, alias="magicLinkRegex")
    enabled: bool = True


class HumanFallbackConfig(SentryRelayModel):
    enabled: bool = False
    fallback_email: Optional[str] = Field(default=None, alias="fallbackEmail")
    fallback_webhook_url: Optional[str] = Field(default=None, alias="fallbackWebhookUrl")
    voice_forward_to_e164: Optional[str] = Field(default=None, alias="voiceForwardToE164")


class Identity(SentryRelayModel):
    id: str
    workspace_id: str = Field(default="", alias="workspaceId")
    name: str
    slug: Optional[str] = None
    status: Optional[str] = "active"
    email_handle: str = Field(default="", alias="emailHandle")
    email_domain: str = Field(default="", alias="emailDomain")
    email_address: str = Field(default="", alias="emailAddress")
    sms_phone_number: Optional[str] = Field(default=None, alias="smsPhoneNumber")
    telnyx_phone_number_id: Optional[str] = Field(default=None, alias="telnyxPhoneNumberId")
    sms_assigned_at: Optional[str] = Field(default=None, alias="smsAssignedAt")
    fallback: Optional[HumanFallbackConfig] = None
    custom_rules: List[CustomExtractionRule] = Field(default_factory=list, alias="customRules")
    totp_secret_count: int = Field(default=0, alias="totpSecretCount")
    last_event_at: Optional[str] = Field(default=None, alias="lastEventAt")
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")

    @property
    def phone_number(self) -> Optional[str]:
        """Convenient alias for sms_phone_number."""
        return self.sms_phone_number


class IdentityListResponse(SentryRelayModel):
    items: List[Identity] = Field(default_factory=list)
    next_cursor: Optional[str] = Field(default=None, alias="nextCursor")

    def __iter__(self):
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> Identity:
        return self.items[index]



class DeleteIdentityResponse(SentryRelayModel):
    deleted: bool
    id: str


class ProvisionSmsDidResponse(SentryRelayModel):
    identity: Identity
    phone_number: str = Field(alias="phoneNumber")
    telnyx_phone_number_id: str = Field(alias="telnyxPhoneNumberId")


class ReleaseSmsDidResponse(SentryRelayModel):
    released: bool
    phone_number: str = Field(alias="phoneNumber")
    identity_id: str = Field(alias="identityId")


class ExtractedLinkItem(SentryRelayModel):
    url: str
    anchor_text: str = Field(default="", alias="anchorText")

    @property
    def href(self) -> str:
        return self.url

    @property
    def text(self) -> str:
        return self.anchor_text


class ExtractedAuthEvent(SentryRelayModel):
    id: str
    identity_id: str = Field(alias="identityId")
    workspace_id: str = Field(default="", alias="workspaceId")
    channel: Literal["email", "sms"]
    classification: str
    otp_code: Optional[str] = Field(default=None, alias="otpCode")
    magic_link: Optional[str] = Field(default=None, alias="magicLink")
    sender: str
    subject: Optional[str] = None
    matched_rule: Optional[str] = Field(default=None, alias="matchedRule")
    confidence: float = 1.0
    received_at_ms: Optional[int] = Field(default=None, alias="receivedAtMs")
    received_at_iso: Optional[str] = Field(default=None, alias="receivedAtIso")
    received_at: Optional[str] = Field(default=None, alias="receivedAt")
    consumed: bool = False
    consumed_at_ms: Optional[int] = Field(default=None, alias="consumedAtMs")
    text_body: Optional[str] = Field(default=None, alias="textBody")
    html_body: Optional[str] = Field(default=None, alias="htmlBody")
    links: List[ExtractedLinkItem] = Field(default_factory=list)
    expires_at_ms: Optional[int] = Field(default=None, alias="expiresAtMs")
    wait_duration_ms: Optional[int] = Field(default=None, alias="waitDurationMs")


class WaitResponse(SentryRelayModel):
    matched: bool
    timed_out: bool = Field(default=False, alias="timedOut")
    event: Optional[ExtractedAuthEvent] = None
    wait_duration_ms: int = Field(default=0, alias="waitDurationMs")

    @property
    def otp_code(self) -> Optional[str]:
        """Convenient shortcut to extracted OTP code (e.g. '849201')."""
        return self.event.otp_code if self.event else None

    @property
    def code(self) -> Optional[str]:
        """Alias for otp_code."""
        return self.otp_code

    @property
    def magic_link(self) -> Optional[str]:
        """Convenient shortcut to extracted magic login link URL."""
        return self.event.magic_link if self.event else None

    @property
    def link(self) -> Optional[str]:
        """Alias for magic_link."""
        return self.magic_link

    @property
    def text_body(self) -> Optional[str]:
        """Convenient shortcut to sanitized message plain-text body."""
        return self.event.text_body if self.event else None

    @property
    def links(self) -> List[ExtractedLinkItem]:
        """Convenient shortcut to all extracted HTTP/HTTPS links in the message."""
        return self.event.links if self.event else []


class LatestResponse(WaitResponse):
    """Response from /latest endpoint, shares the same structure as WaitResponse."""
    pass


class TotpSecretMetadata(SentryRelayModel):
    id: str
    workspace_id: str = Field(default="", alias="workspaceId")
    identity_id: str = Field(default="", alias="identityId")
    issuer: str
    account_label: str = Field(alias="accountLabel")
    algorithm: str = "SHA1"
    digits: int = 6
    period: int = 30
    last_used_at: Optional[str] = Field(default=None, alias="lastUsedAt")
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")


class GeneratedTotpCode(SentryRelayModel):
    code: str
    remaining_seconds: int = Field(alias="remainingSeconds")
    next_code: Optional[str] = Field(default=None, alias="nextCode")
    period: int = 30
    digits: int = 6
    algorithm: str = "SHA1"
    secret_id: Optional[str] = Field(default=None, alias="secretId")
    issuer: Optional[str] = None
    account_label: Optional[str] = Field(default=None, alias="accountLabel")
    generated_at: Optional[str] = Field(default=None, alias="generatedAt")


class DeleteTotpSecretResponse(SentryRelayModel):
    deleted: bool
    secret_id: str = Field(alias="secretId")


class OutboundWebhook(SentryRelayModel):
    id: str
    workspace_id: str = Field(default="", alias="workspaceId")
    target_url: str = Field(alias="targetUrl")
    signing_secret: Optional[str] = Field(default=None, alias="signingSecret")
    events: List[str] = Field(default_factory=list)
    scoped_identity_ids: Optional[List[str]] = Field(default=None, alias="scopedIdentityIds")
    enabled: bool = True
    failure_count: int = Field(default=0, alias="failureCount")
    last_delivered_at: Optional[str] = Field(default=None, alias="lastDeliveredAt")
    created_at: Optional[str] = Field(default=None, alias="createdAt")


class DeleteWebhookResponse(SentryRelayModel):
    deleted: bool
    id: str


class AuditLog(SentryRelayModel):
    id: str
    workspace_id: str = Field(default="", alias="workspaceId")
    identity_id: Optional[str] = Field(default=None, alias="identityId")
    event_type: str = Field(alias="eventType")
    actor: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    expire_at_iso: Optional[str] = Field(default=None, alias="expireAtIso")
