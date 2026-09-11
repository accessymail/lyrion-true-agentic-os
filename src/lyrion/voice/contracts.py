"""Provider-neutral Voice Identity contracts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class VoiceIdentityStatus(StrEnum):
    """Outcome of a speaker identity lookup."""

    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    INDETERMINATE = "INDETERMINATE"





class VoiceEvidenceQuality(StrEnum):
    """Quality classification for identity evidence."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class VoiceIdentityEvidence(BaseModel):
    """Immutable evidence supporting a voice identity assessment."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_ref: str = Field(min_length=1, max_length=1000)
    quality: VoiceEvidenceQuality
    duration_seconds: float = Field(gt=0.0, le=3600.0)
    signal_confidence: float = Field(ge=0.0, le=1.0)


    @field_validator("evidence_ref")
    @classmethod
    def validate_evidence_ref(cls, value: str) -> str:
        """Reject whitespace-only evidence references."""
        if not value.strip():
            raise ValueError("evidence_ref must not be blank")
        return value


class VoiceIdentityRequest(BaseModel):
    """Immutable request for speaker identity resolution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str = Field(min_length=1, max_length=200)
    audio_ref: str = Field(min_length=1, max_length=1000)
    session_id: str | None = Field(default=None, min_length=1, max_length=200)


class VoiceIdentityMatch(BaseModel):
    """Immutable provider-neutral speaker identity result."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str = Field(min_length=1, max_length=200)
    status: VoiceIdentityStatus
    identity_id: str | None = Field(default=None, min_length=1, max_length=200)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_ref: str | None = Field(default=None, min_length=1, max_length=1000)
    provider: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_identity_consistency(self) -> VoiceIdentityMatch:
        """Enforce semantic consistency between status and identity ID."""
        if self.status is VoiceIdentityStatus.KNOWN and self.identity_id is None:
            raise ValueError("KNOWN identity results require identity_id")
        if self.status is not VoiceIdentityStatus.KNOWN and self.identity_id is not None:
            raise ValueError("only KNOWN identity results may contain identity_id")
        return self



class VoiceIdentityProfileStatus(StrEnum):
    """Lifecycle state of a registered voice identity profile."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    REVOKED = "REVOKED"


class VoiceIdentityProfile(BaseModel):
    """Immutable provider-neutral voice identity profile."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    identity_id: str = Field(min_length=1, max_length=200)
    status: VoiceIdentityProfileStatus
    representation_refs: tuple[str, ...] = Field(default_factory=tuple)
    enrolled_at: datetime
    updated_at: datetime
    provenance: str = Field(min_length=1, max_length=1000)
    revision: int = Field(default=1, ge=1)

    @field_validator("identity_id", "provenance")
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        """Reject whitespace-only profile text fields."""
        if not value.strip():
            raise ValueError("profile text fields must not be blank")
        return value

    @field_validator("representation_refs")
    @classmethod
    def validate_representation_refs(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Reject blank representation references."""
        if any(not ref.strip() for ref in value):
            raise ValueError("representation references must not be blank")
        return value

    @model_validator(mode="after")
    def validate_profile(self) -> VoiceIdentityProfile:
        """Validate lifecycle timestamp and registration invariants."""
        if self.enrolled_at.tzinfo is None or self.enrolled_at.utcoffset() is None:
            raise ValueError("enrolled_at must be timezone-aware")
        if self.updated_at.tzinfo is None or self.updated_at.utcoffset() is None:
            raise ValueError("updated_at must be timezone-aware")
        if self.updated_at < self.enrolled_at:
            raise ValueError("updated_at cannot be earlier than enrolled_at")
        if self.status is VoiceIdentityProfileStatus.ACTIVE and not self.representation_refs:
            raise ValueError("ACTIVE profiles require at least one representation reference")
        if len(set(self.representation_refs)) != len(self.representation_refs):
            raise ValueError("representation references must be unique")
        return self


class VoiceIdentityProfileUpdateRequest(BaseModel):
    """Immutable request for a controlled voice identity profile update."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    identity_id: str = Field(min_length=1, max_length=200)
    expected_revision: int = Field(ge=1)
    representation_refs: tuple[str, ...] | None = None
    provenance: str | None = Field(default=None, min_length=1, max_length=1000)

    @field_validator("identity_id", "provenance")
    @classmethod
    def validate_text_fields(cls, value: str | None) -> str | None:
        """Reject whitespace-only supplied text fields."""
        if value is not None and not value.strip():
            raise ValueError("supplied profile text fields must not be blank")
        return value

    @field_validator("representation_refs")
    @classmethod
    def validate_representation_refs(
        cls,
        value: tuple[str, ...] | None,
    ) -> tuple[str, ...] | None:
        """Reject blank or duplicate supplied representation references."""
        if value is None:
            return None
        if any(not ref.strip() for ref in value):
            raise ValueError("representation references must not be blank")
        if len(set(value)) != len(value):
            raise ValueError("representation references must be unique")
        return value

class VoiceIdentityProvider(Protocol):
    """Provider-neutral boundary for speaker identity resolution."""

    async def identify(
        self,
        request: VoiceIdentityRequest,
    ) -> VoiceIdentityMatch:
        """Resolve the speaker identity for one request."""
