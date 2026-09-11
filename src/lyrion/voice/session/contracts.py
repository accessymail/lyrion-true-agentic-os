"""Provider-neutral contracts for Lyrion voice session continuity."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VoiceSessionState(StrEnum):
    """Lifecycle state of a durable logical voice session."""

    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    RESUMABLE = "RESUMABLE"
    EXPIRED = "EXPIRED"
    CLOSED = "CLOSED"


class VoiceTurnStatus(StrEnum):
    """Lifecycle state of one persisted voice turn."""

    ACCEPTED = "ACCEPTED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class VoiceSessionErrorCode(StrEnum):
    """Normalized voice-session continuity failures."""

    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SESSION_NOT_RESUMABLE = "SESSION_NOT_RESUMABLE"
    SESSION_CLOSED = "SESSION_CLOSED"
    STALE_SESSION_REVISION = "STALE_SESSION_REVISION"
    INVALID_RESUME_REFERENCE = "INVALID_RESUME_REFERENCE"
    TURN_REPLAY = "TURN_REPLAY"
    TURN_OUT_OF_ORDER = "TURN_OUT_OF_ORDER"
    SESSION_STATE_CONFLICT = "SESSION_STATE_CONFLICT"
    CONTINUITY_POLICY_FAILURE = "CONTINUITY_POLICY_FAILURE"


class VoiceSession(BaseModel):
    """Immutable durable logical voice-session state."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )

    session_id: str = Field(min_length=1, max_length=200)
    correlation_id: str = Field(min_length=1, max_length=200)

    state: VoiceSessionState

    session_revision: int = Field(default=0, ge=0)
    next_turn_sequence: int = Field(default=0, ge=0)

    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    resumable_until: datetime | None = None

    continuity_version: int = Field(default=1, ge=1)

    @field_validator(
        "created_at",
        "last_activity_at",
        "expires_at",
        "resumable_until",
    )
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        """Require timezone-aware session timestamps."""
        if value is None:
            return None

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("session timestamps must be timezone-aware")

        return value


class VoiceTurn(BaseModel):
    """Immutable durable metadata for one voice conversation turn."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )

    session_id: str = Field(min_length=1, max_length=200)
    turn_id: str = Field(min_length=1, max_length=200)
    sequence: int = Field(ge=0)

    request_id: str = Field(min_length=1, max_length=200)

    created_at: datetime

    input_reference: str | None = Field(
        default=None,
        max_length=500,
    )
    output_reference: str | None = Field(
        default=None,
        max_length=500,
    )

    status: VoiceTurnStatus

    provenance: str = Field(min_length=1, max_length=500)

    @field_validator("created_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime,
    ) -> datetime:
        """Require a timezone-aware turn timestamp."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")

        return value


class VoiceSessionResumeRequest(BaseModel):
    """Request to resume an existing logical voice session."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )

    session_id: str = Field(min_length=1, max_length=200)
    resume_reference: str = Field(min_length=1, max_length=500)
    expected_revision: int = Field(ge=0)
    requested_at: datetime

    @field_validator("requested_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime,
    ) -> datetime:
        """Require a timezone-aware resume timestamp."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("requested_at must be timezone-aware")

        return value


class VoiceSessionResumeResult(BaseModel):
    """Result of a successful logical voice-session resume."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )

    session_id: str = Field(min_length=1, max_length=200)
    session_revision: int = Field(ge=0)
    state: VoiceSessionState
    next_turn_sequence: int = Field(ge=0)
    resumed_at: datetime

    @field_validator("resumed_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime,
    ) -> datetime:
        """Require a timezone-aware resume timestamp."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("resumed_at must be timezone-aware")

        return value


class VoiceSessionError(BaseModel):
    """Structured continuity-layer failure."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )

    session_id: str = Field(min_length=1, max_length=200)
    code: VoiceSessionErrorCode
    message: str = Field(min_length=1, max_length=1000)
    retryable: bool = False
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime,
    ) -> datetime:
        """Require a timezone-aware error timestamp."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")

        return value


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(UTC)
