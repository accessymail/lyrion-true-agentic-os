"""Provider-neutral contracts for streaming voice interaction."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from math import isfinite

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lyrion.voice.providers import VoiceOutputFormat


class VoiceStreamState(StrEnum):
    """Lifecycle state of one streaming voice interaction."""

    IDLE = "IDLE"
    STARTING = "STARTING"
    STREAMING = "STREAMING"
    TURN_ACTIVE = "TURN_ACTIVE"
    PROCESSING = "PROCESSING"
    OUTPUT_STREAMING = "OUTPUT_STREAMING"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class VoiceStreamErrorCode(StrEnum):
    """Normalized streaming failure categories."""

    INVALID_STATE = "INVALID_STATE"
    INVALID_INPUT = "INVALID_INPUT"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    OUTPUT_INVALID = "OUTPUT_INVALID"
    UNSUPPORTED_CAPABILITY = "UNSUPPORTED_CAPABILITY"
    BUFFER_LIMIT = "BUFFER_LIMIT"
    INTERRUPTED = "INTERRUPTED"


class VoiceInterruptionReason(StrEnum):
    """Normalized reasons for interrupting an active voice turn."""

    BARGE_IN = "BARGE_IN"


class VoiceInterruptionStatus(StrEnum):
    """Outcome state of an interruption request."""

    REQUESTED = "REQUESTED"
    ALREADY_INTERRUPTED = "ALREADY_INTERRUPTED"


class VoiceInterruptionRequest(BaseModel):
    """Immutable request to interrupt one active voice turn."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=200)
    reason: VoiceInterruptionReason = VoiceInterruptionReason.BARGE_IN
    requested_at: datetime

    @field_validator("requested_at")
    @classmethod
    def timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("requested_at must be timezone-aware")
        return value


class VoiceInterruptionResult(BaseModel):
    """Immutable result for a voice interruption request."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=200)
    status: VoiceInterruptionStatus
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value


class VoiceInputChunk(BaseModel):
    """Validated inbound audio chunk."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str = Field(min_length=1, max_length=200)
    sequence: int = Field(ge=0)
    audio: bytes = Field(min_length=1)
    captured_at: datetime

    @field_validator("captured_at")
    @classmethod
    def timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware")
        return value


class VoiceOutputChunk(BaseModel):
    """Validated outbound audio chunk."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=200)
    sequence: int = Field(ge=0)
    audio: bytes = Field(min_length=1)
    output_format: VoiceOutputFormat


class VoiceStreamSession(BaseModel):
    """Immutable snapshot of streaming session state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str = Field(min_length=1, max_length=200)
    correlation_id: str = Field(min_length=1, max_length=200)
    state: VoiceStreamState
    next_input_sequence: int = Field(default=0, ge=0)
    started_at: datetime
    updated_at: datetime

    @field_validator("started_at", "updated_at")
    @classmethod
    def timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("session timestamps must be timezone-aware")
        return value


class VoiceStreamError(BaseModel):
    """Structured provider-neutral stream error."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str = Field(min_length=1, max_length=200)
    code: VoiceStreamErrorCode
    message: str = Field(min_length=1, max_length=1000)
    retryable: bool = False
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value


class VoiceStreamMetrics(BaseModel):
    """Minimal metrics for one streaming session."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str = Field(min_length=1, max_length=200)
    input_chunks: int = Field(default=0, ge=0)
    output_chunks: int = Field(default=0, ge=0)
    turns_completed: int = Field(default=0, ge=0)
    provider_failures: int = Field(default=0, ge=0)
    cancellations: int = Field(default=0, ge=0)
    interruptions: int = Field(default=0, ge=0)
    duration_seconds: float = Field(default=0.0, ge=0.0)
    first_output_latency_seconds: float | None = Field(
        default=None,
        ge=0.0,
    )

    @field_validator("duration_seconds", "first_output_latency_seconds")
    @classmethod
    def require_finite_metrics(cls, value: float | None) -> float | None:
        if value is not None and not isfinite(value):
            raise ValueError("stream metrics must be finite")
        return value


def utc_now() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(UTC)
