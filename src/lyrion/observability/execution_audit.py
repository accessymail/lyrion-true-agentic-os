"""Immutable execution audit and evidence records for Lyrion."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from threading import Lock
from typing import Any


@dataclass(frozen=True, slots=True)
class ExecutionAuditEvent:
    """Immutable, hash-addressed execution evidence event."""

    sequence: int
    execution_id: str
    event_type: str
    occurred_at: datetime
    actor: str
    details: Mapping[str, Any]
    previous_hash: str | None
    event_hash: str

    @staticmethod
    def calculate_hash(
        *,
        sequence: int,
        execution_id: str,
        event_type: str,
        occurred_at: datetime,
        actor: str,
        details: Mapping[str, Any],
        previous_hash: str | None,
    ) -> str:
        """Calculate the deterministic hash for an audit event."""
        canonical = (
            f"{sequence}|"
            f"{execution_id}|"
            f"{event_type}|"
            f"{occurred_at.astimezone(UTC).isoformat()}|"
            f"{actor}|"
            f"{repr(sorted(details.items()))}|"
            f"{previous_hash or ''}"
        )

        return sha256(
            canonical.encode("utf-8"),
        ).hexdigest()


class ExecutionAuditLog:
    """Thread-safe append-only in-memory execution evidence log."""

    def __init__(self) -> None:
        """Initialize an empty audit log."""
        self._events: list[ExecutionAuditEvent] = []
        self._lock = Lock()

    @property
    def size(self) -> int:
        """Return the current number of audit events."""
        with self._lock:
            return len(self._events)

    def append(
        self,
        *,
        execution_id: str,
        event_type: str,
        actor: str,
        details: Mapping[str, Any] | None = None,
        occurred_at: datetime | None = None,
    ) -> ExecutionAuditEvent:
        """Append one immutable event to the evidence chain."""
        normalized_execution_id = execution_id.strip()
        normalized_event_type = event_type.strip()
        normalized_actor = actor.strip()

        if not normalized_execution_id:
            raise ValueError("execution_id must not be empty")

        if not normalized_event_type:
            raise ValueError("event_type must not be empty")

        if not normalized_actor:
            raise ValueError("actor must not be empty")

        timestamp = occurred_at or datetime.now(UTC)

        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")

        normalized_details: dict[str, Any] = dict(details or {})

        with self._lock:
            sequence = len(self._events) + 1
            previous_hash = (
                self._events[-1].event_hash
                if self._events
                else None
            )

            event_hash = ExecutionAuditEvent.calculate_hash(
                sequence=sequence,
                execution_id=normalized_execution_id,
                event_type=normalized_event_type,
                occurred_at=timestamp,
                actor=normalized_actor,
                details=normalized_details,
                previous_hash=previous_hash,
            )

            event = ExecutionAuditEvent(
                sequence=sequence,
                execution_id=normalized_execution_id,
                event_type=normalized_event_type,
                occurred_at=timestamp.astimezone(UTC),
                actor=normalized_actor,
                details=normalized_details,
                previous_hash=previous_hash,
                event_hash=event_hash,
            )

            self._events.append(event)

            return event

    def events(self) -> tuple[ExecutionAuditEvent, ...]:
        """Return an immutable snapshot of all events."""
        with self._lock:
            return tuple(self._events)

    def events_for(
        self,
        execution_id: str,
    ) -> tuple[ExecutionAuditEvent, ...]:
        """Return an immutable snapshot for one execution."""
        normalized_execution_id = execution_id.strip()

        if not normalized_execution_id:
            raise ValueError("execution_id must not be empty")

        with self._lock:
            return tuple(
                event
                for event in self._events
                if event.execution_id == normalized_execution_id
            )

    def verify_chain(self) -> bool:
        """Verify sequence ordering and hash-chain integrity."""
        with self._lock:
            previous_hash: str | None = None

            for expected_sequence, event in enumerate(
                self._events,
                start=1,
            ):
                if event.sequence != expected_sequence:
                    return False

                if event.previous_hash != previous_hash:
                    return False

                expected_hash = ExecutionAuditEvent.calculate_hash(
                    sequence=event.sequence,
                    execution_id=event.execution_id,
                    event_type=event.event_type,
                    occurred_at=event.occurred_at,
                    actor=event.actor,
                    details=event.details,
                    previous_hash=event.previous_hash,
                )

                if event.event_hash != expected_hash:
                    return False

                previous_hash = event.event_hash

            return True

    def clear(self) -> None:
        """Clear all events.

        This operation is intentionally explicit and should not be used
        as a normal execution lifecycle operation.
        """
        with self._lock:
            self._events.clear()
