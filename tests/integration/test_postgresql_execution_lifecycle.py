"""PostgreSQL integration tests for durable execution lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

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
    PersistentExecutionState,
)
from lyrion.persistence.execution_lifecycle import (
    PersistentExecutionLifecycle,
)
from lyrion.persistence.sqlalchemy.execution_store import (
    SQLAlchemyExecutionStore,
)
from lyrion.persistence.sqlalchemy.lease_store import (
    SQLAlchemyLeaseStore,
)

pytestmark = pytest.mark.integration


BASE_TIME = datetime(
    2026,
    8,
    31,
    12,
    0,
    tzinfo=UTC,
)


def make_request() -> ExecutionRequest:
    """Create a valid execution request."""
    return ExecutionRequest(
        execution_id="execution:postgres:lifecycle:001",
        request_id="request:postgres:lifecycle:001",
        task_id=TaskId("task:postgres:lifecycle:001"),
        capability_id="development.prepare",
        target_scope="lyrion/project/postgres-lifecycle",
        operation="READ",
        authorization_reference=(
            "authorization:postgres:lifecycle:001"
        ),
        policy_version="aegis-policy-v1",
        principal_id="lyrion-test",
        autonomy_level=AutonomyLevel.L1,
        risk_level=RiskLevel.LOW,
        resource_limits=ResourceLimits(),
        idempotency_key=IdempotencyKey(
            "idem:postgres:lifecycle:001"
        ),
        requested_at=BASE_TIME,
        expires_at=BASE_TIME + timedelta(minutes=5),
    )


def make_lifecycle(
    database_engine: AsyncEngine,
) -> PersistentExecutionLifecycle:
    """Create a PostgreSQL-backed execution lifecycle."""
    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    return PersistentExecutionLifecycle(
        SQLAlchemyExecutionStore(session_factory),
        SQLAlchemyLeaseStore(session_factory),
    )


@pytest.mark.asyncio
async def test_postgresql_execution_full_owned_lifecycle(
    database_engine: AsyncEngine,
) -> None:
    """A PostgreSQL execution must survive the complete owned lifecycle."""
    lifecycle = make_lifecycle(database_engine)
    request = make_request()

    queued = await lifecycle.create_queued(
        request=request,
        opportunity_id=OpportunityId(
            "opportunity:postgres:lifecycle:001"
        ),
    )

    assert queued.state is PersistentExecutionState.QUEUED
    assert queued.revision == 1

    claimed = await lifecycle.claim(
        execution_id=request.execution_id,
        worker_id="worker:postgres:001",
        lease_id="lease:postgres:001",
        claimed_at=BASE_TIME + timedelta(seconds=1),
        expires_at=BASE_TIME + timedelta(minutes=5),
    )

    assert claimed.state is PersistentExecutionState.CLAIMED
    assert claimed.revision == 2
    assert claimed.worker_id == "worker:postgres:001"
    assert claimed.lease_id == "lease:postgres:001"

    executing = await lifecycle.begin(
        execution=claimed,
        worker_id="worker:postgres:001",
        lease_id="lease:postgres:001",
        started_at=BASE_TIME + timedelta(seconds=2),
    )

    assert executing.state is PersistentExecutionState.EXECUTING
    assert executing.revision == 3
    assert executing.started_at == (
        BASE_TIME + timedelta(seconds=2)
    )

    completed = await lifecycle.finish(
        execution=executing,
        worker_id="worker:postgres:001",
        lease_id="lease:postgres:001",
        target_state=PersistentExecutionState.COMPLETED,
        occurred_at=BASE_TIME + timedelta(seconds=3),
    )

    assert completed.state is PersistentExecutionState.COMPLETED
    assert completed.revision == 4
    assert completed.completed_at == (
        BASE_TIME + timedelta(seconds=3)
    )

    assert await lifecycle.get_lease(
        request.execution_id
    ) is None

    persisted = await lifecycle.get(
        request.execution_id
    )

    assert persisted is not None
    assert persisted.state is PersistentExecutionState.COMPLETED
    assert persisted.revision == 4


@pytest.mark.asyncio
async def test_postgresql_claimed_execution_becomes_recoverable_after_lease_expiry(
    database_engine: AsyncEngine,
) -> None:
    """A lost worker must leave a recoverable durable execution."""
    lifecycle = make_lifecycle(database_engine)
    request = make_request().model_copy(
        update={
            "execution_id": "execution:postgres:lifecycle:002",
            "request_id": "request:postgres:lifecycle:002",
            "task_id": TaskId(
                "task:postgres:lifecycle:002"
            ),
            "idempotency_key": IdempotencyKey(
                "idem:postgres:lifecycle:002"
            ),
        }
    )

    await lifecycle.create_queued(
        request=request,
        opportunity_id=OpportunityId(
            "opportunity:postgres:lifecycle:002"
        ),
    )

    claimed = await lifecycle.claim(
        execution_id=request.execution_id,
        worker_id="worker:postgres:002",
        lease_id="lease:postgres:002",
        claimed_at=BASE_TIME,
        expires_at=BASE_TIME + timedelta(seconds=30),
    )

    assert claimed.state is PersistentExecutionState.CLAIMED

    expired_at = BASE_TIME + timedelta(seconds=30)

    lease = await lifecycle.get_lease(
        request.execution_id
    )

    assert lease is not None
    assert lease.is_expired(expired_at) is True

    execution_store = SQLAlchemyExecutionStore(
        async_sessionmaker(
            database_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    )

    recoverable = await execution_store.find_recoverable(
        states=(
            PersistentExecutionState.CLAIMED,
            PersistentExecutionState.EXECUTING,
            PersistentExecutionState.UNKNOWN,
        ),
        now=expired_at,
        limit=10,
    )

    assert len(recoverable) == 1
    assert recoverable[0].execution_id == request.execution_id
    assert recoverable[0].state is PersistentExecutionState.CLAIMED
