"""Tests for secure-execution to durable-persistence adaptation."""

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
    ExecutionResult,
    ExecutionStatus,
    ResourceLimits,
)
from lyrion.persistence.contracts import (
    PersistentExecutionRecord,
    PersistentExecutionState,
)
from lyrion.persistence.execution_adapter import (
    ExecutionPersistenceAdapter,
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
    """Minimal execution store test double."""

    def __init__(self) -> None:
        """Initialize captured state."""
        self.records: list[PersistentExecutionRecord] = []

    async def create(
        self,
        record: PersistentExecutionRecord,
    ) -> PersistentExecutionRecord:
        """Capture the durable record."""
        self.records.append(record)
        return record

    async def get(
        self,
        execution_id: str,
    ) -> PersistentExecutionRecord | None:
        """Return a captured execution when present."""
        for record in self.records:
            if record.execution_id == execution_id:
                return record

        return None

    async def claim(
        self,
        *,
        execution_id: str,
        worker_id: str,
        lease_id: str,
        claimed_at: datetime,
        expected_revision: int,
    ) -> PersistentExecutionRecord | None:
        """Implement the protocol for this adapter test double."""
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
        """Implement the protocol for this adapter test double."""
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

    async def find_recoverable(
        self,
        *,
        states: Sequence[PersistentExecutionState],
        now: datetime,
        limit: int,
    ) -> Sequence[PersistentExecutionRecord]:
        """Implement the protocol for this adapter test double."""
        del states
        del now
        del limit
        raise NotImplementedError


def make_request() -> ExecutionRequest:
    """Create a valid execution request."""
    return ExecutionRequest(
        execution_id="execution:adapter:001",
        request_id="request:adapter:001",
        task_id=TaskId("task:adapter:001"),
        capability_id="development.prepare",
        target_scope="lyrion/project/adapter",
        operation="READ",
        authorization_reference="authorization:adapter:001",
        policy_version="aegis-policy-v1",
        principal_id="lyrion-test",
        autonomy_level=AutonomyLevel.L1,
        risk_level=RiskLevel.LOW,
        resource_limits=ResourceLimits(),
        idempotency_key=IdempotencyKey("idem:adapter:001"),
        requested_at=BASE_TIME,
        expires_at=BASE_TIME + timedelta(minutes=5),
    )


def make_result(
    *,
    status: ExecutionStatus = ExecutionStatus.COMPLETED,
) -> ExecutionResult:
    """Create a valid execution result."""
    return ExecutionResult(
        execution_id="execution:adapter:001",
        request_id="request:adapter:001",
        status=status,
        started_at=BASE_TIME + timedelta(seconds=1),
        completed_at=(
            BASE_TIME + timedelta(seconds=2)
            if status not in {
                ExecutionStatus.DENIED,
            }
            else None
        ),
        exit_code=0 if status is ExecutionStatus.COMPLETED else None,
        output_ref=None,
        error_code=(
            "EXECUTION_FAILED"
            if status in {
                ExecutionStatus.FAILED,
                ExecutionStatus.TIMED_OUT,
                ExecutionStatus.CANCELLED,
                ExecutionStatus.TERMINATED,
                ExecutionStatus.DENIED,
            }
            else None
        ),
        error_message=(
            "Execution did not complete successfully."
            if status in {
                ExecutionStatus.FAILED,
                ExecutionStatus.TIMED_OUT,
                ExecutionStatus.CANCELLED,
                ExecutionStatus.TERMINATED,
                ExecutionStatus.DENIED,
            }
            else None
        ),
        checkpoint_ref="checkpoint:adapter:001",
    )


@pytest.mark.asyncio
async def test_record_result_persists_identity_and_outcome() -> None:
    """The adapter must preserve request identity and result evidence."""
    store = FakeExecutionStore()
    adapter = ExecutionPersistenceAdapter(store)

    request = make_request()
    result = make_result()

    record = await adapter.record_result(
        opportunity_id=OpportunityId("opportunity:adapter:001"),
        request=request,
        result=result,
    )

    assert record.execution_id == request.execution_id
    assert record.request_id == request.request_id
    assert record.task_id == request.task_id
    assert record.idempotency_key == request.idempotency_key
    assert record.opportunity_id == OpportunityId(
        "opportunity:adapter:001"
    )
    assert record.state is PersistentExecutionState.COMPLETED
    assert record.started_at == result.started_at
    assert record.completed_at == result.completed_at
    assert record.checkpoint_ref == result.checkpoint_ref
    assert store.records == [record]


@pytest.mark.parametrize(
    ("status", "expected_state"),
    (
        (
            ExecutionStatus.COMPLETED,
            PersistentExecutionState.COMPLETED,
        ),
        (
            ExecutionStatus.FAILED,
            PersistentExecutionState.FAILED,
        ),
        (
            ExecutionStatus.CANCELLED,
            PersistentExecutionState.CANCELLED,
        ),
        (
            ExecutionStatus.TERMINATED,
            PersistentExecutionState.ABANDONED,
        ),
        (
            ExecutionStatus.TIMED_OUT,
            PersistentExecutionState.FAILED,
        ),
        (
            ExecutionStatus.DENIED,
            PersistentExecutionState.FAILED,
        ),
        (
            ExecutionStatus.RUNNING,
            PersistentExecutionState.EXECUTING,
        ),
    ),
)
def test_status_mapping(
    status: ExecutionStatus,
    expected_state: PersistentExecutionState,
) -> None:
    """Known execution statuses must map deterministically."""
    assert (
        ExecutionPersistenceAdapter._map_status(status)
        is expected_state
    )


@pytest.mark.asyncio
async def test_mismatched_execution_identity_is_rejected() -> None:
    """Request/result identity divergence must fail closed."""
    store = FakeExecutionStore()
    adapter = ExecutionPersistenceAdapter(store)

    request = make_request()
    result = make_result().model_copy(
        update={
            "execution_id": "execution:other",
        }
    )

    with pytest.raises(
        ValueError,
        match="execution_id",
    ):
        await adapter.record_result(
            opportunity_id=OpportunityId(
                "opportunity:adapter:001"
            ),
            request=request,
            result=result,
        )


@pytest.mark.asyncio
async def test_mismatched_request_identity_is_rejected() -> None:
    """Request/result request IDs must remain aligned."""
    store = FakeExecutionStore()
    adapter = ExecutionPersistenceAdapter(store)

    request = make_request()
    result = make_result().model_copy(
        update={
            "request_id": "request:other",
        }
    )

    with pytest.raises(
        ValueError,
        match="request_id",
    ):
        await adapter.record_result(
            opportunity_id=OpportunityId(
                "opportunity:adapter:001"
            ),
            request=request,
            result=result,
        )
