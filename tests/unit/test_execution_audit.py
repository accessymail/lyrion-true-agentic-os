"""Adversarial tests for execution audit and evidence logging."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest

from lyrion.observability.execution_audit import (
    ExecutionAuditEvent,
    ExecutionAuditLog,
)


def test_empty_log_is_valid() -> None:
    """A new audit log should contain no events."""
    log = ExecutionAuditLog()

    assert log.size == 0
    assert log.events() == ()
    assert log.verify_chain() is True


def test_append_creates_immutable_event() -> None:
    """Appending an event should produce immutable evidence."""
    log = ExecutionAuditLog()
    timestamp = datetime.now(UTC)

    event = log.append(
        execution_id="exec-audit-001",
        event_type="ADMITTED",
        actor="aegis",
        details={"policy_version": "aegis-policy-v1"},
        occurred_at=timestamp,
    )

    assert event.sequence == 1
    assert event.execution_id == "exec-audit-001"
    assert event.event_type == "ADMITTED"
    assert event.actor == "aegis"
    assert event.previous_hash is None
    assert len(event.event_hash) == 64

    with pytest.raises(AttributeError):
        event.sequence = 99  # type: ignore[misc]


def test_second_event_links_to_first() -> None:
    """The second event must point to the first event hash."""
    log = ExecutionAuditLog()

    first = log.append(
        execution_id="exec-audit-001",
        event_type="ADMITTED",
        actor="gateway",
    )
    second = log.append(
        execution_id="exec-audit-001",
        event_type="STARTED",
        actor="runtime",
    )

    assert second.sequence == 2
    assert second.previous_hash == first.event_hash
    assert first.event_hash != second.event_hash
    assert log.verify_chain() is True


def test_chain_hash_is_deterministic() -> None:
    """Identical event inputs should produce identical hashes."""
    timestamp = datetime.now(UTC)
    details = {
        "capability_id": "development.prepare",
        "policy_version": "aegis-policy-v1",
    }

    first = ExecutionAuditEvent.calculate_hash(
        sequence=1,
        execution_id="exec-001",
        event_type="ADMITTED",
        occurred_at=timestamp,
        actor="gateway",
        details=details,
        previous_hash=None,
    )

    second = ExecutionAuditEvent.calculate_hash(
        sequence=1,
        execution_id="exec-001",
        event_type="ADMITTED",
        occurred_at=timestamp,
        actor="gateway",
        details=details,
        previous_hash=None,
    )

    assert first == second


def test_different_details_change_hash() -> None:
    """Changing evidence details must change the event hash."""
    timestamp = datetime.now(UTC)

    first = ExecutionAuditEvent.calculate_hash(
        sequence=1,
        execution_id="exec-001",
        event_type="ADMITTED",
        occurred_at=timestamp,
        actor="gateway",
        details={"risk": "LOW"},
        previous_hash=None,
    )

    second = ExecutionAuditEvent.calculate_hash(
        sequence=1,
        execution_id="exec-001",
        event_type="ADMITTED",
        occurred_at=timestamp,
        actor="gateway",
        details={"risk": "HIGH"},
        previous_hash=None,
    )

    assert first != second


def test_events_returns_immutable_snapshot() -> None:
    """The caller cannot mutate the audit log through events()."""
    log = ExecutionAuditLog()

    log.append(
        execution_id="exec-001",
        event_type="ADMITTED",
        actor="gateway",
    )

    snapshot = log.events()

    assert isinstance(snapshot, tuple)
    assert len(snapshot) == 1
    assert log.size == 1


def test_events_for_filters_by_execution() -> None:
    """events_for() should isolate evidence by execution ID."""
    log = ExecutionAuditLog()

    log.append(
        execution_id="exec-001",
        event_type="ADMITTED",
        actor="gateway",
    )
    log.append(
        execution_id="exec-002",
        event_type="ADMITTED",
        actor="gateway",
    )
    log.append(
        execution_id="exec-001",
        event_type="STARTED",
        actor="runtime",
    )

    events = log.events_for("exec-001")

    assert len(events) == 2
    assert all(
        event.execution_id == "exec-001"
        for event in events
    )


def test_blank_execution_id_is_rejected() -> None:
    """Execution identifiers must be non-empty."""
    with pytest.raises(ValueError):
        ExecutionAuditLog().append(
            execution_id="",
            event_type="ADMITTED",
            actor="gateway",
        )


def test_blank_event_type_is_rejected() -> None:
    """Event types must be non-empty."""
    with pytest.raises(ValueError):
        ExecutionAuditLog().append(
            execution_id="exec-001",
            event_type="",
            actor="gateway",
        )


def test_blank_actor_is_rejected() -> None:
    """Audit actors must be non-empty."""
    with pytest.raises(ValueError):
        ExecutionAuditLog().append(
            execution_id="exec-001",
            event_type="ADMITTED",
            actor="",
        )


def test_naive_timestamp_is_rejected() -> None:
    """Audit timestamps must be timezone-aware."""
    with pytest.raises(ValueError):
        ExecutionAuditLog().append(
            execution_id="exec-001",
            event_type="ADMITTED",
            actor="gateway",
            occurred_at=datetime.now(),
        )


def test_execution_events_preserve_order() -> None:
    """Events must retain deterministic append order."""
    log = ExecutionAuditLog()
    started = datetime.now(UTC)

    for index in range(3):
        log.append(
            execution_id="exec-001",
            event_type=f"EVENT_{index}",
            actor="test",
            occurred_at=started + timedelta(seconds=index),
        )

    events = log.events()

    assert [event.sequence for event in events] == [1, 2, 3]
    assert [
        event.event_type
        for event in events
    ] == [
        "EVENT_0",
        "EVENT_1",
        "EVENT_2",
    ]
    assert log.verify_chain() is True


def test_chain_integrity_detects_tampering() -> None:
    """Changing an event should invalidate the hash chain."""
    log = ExecutionAuditLog()

    log.append(
        execution_id="exec-001",
        event_type="ADMITTED",
        actor="gateway",
        details={"policy": "v1"},
    )
    log.append(
        execution_id="exec-001",
        event_type="STARTED",
        actor="runtime",
    )

    original = log._events[0]
    forged = ExecutionAuditEvent(
        sequence=original.sequence,
        execution_id=original.execution_id,
        event_type=original.event_type,
        occurred_at=original.occurred_at,
        actor=original.actor,
        details={"policy": "forged"},
        previous_hash=original.previous_hash,
        event_hash=original.event_hash,
    )

    log._events[0] = forged

    assert log.verify_chain() is False


def test_hash_chain_detects_event_reordering() -> None:
    """Reordering events must invalidate the chain."""
    log = ExecutionAuditLog()

    log.append(
        execution_id="exec-001",
        event_type="ADMITTED",
        actor="gateway",
    )
    log.append(
        execution_id="exec-001",
        event_type="STARTED",
        actor="runtime",
    )

    log._events.reverse()

    assert log.verify_chain() is False


def test_clear_explicitly_removes_events() -> None:
    """Explicit clear should remove all in-memory evidence."""
    log = ExecutionAuditLog()

    log.append(
        execution_id="exec-001",
        event_type="ADMITTED",
        actor="gateway",
    )

    assert log.size == 1

    log.clear()

    assert log.size == 0
    assert log.events() == ()
    assert log.verify_chain() is True


def test_concurrent_appends_have_unique_sequences() -> None:
    """Concurrent appends must remain atomic and ordered."""
    log = ExecutionAuditLog()

    def append_event(index: int) -> ExecutionAuditEvent:
        """Append one concurrent audit event."""
        return log.append(
            execution_id=f"exec-{index}",
            event_type="CONCURRENT",
            actor="test",
        )

    with ThreadPoolExecutor(max_workers=16) as executor:
        events = list(
            executor.map(
                append_event,
                range(64),
            )
        )

    sequences = sorted(
        event.sequence
        for event in events
    )

    assert sequences == list(range(1, 65))
    assert log.size == 64
    assert log.verify_chain() is True


def test_execution_id_normalization_is_consistent() -> None:
    """Surrounding execution-ID whitespace should be normalized."""
    log = ExecutionAuditLog()

    event = log.append(
        execution_id="  exec-001  ",
        event_type=" ADMITTED ",
        actor=" gateway ",
    )

    assert event.execution_id == "exec-001"
    assert event.event_type == "ADMITTED"
    assert event.actor == "gateway"


def test_audit_evidence_can_capture_security_dimensions() -> None:
    """Audit events can carry key security evidence dimensions."""
    log = ExecutionAuditLog()

    event = log.append(
        execution_id="exec-security-001",
        event_type="AUTHORIZATION_DECISION",
        actor="aegis",
        details={
            "request_id": "request-001",
            "capability_id": "development.prepare",
            "target_scope": "lyrion/project/src",
            "policy_version": "aegis-policy-v1",
            "decision": "ALLOWED",
            "risk_level": "LOW",
            "network_access": False,
        },
    )

    assert event.details["request_id"] == "request-001"
    assert event.details["capability_id"] == "development.prepare"
    assert event.details["policy_version"] == "aegis-policy-v1"
    assert event.details["decision"] == "ALLOWED"
    assert log.verify_chain() is True


def test_empty_details_are_supported() -> None:
    """An audit event may contain no additional details."""
    log = ExecutionAuditLog()

    event = log.append(
        execution_id="exec-001",
        event_type="TERMINATED",
        actor="runtime",
    )

    assert dict(event.details) == {}
    assert log.verify_chain() is True
