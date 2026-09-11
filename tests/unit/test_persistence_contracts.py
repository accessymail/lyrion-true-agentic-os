"""Adversarial tests for durable persistence contracts."""

from datetime import UTC, datetime, timedelta

import pytest

from lyrion.core.types import IdempotencyKey, OpportunityId, TaskId
from lyrion.persistence.contracts import (
    PersistentExecutionRecord,
    PersistentExecutionState,
    PersistentScheduler,
    PersistentSchedulerState,
    RecoveryAction,
    RecoveryDecision,
    RuntimeInstance,
    RuntimeLease,
    RuntimeLifecycleState,
)

BASE_TIME = datetime(
    2026,
    8,
    31,
    12,
    0,
    tzinfo=UTC,
)


def make_execution(
    *,
    state: PersistentExecutionState = PersistentExecutionState.QUEUED,
    claimed_at: datetime | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    worker_id: str | None = None,
    lease_id: str | None = None,
) -> PersistentExecutionRecord:
    """Create a valid baseline persistent execution."""
    return PersistentExecutionRecord(
        execution_id="execution:001",
        request_id="request:001",
        opportunity_id=OpportunityId("opportunity:001"),
        task_id=TaskId("task:001"),
        idempotency_key=IdempotencyKey("idem:001"),
        state=state,
        created_at=BASE_TIME,
        claimed_at=claimed_at,
        started_at=started_at,
        completed_at=completed_at,
        worker_id=worker_id,
        lease_id=lease_id,
    )


def make_scheduler(
    *,
    state: PersistentSchedulerState = (
        PersistentSchedulerState.READY
    ),
    next_run_at: datetime | None = None,
    revision: int = 1,
) -> PersistentScheduler:
    """Create a valid baseline persistent scheduler."""
    return PersistentScheduler(
        scheduler_id="scheduler:001",
        state=state,
        next_run_at=next_run_at,
        revision=revision,
    )


def test_scheduler_initial_state_is_representable() -> None:
    """A new scheduler may have no persisted next-run deadline."""
    scheduler = make_scheduler()

    assert scheduler.scheduler_id == "scheduler:001"
    assert scheduler.state is PersistentSchedulerState.READY
    assert scheduler.next_run_at is None
    assert scheduler.revision == 1


def test_scheduler_paused_state_is_representable() -> None:
    """PAUSED must be an explicit durable scheduler state."""
    scheduler = make_scheduler(
        state=PersistentSchedulerState.PAUSED,
    )

    assert scheduler.state is PersistentSchedulerState.PAUSED


def test_scheduler_next_run_normalizes_utc() -> None:
    """Persisted next-run timestamps should normalize to UTC."""
    scheduler = make_scheduler(
        next_run_at=BASE_TIME + timedelta(minutes=1),
    )

    assert scheduler.next_run_at is not None
    assert scheduler.next_run_at.tzinfo is UTC


def test_scheduler_naive_next_run_is_rejected() -> None:
    """Scheduler deadlines must be timezone-aware."""
    with pytest.raises(
        ValueError,
        match="next_run_at must be timezone-aware",
    ):
        make_scheduler(
            next_run_at=datetime(
                2026,
                8,
                31,
                12,
                1,
            ),
        )


def test_scheduler_revision_must_be_positive() -> None:
    """Scheduler optimistic revisions must start at one or greater."""
    with pytest.raises(ValueError):
        make_scheduler(revision=0)


def test_scheduler_identifier_cannot_be_blank() -> None:
    """Scheduler identity must be non-empty."""
    with pytest.raises(ValueError):
        PersistentScheduler(
            scheduler_id="",
            state=PersistentSchedulerState.READY,
        )


def test_scheduler_is_immutable() -> None:
    """Persistent scheduler state must not mutate in place."""
    scheduler = make_scheduler()

    with pytest.raises(ValueError):
        scheduler.state = PersistentSchedulerState.PAUSED


def test_runtime_instance_normalizes_utc() -> None:
    """Runtime lifecycle timestamps should normalize to UTC."""
    instance = RuntimeInstance(
        instance_id="runtime:001",
        state=RuntimeLifecycleState.RUNNING,
        started_at=BASE_TIME,
        heartbeat_at=BASE_TIME + timedelta(seconds=5),
    )

    assert instance.started_at.tzinfo is UTC
    assert instance.heartbeat_at.tzinfo is UTC


def test_runtime_heartbeat_before_start_is_rejected() -> None:
    """A heartbeat cannot precede runtime startup."""
    with pytest.raises(
        ValueError,
        match="heartbeat_at cannot be earlier",
    ):
        RuntimeInstance(
            instance_id="runtime:001",
            state=RuntimeLifecycleState.RUNNING,
            started_at=BASE_TIME,
            heartbeat_at=BASE_TIME - timedelta(seconds=1),
        )


