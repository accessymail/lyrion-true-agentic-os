"""Adversarial tests for deterministic persistence recovery."""

from datetime import UTC, datetime, timedelta

import pytest

from lyrion.core.types import IdempotencyKey, OpportunityId, TaskId
from lyrion.persistence.contracts import (
    PersistentExecutionRecord,
    PersistentExecutionState,
    RecoveryAction,
    RuntimeLease,
)
from lyrion.persistence.recovery import RecoveryManager

BASE_TIME = datetime(
    2026,
    8,
    31,
    12,
    0,
    tzinfo=UTC,
)


def make_record(
    *,
    state: PersistentExecutionState,
    claimed_at: datetime | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    revision: int = 1,
) -> PersistentExecutionRecord:
    """Create a valid execution record for recovery tests."""
    return PersistentExecutionRecord(
        execution_id="execution:recovery:001",
        request_id="request:recovery:001",
        opportunity_id=OpportunityId("opportunity:recovery:001"),
        task_id=TaskId("task:recovery:001"),
        idempotency_key=IdempotencyKey("idem:recovery:001"),
        state=state,
        created_at=BASE_TIME,
        claimed_at=claimed_at,
        started_at=started_at,
        completed_at=completed_at,
        revision=revision,
    )


def make_lease(
    *,
    worker_id: str = "worker:001",
    lease_id: str = "lease:001",
    expires_at: datetime = BASE_TIME + timedelta(minutes=5),
) -> RuntimeLease:
    """Create a valid recovery lease."""
    return RuntimeLease(
        lease_id=lease_id,
        resource_id="execution:recovery:001",
        worker_id=worker_id,
        acquired_at=BASE_TIME,
        expires_at=expires_at,
    )


def test_queued_execution_requires_no_recovery() -> None:
    """Queued work must remain queued."""
    decision = RecoveryManager().decide(
        record=make_record(
            state=PersistentExecutionState.QUEUED,
        ),
        lease=None,
        now=BASE_TIME,
    )

    assert decision.action is RecoveryAction.NOOP


def test_claimed_execution_with_active_lease_requires_no_recovery() -> None:
    """An owned claim must not be disturbed."""
    decision = RecoveryManager().decide(
        record=make_record(
            state=PersistentExecutionState.CLAIMED,
            claimed_at=BASE_TIME + timedelta(seconds=1),
        ),
        lease=make_lease(),
        now=BASE_TIME + timedelta(minutes=1),
    )

    assert decision.action is RecoveryAction.NOOP


def test_claimed_execution_with_expired_lease_is_requeued() -> None:
    """A lost claim before execution can safely return to the queue."""
    decision = RecoveryManager().decide(
        record=make_record(
            state=PersistentExecutionState.CLAIMED,
            claimed_at=BASE_TIME + timedelta(seconds=1),
        ),
        lease=make_lease(
            expires_at=BASE_TIME + timedelta(seconds=30),
        ),
        now=BASE_TIME + timedelta(seconds=30),
    )

    assert decision.action is RecoveryAction.REQUEUE


def test_claimed_execution_without_lease_is_requeued() -> None:
    """A claim without durable ownership can be recovered."""
    decision = RecoveryManager().decide(
        record=make_record(
            state=PersistentExecutionState.CLAIMED,
            claimed_at=BASE_TIME + timedelta(seconds=1),
        ),
        lease=None,
        now=BASE_TIME + timedelta(minutes=1),
    )

    assert decision.action is RecoveryAction.REQUEUE


def test_executing_with_active_lease_requires_no_recovery() -> None:
    """Active execution ownership must remain untouched."""
    decision = RecoveryManager().decide(
        record=make_record(
            state=PersistentExecutionState.EXECUTING,
            claimed_at=BASE_TIME + timedelta(seconds=1),
            started_at=BASE_TIME + timedelta(seconds=2),
        ),
        lease=make_lease(),
        now=BASE_TIME + timedelta(minutes=1),
    )

    assert decision.action is RecoveryAction.NOOP


def test_executing_with_expired_lease_requires_reconciliation() -> None:
    """Lost execution ownership must never become an automatic retry."""
    decision = RecoveryManager().decide(
        record=make_record(
            state=PersistentExecutionState.EXECUTING,
            claimed_at=BASE_TIME + timedelta(seconds=1),
            started_at=BASE_TIME + timedelta(seconds=2),
        ),
        lease=make_lease(
            expires_at=BASE_TIME + timedelta(seconds=30),
        ),
        now=BASE_TIME + timedelta(seconds=30),
    )

    assert decision.action is RecoveryAction.RECONCILE


def test_unknown_execution_requires_reconciliation() -> None:
    """UNKNOWN must remain unresolved until evidence is reconciled."""
    decision = RecoveryManager().decide(
        record=make_record(
            state=PersistentExecutionState.UNKNOWN,
            completed_at=BASE_TIME + timedelta(seconds=3),
        ),
        lease=None,
        now=BASE_TIME + timedelta(minutes=1),
    )

    assert decision.action is RecoveryAction.RECONCILE


def test_abandoned_execution_is_quarantined() -> None:
    """ABANDONED work must not silently re-enter execution."""
    decision = RecoveryManager().decide(
        record=make_record(
            state=PersistentExecutionState.ABANDONED,
            completed_at=BASE_TIME + timedelta(seconds=3),
        ),
        lease=None,
        now=BASE_TIME + timedelta(minutes=1),
    )

    assert decision.action is RecoveryAction.QUARANTINE


@pytest.mark.parametrize(
    "state",
    [
        PersistentExecutionState.COMPLETED,
        PersistentExecutionState.FAILED,
        PersistentExecutionState.CANCELLED,
    ],
)
def test_terminal_execution_requires_no_recovery(
    state: PersistentExecutionState,
) -> None:
    """Terminal executions require no recovery action."""
    decision = RecoveryManager().decide(
        record=make_record(
            state=state,
            completed_at=BASE_TIME + timedelta(seconds=3),
        ),
        lease=None,
        now=BASE_TIME + timedelta(minutes=1),
    )

    assert decision.action is RecoveryAction.NOOP


def test_recovery_is_deterministic() -> None:
    """Identical state and time must yield identical decisions."""
    record = make_record(
        state=PersistentExecutionState.EXECUTING,
        claimed_at=BASE_TIME + timedelta(seconds=1),
        started_at=BASE_TIME + timedelta(seconds=2),
        revision=7,
    )
    lease = make_lease(
        expires_at=BASE_TIME + timedelta(seconds=30),
    )

    manager = RecoveryManager()

    first = manager.decide(
        record=record,
        lease=lease,
        now=BASE_TIME + timedelta(seconds=30),
    )

    second = manager.decide(
        record=record,
        lease=lease,
        now=BASE_TIME + timedelta(seconds=30),
    )

    assert first == second
    assert first.execution_id == record.execution_id
    assert first.source_revision == 7


def test_naive_recovery_clock_is_rejected() -> None:
    """Recovery must use an explicit timezone-aware clock."""
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        RecoveryManager().decide(
            record=make_record(
                state=PersistentExecutionState.QUEUED,
            ),
            lease=None,
            now=datetime(
                2026,
                8,
                31,
                12,
                0,
            ),
        )
