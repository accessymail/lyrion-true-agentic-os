"""Tests for durable execution lifecycle orchestration."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest

from lyrion.core.types import (
    AutonomyLevel,
    IdempotencyKey,
    OpportunityId,
    RiskLevel,
    TaskId,
)
from lyrion.execution.contracts import (
    ExecutionRequest,
    ResourceLimits,
)
from lyrion.persistence.contracts import (
    PersistentExecutionRecord,
    PersistentExecutionState,
    RuntimeLease,
)
from lyrion.persistence.execution_lifecycle import (
    PersistentExecutionLifecycle,
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
    """Execution store test double."""

    def __init__(self) -> None:
        """Initialize state."""
        self.records: dict[str, PersistentExecutionRecord] = {}

    async def create(
        self,
        record: PersistentExecutionRecord,
    ) -> PersistentExecutionRecord:
        """Create one record."""
        self.records[record.execution_id] = record
        return record

    async def get(
        self,
        execution_id: str,
    ) -> PersistentExecutionRecord | None:
        """Return one record."""
        return self.records.get(execution_id)

    async def claim(
        self,
        *,
        execution_id: str,
        worker_id: str,
        lease_id: str,
        claimed_at: datetime,
        expected_revision: int,
    ) -> PersistentExecutionRecord | None:
        """Claim a queued execution."""
        record = self.records.get(execution_id)

        if record is None:
            return None

        if record.state is not PersistentExecutionState.QUEUED:
            return None

        if record.revision != expected_revision:
            return None

        updated = record.model_copy(
            update={
                "state": PersistentExecutionState.CLAIMED,
                "claimed_at": claimed_at,
                "worker_id": worker_id,
                "lease_id": lease_id,
                "revision": expected_revision + 1,
            }
        )

        self.records[execution_id] = updated
        return updated

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
        """Advance one owned execution."""
        record = self.records[execution_id]

        if record.worker_id != worker_id:
            raise RuntimeError("worker mismatch")

        if record.lease_id != lease_id:
            raise RuntimeError("lease mismatch")

        if record.revision != expected_revision:
            raise RuntimeError("revision mismatch")

        update = {
            "state": target_state,
            "revision": expected_revision + 1,
        }

        if target_state is PersistentExecutionState.EXECUTING:
            update["started_at"] = occurred_at

        if target_state in {
            PersistentExecutionState.COMPLETED,
            PersistentExecutionState.FAILED,
            PersistentExecutionState.CANCELLED,
            PersistentExecutionState.ABANDONED,
        }:
            update["completed_at"] = occurred_at

        if checkpoint_ref is not None:
            update["checkpoint_ref"] = checkpoint_ref

        if error_code is not None:
            update["error_code"] = error_code

        if error_message is not None:
            update["error_message"] = error_message

        updated = record.model_copy(update=update)
        self.records[execution_id] = updated
        return updated

    async def find_recoverable(
        self,
        *,
        states: Sequence[PersistentExecutionState],
        now: datetime,
        limit: int,
    ) -> Sequence[PersistentExecutionRecord]:
        """Return recoverable executions."""
        del now

        return [
            record
            for record in self.records.values()
            if record.state in states
        ][:limit]


class FakeLeaseStore:
    """Lease store test double."""

    def __init__(self) -> None:
        """Initialize state."""
        self.leases: dict[str, RuntimeLease] = {}

    async def acquire(
        self,
        *,
        resource_id: str,
        worker_id: str,
        lease_id: str,
        acquired_at: datetime,
        expires_at: datetime,
    ) -> RuntimeLease | None:
        """Acquire an execution lease."""
        current = self.leases.get(resource_id)

        if current is not None and not current.is_expired(
            acquired_at
        ):
            return None

        lease = RuntimeLease(
            lease_id=lease_id,
            resource_id=resource_id,
            worker_id=worker_id,
            acquired_at=acquired_at,
            expires_at=expires_at,
            revision=1 if current is None else current.revision + 1,
        )

        self.leases[resource_id] = lease
        return lease

    async def get(
        self,
        resource_id: str,
    ) -> RuntimeLease | None:
        """Return a resource lease."""
        return self.leases.get(resource_id)

    async def renew(
        self,
        *,
        lease_id: str,
        worker_id: str,
        expected_revision: int,
        expires_at: datetime,
    ) -> RuntimeLease:
        """Renew an owned lease."""
        raise NotImplementedError

    async def release(
        self,
        *,
        lease_id: str,
        worker_id: str,
    ) -> None:
        """Release an owned lease."""
        for resource_id, lease in tuple(self.leases.items()):
            if (
                lease.lease_id == lease_id
                and lease.worker_id == worker_id
            ):
                del self.leases[resource_id]
                return

    async def find_expired(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> Sequence[RuntimeLease]:
        """Return expired leases up to the requested bound."""
        return [
            lease
            for lease in self.leases.values()
            if lease.is_expired(now)
        ][:limit]


def make_request() -> ExecutionRequest:
    """Create a valid execution request."""
    return ExecutionRequest(
        execution_id="execution:lifecycle:001",
        request_id="request:lifecycle:001",
        task_id=TaskId("task:lifecycle:001"),
        capability_id="development.prepare",
        target_scope="lyrion/project/lifecycle",
        operation="READ",
        authorization_reference="authorization:lifecycle:001",
        policy_version="aegis-policy-v1",
        principal_id="lyrion-test",
        autonomy_level=AutonomyLevel.L1,
        risk_level=RiskLevel.LOW,
        resource_limits=ResourceLimits(),
        idempotency_key=IdempotencyKey(
            "idem:lifecycle:001"
        ),
        requested_at=BASE_TIME,
        expires_at=BASE_TIME + timedelta(minutes=5),
    )


@pytest.mark.asyncio
async def test_lifecycle_claim_begin_and_finish() -> None:
    """Durable execution should follow the full owned lifecycle."""
    execution_store = FakeExecutionStore()
    lease_store = FakeLeaseStore()

    lifecycle = PersistentExecutionLifecycle(
        execution_store,
        lease_store,
    )

    request = make_request()

    queued = await lifecycle.create_queued(
        request=request,
        opportunity_id=OpportunityId(
            "opportunity:lifecycle:001"
        ),
    )

    assert queued.state is PersistentExecutionState.QUEUED

    claimed = await lifecycle.claim(
        execution_id=request.execution_id,
        worker_id="worker:001",
        lease_id="lease:lifecycle:001",
        claimed_at=BASE_TIME + timedelta(seconds=1),
        expires_at=BASE_TIME + timedelta(minutes=5),
    )

    assert claimed.state is PersistentExecutionState.CLAIMED
    assert claimed.revision == 2

    executing = await lifecycle.begin(
        execution=claimed,
        worker_id="worker:001",
        lease_id="lease:lifecycle:001",
        started_at=BASE_TIME + timedelta(seconds=2),
    )

    assert executing.state is PersistentExecutionState.EXECUTING
    assert executing.started_at == (
        BASE_TIME + timedelta(seconds=2)
    )
    assert executing.revision == 3

    completed = await lifecycle.finish(
        execution=executing,
        worker_id="worker:001",
        lease_id="lease:lifecycle:001",
        target_state=PersistentExecutionState.COMPLETED,
        occurred_at=BASE_TIME + timedelta(seconds=3),
    )

    assert completed.state is PersistentExecutionState.COMPLETED
    assert completed.completed_at == (
        BASE_TIME + timedelta(seconds=3)
    )
    assert completed.revision == 4
    assert await lifecycle.get_lease(
        request.execution_id
    ) is None


@pytest.mark.asyncio
async def test_claim_rejects_active_lease() -> None:
    """An active owner must prevent a second execution claimant."""
    execution_store = FakeExecutionStore()
    lease_store = FakeLeaseStore()

    lifecycle = PersistentExecutionLifecycle(
        execution_store,
        lease_store,
    )

    request = make_request()

    await lifecycle.create_queued(
        request=request,
        opportunity_id=OpportunityId(
            "opportunity:lifecycle:001"
        ),
    )

    await lifecycle.claim(
        execution_id=request.execution_id,
        worker_id="worker:001",
        lease_id="lease:lifecycle:001",
        claimed_at=BASE_TIME,
        expires_at=BASE_TIME + timedelta(minutes=5),
    )

    with pytest.raises(
        RuntimeError,
        match="ownership could not be acquired",
    ):
        await lifecycle.claim(
            execution_id=request.execution_id,
            worker_id="worker:002",
            lease_id="lease:lifecycle:002",
            claimed_at=BASE_TIME + timedelta(seconds=1),
            expires_at=BASE_TIME + timedelta(minutes=5),
            expected_revision=2,
        )
