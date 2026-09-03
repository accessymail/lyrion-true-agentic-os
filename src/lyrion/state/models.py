"""Operational world-state contracts for Lyrion Intelligence OS."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lyrion.core.types import EventId
from lyrion.events.models import EventSensitivity, EventTrustLevel


class StateValueType(StrEnum):
    """Supported categories for operational state values."""

    STRING = "STRING"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    OBJECT = "OBJECT"
    ARRAY = "ARRAY"
    NULL = "NULL"


class StateRecord(BaseModel):
    """Immutable operational state derived from supported evidence."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )

    state_id: str = Field(min_length=1, max_length=200)
    subject: str = Field(min_length=1, max_length=500)
    key: str = Field(min_length=1, max_length=200)

    value_type: StateValueType
    value: object

    evidence_refs: tuple[EventId, ...] = Field(min_length=1)

    observed_at: datetime
    effective_at: datetime
    expires_at: datetime | None = None

    confidence: float = Field(ge=0.0, le=1.0)

    trust_level: EventTrustLevel
    sensitivity: EventSensitivity

    revision: int = Field(default=1, ge=1)

    supersedes_state_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    @field_validator("observed_at", "effective_at", "expires_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        """Require timezone-aware timestamps."""
        if value is None:
            return None

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("state timestamps must be timezone-aware")

        return value

    @field_validator("expires_at")
    @classmethod
    def validate_expiry(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        """Ensure expiry is not earlier than effective time."""
        if value is None:
            return None

        data = getattr(info, "data", {})
        effective_at = data.get("effective_at")

        if effective_at is not None and value < effective_at:
            raise ValueError("expires_at cannot be earlier than effective_at")

        return value

    @field_validator("evidence_refs")
    @classmethod
    def validate_evidence_refs(
        cls,
        value: tuple[EventId, ...],
    ) -> tuple[EventId, ...]:
        """Reject empty and duplicate evidence references."""
        if not value:
            raise ValueError("at least one evidence reference is required")

        if len(set(value)) != len(value):
            raise ValueError("evidence references must be unique")

        return value

    def is_expired(self, now: datetime | None = None) -> bool:
        """Return whether this state record has expired."""
        current_time = now or datetime.now(UTC)

        if current_time.tzinfo is None or current_time.utcoffset() is None:
            raise ValueError("now must be timezone-aware")

        return self.expires_at is not None and current_time >= self.expires_at
