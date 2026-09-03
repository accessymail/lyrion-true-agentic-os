"""Unit tests for Lyrion operational world-state contracts."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lyrion.core.types import EventId
from lyrion.events.models import EventSensitivity, EventTrustLevel
from lyrion.state.models import StateRecord, StateValueType


def make_state(**overrides: object) -> StateRecord:
    """Create a valid baseline state record for tests."""
    now = datetime.now(UTC)

    values: dict[str, object] = {
        "state_id": "state_test_001",
        "subject": "lyri",
        "key": "current_mode",
        "value_type": StateValueType.STRING,
        "value": "development",
        "evidence_refs": (EventId("evt_test_001"),),
        "observed_at": now,
        "effective_at": now,
        "expires_at": now + timedelta(minutes=10),
        "confidence": 0.95,
        "trust_level": EventTrustLevel.SYSTEM,
        "sensitivity": EventSensitivity.INTERNAL,
        "revision": 1,
        "supersedes_state_id": None,
    }

    values.update(overrides)
    return StateRecord(**values)


def test_state_creation() -> None:
    """A valid state record should be accepted."""
    state = make_state()

    assert state.state_id == "state_test_001"
    assert state.subject == "lyri"
    assert state.key == "current_mode"
    assert state.value == "development"


def test_state_json_serialization() -> None:
    """A state record should serialize to a JSON-compatible form."""
    state = make_state()

    serialized = state.model_dump(mode="json")

    assert serialized["state_id"] == "state_test_001"
    assert serialized["value_type"] == "STRING"
    assert serialized["confidence"] == 0.95


def test_state_is_immutable() -> None:
    """State records must not be mutable after construction."""
    state = make_state()

    with pytest.raises(ValidationError):
        state.value = "changed"


def test_state_requires_timezone_aware_timestamps() -> None:
    """Naive timestamps must be rejected."""
    naive = datetime.now()

    with pytest.raises(ValidationError):
        make_state(observed_at=naive)


def test_state_rejects_invalid_expiry() -> None:
    """Expiry cannot precede effective time."""
    now = datetime.now(UTC)

    with pytest.raises(ValidationError):
        make_state(
            effective_at=now,
            expires_at=now - timedelta(seconds=1),
        )


def test_state_rejects_duplicate_evidence() -> None:
    """Evidence references must be unique."""
    with pytest.raises(ValidationError):
        make_state(
            evidence_refs=(
                EventId("evt_same"),
                EventId("evt_same"),
            )
        )


def test_state_requires_evidence() -> None:
    """Operational state must have at least one evidence reference."""
    with pytest.raises(ValidationError):
        make_state(evidence_refs=())


def test_confidence_is_bounded() -> None:
    """Confidence must remain within the inclusive 0..1 range."""
    with pytest.raises(ValidationError):
        make_state(confidence=1.1)

    with pytest.raises(ValidationError):
        make_state(confidence=-0.1)


def test_revision_must_be_positive() -> None:
    """State revisions start at one and cannot be zero or negative."""
    with pytest.raises(ValidationError):
        make_state(revision=0)


def test_state_expiry_behavior() -> None:
    """State should expire at or after its expiry timestamp."""
    now = datetime.now(UTC)

    state = make_state(
        observed_at=now,
        effective_at=now,
        expires_at=now + timedelta(seconds=1),
    )

    assert state.is_expired(now) is False
    assert state.is_expired(now + timedelta(seconds=2)) is True


def test_state_without_expiry_does_not_expire() -> None:
    """A state without an expiry remains non-expired."""
    now = datetime.now(UTC)

    state = make_state(
        observed_at=now,
        effective_at=now,
        expires_at=None,
    )

    assert state.is_expired(now) is False


def test_state_accepts_supersession_reference() -> None:
    """A state revision may explicitly supersede an earlier state."""
    state = make_state(
        revision=2,
        supersedes_state_id="state_test_000",
    )

    assert state.revision == 2
    assert state.supersedes_state_id == "state_test_000"