def test_runtime_naive_timestamp_is_rejected() -> None:
    """Runtime timestamps must be timezone-aware."""
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        RuntimeInstance(
            instance_id="runtime:001",
            state=RuntimeLifecycleState.STARTING,
            started_at=datetime(
                2026,
                8,
                31,
                12,
                0,
            ),
            heartbeat_at=BASE_TIME,
        )


def test_lease_requires_positive_duration() -> None:
    """Lease expiry must follow acquisition."""
    with pytest.raises(
        ValueError,
        match="later than acquired_at",
    ):
        RuntimeLease(
            lease_id="lease:001",
            resource_id="execution:001",
            worker_id="worker:001",
            acquired_at=BASE_TIME,
            expires_at=BASE_TIME,
        )


def test_lease_expiry_is_deterministic() -> None:
    """Lease expiration should use the supplied clock."""
    lease = RuntimeLease(
        lease_id="lease:001",
        resource_id="execution:001",
        worker_id="worker:001",
        acquired_at=BASE_TIME,
        expires_at=BASE_TIME + timedelta(seconds=30),
    )

    assert lease.is_expired(
        BASE_TIME + timedelta(seconds=29),
    ) is False

    assert lease.is_expired(
        BASE_TIME + timedelta(seconds=30),
    ) is True


def test_lease_naive_clock_is_rejected() -> None:
    """Lease expiration checks require timezone-aware clocks."""
    lease = RuntimeLease(
        lease_id="lease:001",
        resource_id="execution:001",
        worker_id="worker:001",
        acquired_at=BASE_TIME,
        expires_at=BASE_TIME + timedelta(seconds=30),
    )

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        lease.is_expired(
            datetime(
                2026,
                8,
                31,
                12,
                0,
            ),
        )


def test_queued_execution_requires_only_creation_time() -> None:
    """Initial durable execution state should be minimal."""
    record = make_execution()

    assert record.state is PersistentExecutionState.QUEUED
    assert record.claimed_at is None
    assert record.started_at is None
    assert record.completed_at is None


def test_executing_execution_requires_start_time() -> None:
    """EXECUTING state must have explicit start evidence."""
    with pytest.raises(
        ValueError,
        match="requires started_at",
    ):
        make_execution(
            state=PersistentExecutionState.EXECUTING,
        )


def test_terminal_execution_requires_completion_time() -> None:
    """Terminal states require an explicit completion timestamp."""
    with pytest.raises(
        ValueError,
        match="requires completed_at",
    ):
        make_execution(
            state=PersistentExecutionState.COMPLETED,
        )


def test_execution_timestamps_must_be_ordered() -> None:
    """Lifecycle timestamps cannot move backward."""
    with pytest.raises(
        ValueError,
        match="timestamps must be ordered",
    ):
        make_execution(
            claimed_at=BASE_TIME + timedelta(seconds=10),
            started_at=BASE_TIME + timedelta(seconds=5),
        )


def test_completed_execution_preserves_identity() -> None:
    """Terminal records must retain durable execution identity."""
    record = make_execution(
        state=PersistentExecutionState.COMPLETED,
        claimed_at=BASE_TIME + timedelta(seconds=1),
        started_at=BASE_TIME + timedelta(seconds=2),
        completed_at=BASE_TIME + timedelta(seconds=3),
        worker_id="worker:001",
        lease_id="lease:001",
    )

    assert record.execution_id == "execution:001"
    assert record.request_id == "request:001"
    assert record.opportunity_id == OpportunityId(
        "opportunity:001",
    )
    assert record.task_id == TaskId("task:001")
    assert record.idempotency_key == IdempotencyKey(
        "idem:001",
    )


def test_unknown_state_is_allowed_for_crash_recovery() -> None:
    """UNKNOWN must represent unresolved execution outcomes."""
    record = make_execution(
        state=PersistentExecutionState.UNKNOWN,
        completed_at=BASE_TIME + timedelta(seconds=3),
    )

    assert record.state is PersistentExecutionState.UNKNOWN


def test_recovery_decision_requires_explicit_reason() -> None:
    """Recovery decisions must explain their chosen action."""
    with pytest.raises(ValueError):
        RecoveryDecision(
            execution_id="execution:001",
            action=RecoveryAction.QUARANTINE,
            reason="",
            evaluated_at=BASE_TIME,
        )


def test_recovery_decision_normalizes_timestamp() -> None:
    """Recovery timestamps should normalize to UTC."""
    decision = RecoveryDecision(
        execution_id="execution:001",
        action=RecoveryAction.RECONCILE,
        reason="Execution outcome requires reconciliation.",
        evaluated_at=BASE_TIME,
    )

    assert decision.evaluated_at.tzinfo is UTC


def test_models_are_immutable() -> None:
    """Durable contracts must not be mutable in place."""
    instance = RuntimeInstance(
        instance_id="runtime:001",
        state=RuntimeLifecycleState.RUNNING,
        started_at=BASE_TIME,
        heartbeat_at=BASE_TIME,
    )

    with pytest.raises(
        ValueError,
    ):
        instance.state = RuntimeLifecycleState.PAUSED
