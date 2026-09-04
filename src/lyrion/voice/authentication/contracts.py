"""Provider-neutral contracts for voice authentication."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class VoiceAuthenticationMethod(StrEnum):
    """Supported provider-neutral voice authentication methods."""

    SPEAKER_VERIFICATION = "SPEAKER_VERIFICATION"


class VoiceAuthenticationStatus(StrEnum):
    """Current outcome of a voice authentication attempt."""

    UNKNOWN = "UNKNOWN"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    STEP_UP_REQUIRED = "STEP_UP_REQUIRED"


class VoiceAuthenticationAssurance(StrEnum):
    """Assurance level established by voice authentication."""

    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class VoiceAuthenticationRequest(BaseModel):
    """Immutable request to authenticate a voice claimant."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str = Field(min_length=1, max_length=200)
    session_id: str = Field(min_length=1, max_length=200)
    claimed_principal_id: str = Field(min_length=1, max_length=500)
    method: VoiceAuthenticationMethod
    correlation_id: str = Field(min_length=1, max_length=200)
    idempotency_key: str = Field(min_length=1, max_length=500)
    requested_at: datetime
    expires_at: datetime

    @field_validator(
        "request_id",
        "session_id",
        "claimed_principal_id",
        "correlation_id",
        "idempotency_key",
    )
    @classmethod
    def require_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("identifier fields must not be blank")
        return value

    @field_validator("requested_at", "expires_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("authentication timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_temporal_bounds(self) -> VoiceAuthenticationRequest:
        if self.expires_at < self.requested_at:
            raise ValueError("expires_at cannot be earlier than requested_at")
        return self


class VoiceAuthenticationEvidence(BaseModel):
    """Immutable opaque evidence reference produced by a verifier."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str = Field(min_length=1, max_length=500)
    method: VoiceAuthenticationMethod
    assurance: VoiceAuthenticationAssurance
    provider_id: str = Field(min_length=1, max_length=200)
    reference: str = Field(min_length=1, max_length=500)
    observed_at: datetime

    @field_validator("evidence_id", "provider_id", "reference")
    @classmethod
    def require_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("evidence identifiers must not be blank")
        return value

    @field_validator("observed_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evidence timestamp must be timezone-aware")
        return value


class VoiceAuthenticationResult(BaseModel):
    """Immutable provider-neutral authentication result.

    Authentication state never grants authorization or execution authority.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str = Field(min_length=1, max_length=200)
    session_id: str = Field(min_length=1, max_length=200)
    correlation_id: str = Field(min_length=1, max_length=200)
    idempotency_key: str = Field(min_length=1, max_length=500)
    status: VoiceAuthenticationStatus
    assurance: VoiceAuthenticationAssurance
    claimed_principal_id: str = Field(min_length=1, max_length=500)
    authenticated_principal_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )
    evidence: VoiceAuthenticationEvidence | None = None
    evaluated_at: datetime
    expires_at: datetime | None = None
    reason: str = Field(min_length=1, max_length=4000)

    @field_validator(
        "request_id",
        "session_id",
        "correlation_id",
        "idempotency_key",
        "claimed_principal_id",
        "reason",
    )
    @classmethod
    def require_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("result fields must not be blank")
        return value

    @field_validator("authenticated_principal_id")
    @classmethod
    def validate_authenticated_principal(
        cls,
        value: str | None,
    ) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("authenticated_principal_id must not be blank")
        return value

    @field_validator("evaluated_at", "expires_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return None

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("authentication timestamps must be timezone-aware")

        return value

    @model_validator(mode="after")
    def validate_security_invariants(self) -> VoiceAuthenticationResult:
        if self.expires_at is not None and self.expires_at < self.evaluated_at:
            raise ValueError("authentication expiry cannot precede evaluation")

        if self.status is VoiceAuthenticationStatus.VERIFIED:
            if self.assurance is VoiceAuthenticationAssurance.NONE:
                raise ValueError("VERIFIED results require non-NONE assurance")

            if self.authenticated_principal_id is None:
                raise ValueError(
                    "VERIFIED results require authenticated_principal_id"
                )

            if self.evidence is None:
                raise ValueError("VERIFIED results require evidence")

            if self.expires_at is None:
                raise ValueError("VERIFIED results require an expiry")

            if self.authenticated_principal_id != self.claimed_principal_id:
                raise ValueError(
                    "authenticated principal must match claimed principal"
                )

            if self.evidence.assurance is not self.assurance:
                raise ValueError("result/evidence assurance must match")

        else:
            if self.authenticated_principal_id is not None:
                raise ValueError(
                    "non-VERIFIED results cannot bind an authenticated principal"
                )

            if self.assurance is not VoiceAuthenticationAssurance.NONE:
                raise ValueError("non-VERIFIED results must use NONE assurance")

        if self.evidence is not None:
            if self.evidence.method is not VoiceAuthenticationMethod.SPEAKER_VERIFICATION:
                raise ValueError("unsupported evidence method")

        return self

    @classmethod
    def from_request(
        cls,
        *,
        request: VoiceAuthenticationRequest,
        status: VoiceAuthenticationStatus,
        assurance: VoiceAuthenticationAssurance,
        authenticated_principal_id: str | None,
        evidence: VoiceAuthenticationEvidence | None,
        evaluated_at: datetime,
        expires_at: datetime | None,
        reason: str,
    ) -> VoiceAuthenticationResult:
        evaluated_at_utc = evaluated_at.astimezone(UTC)
        expires_at_utc = (
            None if expires_at is None else expires_at.astimezone(UTC)
        )

        # A non-VERIFIED result may legitimately be evaluated before the
        # requested validity window begins (for example, rejecting a
        # not-yet-valid request). A VERIFIED result must never predate the
        # request itself.
        if (
            status is VoiceAuthenticationStatus.VERIFIED
            and evaluated_at_utc < request.requested_at.astimezone(UTC)
        ):
            raise ValueError(
                "verified evaluation cannot precede authentication request"
            )

        if expires_at_utc is not None and expires_at_utc > request.expires_at.astimezone(
            UTC
        ):
            raise ValueError("authentication expiry cannot exceed request expiry")

        if evidence is not None and evidence.method is not request.method:
            raise ValueError("evidence method must match request method")

        return cls(
            request_id=request.request_id,
            session_id=request.session_id,
            correlation_id=request.correlation_id,
            idempotency_key=request.idempotency_key,
            status=status,
            assurance=assurance,
            claimed_principal_id=request.claimed_principal_id,
            authenticated_principal_id=authenticated_principal_id,
            evidence=evidence,
            evaluated_at=evaluated_at_utc,
            expires_at=expires_at_utc,
            reason=reason,
        )

    @classmethod
    def verified(
        cls,
        *,
        request: VoiceAuthenticationRequest,
        authenticated_principal_id: str,
        evidence: VoiceAuthenticationEvidence,
        evaluated_at: datetime,
        expires_at: datetime,
        reason: str,
    ) -> VoiceAuthenticationResult:
        return cls.from_request(
            request=request,
            status=VoiceAuthenticationStatus.VERIFIED,
            assurance=evidence.assurance,
            authenticated_principal_id=authenticated_principal_id,
            evidence=evidence,
            evaluated_at=evaluated_at,
            expires_at=expires_at,
            reason=reason,
        )
