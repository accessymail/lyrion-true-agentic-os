"""Validated event contracts for Lyrion Intelligence OS."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lyrion.core.types import (
    CorrelationId,
    EventId,
    IdempotencyKey,
)


class EventSensitivity(StrEnum):
    """Sensitivity classification assigned to an event."""

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    SENSITIVE = "SENSITIVE"
    HIGHLY_SENSITIVE = "HIGHLY_SENSITIVE"


class EventTrustLevel(StrEnum):
    """Trust classification for an event source or observation."""

    UNTRUSTED = "UNTRUSTED"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    SYSTEM = "SYSTEM"


class Event(BaseModel):
    """Immutable, validated event envelope entering the Lyrion event fabric."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )

    event_id: EventId
    event_type: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=200)

    timestamp: datetime
    observed_at: datetime

    subject: str | None = Field(default=None, max_length=500)
    payload: dict[str, Any] = Field(default_factory=dict)

    sensitivity: EventSensitivity = EventSensitivity.INTERNAL
    provenance: str = Field(min_length=1, max_length=1000)
    trust_level: EventTrustLevel = EventTrustLevel.UNTRUSTED

    correlation_id: CorrelationId | None = None
    idempotency_key: IdempotencyKey

    @field_validator("timestamp", "observed_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        """Require timezone-aware UTC-normalizable timestamps."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value

    @field_validator("payload")
    @classmethod
    def validate_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Ensure payload remains a JSON-like object boundary."""
        if not isinstance(value, dict):
            raise ValueError("payload must be an object")
        return value

    @field_validator("observed_at")
    @classmethod
    def observed_at_not_before_timestamp(
        cls,
        value: datetime,
        info: Any,
    ) -> datetime:
        """Reject observations that precede the event timestamp."""
        timestamp = info.data.get("timestamp")
        if timestamp is not None and value < timestamp:
            raise ValueError("observed_at cannot be earlier than timestamp")
        return value

    def normalized_timestamps(self) -> tuple[datetime, datetime]:
        """Return event and observation timestamps normalized to UTC."""
        return (
            self.timestamp.astimezone(UTC),
            self.observed_at.astimezone(UTC),
        )
