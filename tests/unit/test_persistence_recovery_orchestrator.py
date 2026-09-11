"""Tests for durable recovery decision application."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest

from lyrion.core.types import IdempotencyKey, OpportunityId, TaskId
from lyrion.persistence.contracts import (
    PersistentExecutionRecord,
    PersistentExecutionState,
    RecoveryAction,
    RecoveryDecision,
    RuntimeLease,
)
from lyrion.persistence.recovery_orchestrator import (
    PersistentRecoveryOrchestrator,
)

BASE_TIME = datetime(
    2026,
    8,
    31,
    12,
    0,
    tzinfo=UTC,
)


class FakeExecutionStore:
    """Execution persistence test double."""

    def __init__(
        self,
        record: PersistentExecutionRecord,
    ) -> None:
        """Initialize the current durable record."""
        self.record = record
        self.requeue_calls = 0

    async def create(
        self,
        record: PersistentExecutionRecord,
    ) -> PersistentExecutionRecord:
        """Create a record."""
        self.record = record
        return record

    async def get(
        self,
        execution_id: str,
    ) -> PersistentExecutionRecord | None:
        """Return the requested record."""
        if self.record.execution_id != execution_id:
            return None

        return self.record

    async def claim(
        self,
        *,
        execution_id: str,
        worker_id: str,
        lease_id: str,
        claimed_at: datetime,
        expected_revision: int,
    ) -> PersistentExecutionRecord | None:
        """Unused execution-store operation."""
        del execution_id
        del worker_id
        del lease_id
        del claimed_at
        del expected_revision
        raise NotImplementedError

    async def transition(
        self,
        *,
        execution_id: str,
        worker_id: str,
        lease_id: str,
        expected_revision: int,
        target_state: PersistentExecutionState,
        occurred_at: datetime,
        checkpoint_ref: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> PersistentExecutionRecord:
        """Unused execution-store operation."""
        del execution_id
        del worker_id
        del lease_id
        del expected_revision
        del target_state
        del occurred_at
        del checkpoint_ref
        del error_code
        del error_message
        raise NotImplementedError

    async def requeue(
        self,
        *,
        execution_id: str,
        expected_revision: int,
        occurred_at: datetime,
    ) -> PersistentExecutionRecord:
        """Requeue the claimed execution."""
        del execution_id
        del occurred_at

        self.requeue_calls += 1

        self.record = self.record.model_copy(
            update={
                "state": PersistentExecutionState.QUEUED,
                "worker_id": None,
                "lease_id": None,
                "claimed_at": None,
                "revision": expected_revision + 1,
            }
        )

        return self.record

    async def find_recoverable(
        self,
        *,
        states: Sequence[PersistentExecutionState],
        now: datetime,
        limit: int,
    ) -> Sequence[PersistentExecutionRecord]:
        """Unused execution-store operation."""
        del states
        del now
        del limit
        raise NotImplementedError


class FakeLeaseStore:
    """Lease persistence test double."""

    def __init__(
        self,
        lease: RuntimeLease | None,
    ) -> None:
        """Initialize the lease state."""
        self.lease = lease
        self.release_calls = 0

    async def acquire(
        self,
        *,
        resource_id: str,
        worker_id: str,
        lease_id: str,
        acquired_at: datetime,
        expires_at: datetime,
    ) -> RuntimeLease | None:
        """Unused lease acquisition."""
        del resource_id
        del worker_id
        del lease_id
        del acquired_at
        del expires_at
        raise NotImplementedError

    async def get(
        self,
        resource_id: str,
    ) -> RuntimeLease | None:
        """Return the lease for the execution."""
        if self.lease is None:
            return None

        if self.lease.resource_id != resource_id:
            return None

        return self.lease

    async def renew(
        self,
        *,
        lease_id: str,
        worker_id: str,
        expected_revision: int,
        expires_at: datetime,
    ) -> RuntimeLease:
        """Unused lease renewal."""
        del lease_id
        del worker_id
        del expected_revision
        del expires_at
        raise NotImplementedError

    async def release(
        self,
        *,
        lease_id: str,
        worker_id: str,
    ) -> None:
        """Release the current lease."""
        assert self.lease is not None
        assert self.lease.lease_id == lease_id
        assert self.lease.worker_id == worker_id

        self.release_calls += 1
        self.lease = None

    async def find_expired(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> Sequence[RuntimeLease]:
        """Unused expired-lease lookup."""
        del now
        del limit
        raise NotImplementedError


class FakeRecoveryStore:
    """Recovery decision persistence test double."""

    def __init__(self) -> None:
        """Initialize decision history."""
        self.decisions: list[RecoveryDecision] = []

    async def record(
        self,
        decision: RecoveryDecision,
    ) -> RecoveryDecision:
        """Persist a decision."""
        self.decisions.append(decision)
        return decision

    async def find_for_execution(
        self,
        execution_id: str,
    ) -> Sequence[RecoveryDecision]:
        """Return recorded decisions for an execution."""
        return tuple(
            decision
            for decision in self.decisions
            if decision.execution_id == execution_id
        )


def make_record(
    *,
    state: PersistentExecutionState,
    revision: int = 2,
) -> PersistentExecutionRecord:
    """Create a recovery test record."""
    claimed_at = (
        BASE_TIME + timedelta(seconds=1)
        if state is not PersistentExecutionState.QUEUED
        else None
    )
    started_at = (
        BASE_TIME + timedelta(seconds=2)
        if state is PersistentExecutionState.EXECUTING
        else None
    )
    completed_at = (
        BASE_TIME + timedelta(seconds=3)
        if state
        in {
            PersistentExecutionState.COMPLETED,
            PersistentExecutionState.FAILED,
            PersistentExecutionState.CANCELLED,
            PersistentExecutionState.ABANDONED,
        }
        else None
    )

    return PersistentExecutionRecord(
        execution_id="execution:recovery:orchestrator:001",
        request_id="request:recovery:orchestrator:001",
        opportunity_id=OpportunityId(
            "opportunity:recovery:orchestrator:001"
        ),
        task_id=TaskId(
            "task:recovery:orchestrator:001"
        ),
        idempotency_key=IdempotencyKey(
            "idem:recovery:orchestrator:001"
        ),
        state=state,
        created_at=BASE_TIME,
        claimed_at=claimed_at,
        started_at=started_at,
        completed_at=completed_at,
        worker_id=(
            "worker:001"
            if claimed_at is not None
            else None
        ),
        lease_id=(
            "lease:001"
            if claimed_at is not None
            else None
        ),
        revision=revision,
    )


def make_lease(
    *,
    expires_at: datetime,
) -> RuntimeLease:
    """Create a recovery lease."""
    return RuntimeLease(
        lease_id="lease:001",
        resource_id="execution:recovery:orchestrator:001",
        worker_id="worker:001",
        acquired_at=BASE_TIME,
        expires_at=expires_at,
        revision=1,
    )


@pytest.mark.asyncio
async def test_claimed_expired_execution_is_requeued() -> None:
    """Expired CLAIMED work must return to the queue."""
    execution_store = FakeExecutionStore(
        make_record(
            state=PersistentExecutionState.CLAIMED,
        )
    )
    lease_store = FakeLeaseStore(
        make_lease(
            expires_at=BASE_TIME + timedelta(seconds=30),
        )
    )
    recovery_store = FakeRecoveryStore()

    orchestrator = PersistentRecoveryOrchestrator(
        execution_store,
        lease_store,
        recovery_store,
    )

    action = await orchestrator.recover_one(
        execution_id=execution_store.record.execution_id,
        now=BASE_TIME + timedelta(seconds=30),
    )

    assert action is RecoveryAction.REQUEUE
    assert execution_store.requeue_calls == 1
    assert lease_store.release_calls == 1
    assert execution_store.record.state is (
        PersistentExecutionState.QUEUED
    )
    assert execution_store.record.revision == 3
    assert lease_store.lease is None
    assert recovery_store.decisions[-1].action is (
        RecoveryAction.REQUEUE
    )


@pytest.mark.asyncio
async def test_claimed_without_lease_is_requeued() -> None:
    """CLAIMED work without a lease must still be recoverable."""
    execution_store = FakeExecutionStore(
        make_record(
            state=PersistentExecutionState.CLAIMED,
        )
    )
    lease_store = FakeLeaseStore(None)
    recovery_store = FakeRecoveryStore()

    orchestrator = PersistentRecoveryOrchestrator(
        execution_store,
        lease_store,
        recovery_store,
    )

    action = await orchestrator.recover_one(
        execution_id=execution_store.record.execution_id,
        now=BASE_TIME + timedelta(minutes=1),
    )

    assert action is RecoveryAction.REQUEUE
    assert execution_store.requeue_calls == 1
    assert lease_store.release_calls == 0
    assert execution_store.record.state is (
        PersistentExecutionState.QUEUED
    )


@pytest.mark.asyncio
async def test_active_lease_produces_noop() -> None:
    """Active ownership must never be requeued."""
    execution_store = FakeExecutionStore(
        make_record(
            state=PersistentExecutionState.CLAIMED,
        )
    )
    lease_store = FakeLeaseStore(
        make_lease(
            expires_at=BASE_TIME + timedelta(minutes=5),
        )
    )
    recovery_store = FakeRecoveryStore()

    orchestrator = PersistentRecoveryOrchestrator(
        execution_store,
        lease_store,
        recovery_store,
    )

    action = await orchestrator.recover_one(
        execution_id=execution_store.record.execution_id,
        now=BASE_TIME + timedelta(minutes=1),
    )

    assert action is RecoveryAction.NOOP
    assert execution_store.requeue_calls == 0
    assert lease_store.release_calls == 0
    assert execution_store.record.state is (
        PersistentExecutionState.CLAIMED
    )
    assert recovery_store.decisions[-1].action is (
        RecoveryAction.NOOP
    )


@pytest.mark.asyncio
async def test_executing_expired_execution_is_reconciled() -> None:
    """Lost executing work must never be automatically retried."""
    execution_store = FakeExecutionStore(
        make_record(
            state=PersistentExecutionState.EXECUTING,
            revision=3,
        )
    )
    lease_store = FakeLeaseStore(
        make_lease(
            expires_at=BASE_TIME + timedelta(seconds=30),
        )
    )
    recovery_store = FakeRecoveryStore()

    orchestrator = PersistentRecoveryOrchestrator(
        execution_store,
        lease_store,
        recovery_store,
    )

    action = await orchestrator.recover_one(
        execution_id=execution_store.record.execution_id,
        now=BASE_TIME + timedelta(seconds=30),
    )

    assert action is RecoveryAction.RECONCILE
    assert execution_store.requeue_calls == 0
    assert lease_store.release_calls == 0
    assert execution_store.record.state is (
        PersistentExecutionState.EXECUTING
    )
    assert recovery_store.decisions[-1].action is (
        RecoveryAction.RECONCILE
    )


@pytest.mark.asyncio
async def test_unknown_execution_is_reconciled() -> None:
    """UNKNOWN execution state must remain unresolved."""
    execution_store = FakeExecutionStore(
        make_record(
            state=PersistentExecutionState.UNKNOWN,
            revision=7,
        )
    )
    lease_store = FakeLeaseStore(None)
    recovery_store = FakeRecoveryStore()

    orchestrator = PersistentRecoveryOrchestrator(
        execution_store,
        lease_store,
        recovery_store,
    )

    action = await orchestrator.recover_one(
        execution_id=execution_store.record.execution_id,
        now=BASE_TIME + timedelta(minutes=1),
    )

    assert action is RecoveryAction.RECONCILE
    assert execution_store.requeue_calls == 0
    assert lease_store.release_calls == 0


@pytest.mark.asyncio
async def test_abandoned_execution_is_quarantined() -> None:
    """ABANDONED execution must remain quarantined."""
    execution_store = FakeExecutionStore(
        make_record(
            state=PersistentExecutionState.ABANDONED,
        )
    )
    lease_store = FakeLeaseStore(None)
    recovery_store = FakeRecoveryStore()

    orchestrator = PersistentRecoveryOrchestrator(
        execution_store,
        lease_store,
        recovery_store,
    )

    action = await orchestrator.recover_one(
        execution_id=execution_store.record.execution_id,
        now=BASE_TIME + timedelta(minutes=1),
    )

    assert action is RecoveryAction.QUARANTINE
    assert execution_store.requeue_calls == 0
    assert lease_store.release_calls == 0
