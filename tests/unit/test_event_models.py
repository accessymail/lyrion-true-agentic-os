"""Unit tests for Lyrion event contracts."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lyrion.core.types import CorrelationId, EventId, IdempotencyKey
from lyrion.events.models import (
    Event,
    EventSensitivity,
    EventTrustLevel,
)


def make_event(**overrides: object) -> Event:
    """Create a valid baseline event for tests."""
    now = datetime.now(UTC)

    values: dict[str, object] = {
        "event_id": EventId("evt_test_001"),
        "event_type": "test.created",
        "source": "unit-test",
        "timestamp": now,
        "observed_at": now,
        "subject": "test",
        "payload": {"message": "hello"},
        "sensitivity": EventSensitivity.INTERNAL,
        "provenance": "unit-test",
        "trust_level": EventTrustLevel.SYSTEM,
        "correlation_id": CorrelationId("corr_test_001"),
        "idempotency_key": IdempotencyKey("idem_test_001"),
    }

    values.update(overrides)
    return Event(**values)


def test_event_creation() -> None:
    """A valid event should be accepted."""
    event = make_event()

    assert event.event_id == "evt_test_001"
    assert event.event_type == "test.created"
    assert event.source == "unit-test"
    assert event.payload == {"message": "hello"}


def test_event_json_serialization() -> None:
    """An event should serialize to a JSON-compatible representation."""
    event = make_event()

    serialized = event.model_dump(mode="json")

    assert serialized["event_id"] == "evt_test_001"
    assert serialized["sensitivity"] == "INTERNAL"
    assert serialized["trust_level"] == "SYSTEM"


def test_event_is_immutable() -> None:
    """Event fields must not be mutable after construction."""
    event = make_event()

    with pytest.raises(ValidationError):
        event.source = "modified"


def test_event_requires_timezone_aware_timestamps() -> None:
    """Naive datetimes must be rejected."""
    naive = datetime.now()

    with pytest.raises(ValidationError):
        make_event(timestamp=naive)


def test_observed_at_cannot_precede_event_timestamp() -> None:
    """Observation time cannot be earlier than event time."""
    now = datetime.now(UTC)

    with pytest.raises(ValidationError):
        make_event(
            timestamp=now,
            observed_at=now - timedelta(seconds=1),
        )


def test_event_rejects_unknown_fields() -> None:
    """Unexpected event fields must be rejected."""
    with pytest.raises(ValidationError):
        make_event(unexpected_field="not-allowed")


def test_event_defaults() -> None:
    """Optional event fields should receive their defined defaults."""
    event = make_event(
        subject=None,
        payload={},
        sensitivity=EventSensitivity.INTERNAL,
        trust_level=EventTrustLevel.UNTRUSTED,
        correlation_id=None,
    )

    assert event.subject is None
    assert event.payload == {}
    assert event.sensitivity is EventSensitivity.INTERNAL
    assert event.trust_level is EventTrustLevel.UNTRUSTED
    assert event.correlation_id is None


def test_event_timestamps_can_be_normalized_to_utc() -> None:
    """Timezone-aware timestamps should normalize cleanly to UTC."""
    event = make_event()

    timestamp, observed_at = event.normalized_timestamps()

    assert timestamp.tzinfo is UTC
    assert observed_at.tzinfo is UTC
