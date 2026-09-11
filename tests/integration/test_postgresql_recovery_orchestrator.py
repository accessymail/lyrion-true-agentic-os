"""PostgreSQL integration tests for durable recovery orchestration."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from lyrion.core.types import (
    IdempotencyKey,
    OpportunityId,
    TaskId,
)
from lyrion.persistence.contracts import (
    PersistentExecutionRecord,
    PersistentExecutionState,
    RecoveryAction,
    RuntimeLease,
)
from lyrion.persistence.protocols import ExecutionStore
from lyrion.persistence.recovery_orchestrator import (
    PersistentRecoveryOrchestrator,
)
from lyrion.persistence.sqlalchemy.models import (
    PersistentExecutionModel,
    RecoveryDecisionModel,
    RuntimeLeaseModel,
)
from lyrion.persistence.sqlalchemy.uow import (
    SQLAlchemyPersistenceUnitOfWork,
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


def make_execution(
    *,
    execution_id: str,
    state: PersistentExecutionState,
    revision: int = 1,
    claimed: bool = False,
    started: bool = False,
) -> PersistentExecutionRecord:
    """Create a valid durable execution record."""
    claimed_at = (
        BASE_TIME + timedelta(seconds=1)
        if claimed
        else None
    )

    started_at = (
        BASE_TIME + timedelta(seconds=2)
        if started
        else None
    )

    return PersistentExecutionRecord(
        execution_id=execution_id,
        request_id=f"request:{execution_id}",
        opportunity_id=OpportunityId(
            f"opportunity:{execution_id}"
        ),
        task_id=TaskId(
            f"task:{execution_id}"
        ),
        idempotency_key=IdempotencyKey(
            f"idem:{execution_id}"
        ),
        state=state,
        created_at=BASE_TIME,
        claimed_at=claimed_at,
        started_at=started_at,
        worker_id=(
            "worker:recovery"
            if claimed
            else None
        ),
        lease_id=(
            "lease:recovery"
            if claimed
            else None
        ),
        revision=revision,
    )


def make_lease(
    *,
    resource_id: str,
) -> RuntimeLease:
    """Create an expired execution lease."""
    return RuntimeLease(
        lease_id="lease:recovery",
        resource_id=resource_id,
        worker_id="worker:recovery",
        acquired_at=BASE_TIME,
        expires_at=BASE_TIME + timedelta(seconds=30),
        revision=1,
    )


def make_session_factory(
    database_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create an async PostgreSQL session factory."""
    return async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.mark.asyncio
async def test_postgresql_recovery_requeues_expired_claimed_execution(
    database_engine: AsyncEngine,
) -> None:
    """Expired CLAIMED work must be requeued atomically."""
    session_factory = make_session_factory(
        database_engine,
    )

    execution_id = (
        "execution:postgres:recovery:requeue:001"
    )

    async with SQLAlchemyPersistenceUnitOfWork(
        session_factory,
    ) as uow:
        execution = make_execution(
            execution_id=execution_id,
            state=PersistentExecutionState.CLAIMED,
            revision=2,
            claimed=True,
        )

        await uow.executions.create(execution)

        lease = make_lease(
            resource_id=execution_id,
        )

        acquired = await uow.leases.acquire(
            resource_id=lease.resource_id,
            worker_id=lease.worker_id,
            lease_id=lease.lease_id,
            acquired_at=lease.acquired_at,
            expires_at=lease.expires_at,
        )

        assert acquired is not None

        orchestrator = PersistentRecoveryOrchestrator(
            uow.executions,
            uow.leases,
            uow.recovery,
        )

        action = await orchestrator.recover_one(
            execution_id=execution_id,
            now=BASE_TIME + timedelta(seconds=30),
        )

        assert action is RecoveryAction.REQUEUE

    async with session_factory() as session:
        execution_model = await session.scalar(
            select(PersistentExecutionModel).where(
                PersistentExecutionModel.execution_id
                == execution_id,
            )
        )
        lease_model = await session.scalar(
            select(RuntimeLeaseModel).where(
                RuntimeLeaseModel.resource_id
                == execution_id,
            )
        )
        decision_model = await session.scalar(
            select(RecoveryDecisionModel).where(
                RecoveryDecisionModel.execution_id
                == execution_id,
            )
        )

    assert execution_model is not None
    assert execution_model.state == (
        PersistentExecutionState.QUEUED.value
    )
    assert execution_model.worker_id is None
    assert execution_model.lease_id is None
    assert execution_model.claimed_at is None
    assert execution_model.revision == 3

    assert lease_model is None

    assert decision_model is not None
    assert decision_model.action == RecoveryAction.REQUEUE.value
    assert decision_model.source_revision == 2


@pytest.mark.asyncio
async def test_postgresql_recovery_reconciles_expired_executing_execution(
    database_engine: AsyncEngine,
) -> None:
    """Expired EXECUTING work must remain unresolved."""
    session_factory = make_session_factory(
        database_engine,
    )

    execution_id = (
        "execution:postgres:recovery:reconcile:001"
    )

    async with SQLAlchemyPersistenceUnitOfWork(
        session_factory,
    ) as uow:
        execution = make_execution(
            execution_id=execution_id,
            state=PersistentExecutionState.EXECUTING,
            revision=3,
            claimed=True,
            started=True,
        )

        await uow.executions.create(execution)

        lease = make_lease(
            resource_id=execution_id,
        )

        acquired = await uow.leases.acquire(
            resource_id=lease.resource_id,
            worker_id=lease.worker_id,
            lease_id=lease.lease_id,
            acquired_at=lease.acquired_at,
            expires_at=lease.expires_at,
        )

        assert acquired is not None

        orchestrator = PersistentRecoveryOrchestrator(
            uow.executions,
            uow.leases,
            uow.recovery,
        )

        action = await orchestrator.recover_one(
            execution_id=execution_id,
            now=BASE_TIME + timedelta(seconds=30),
        )

        assert action is RecoveryAction.RECONCILE

    async with session_factory() as session:
        execution_model = await session.scalar(
            select(PersistentExecutionModel).where(
                PersistentExecutionModel.execution_id
                == execution_id,
            )
        )
        lease_model = await session.scalar(
            select(RuntimeLeaseModel).where(
                RuntimeLeaseModel.resource_id
                == execution_id,
            )
        )
        decision_model = await session.scalar(
            select(RecoveryDecisionModel).where(
                RecoveryDecisionModel.execution_id
                == execution_id,
            )
        )

    assert execution_model is not None
    assert execution_model.state == (
        PersistentExecutionState.EXECUTING.value
    )
    assert execution_model.revision == 3
    assert execution_model.worker_id == "worker:recovery"
    assert execution_model.lease_id == "lease:recovery"

    assert lease_model is not None

    assert decision_model is not None
    assert decision_model.action == (
        RecoveryAction.RECONCILE.value
    )


@pytest.mark.asyncio
async def test_postgresql_recovery_decision_and_requeue_roll_back_together(
    database_engine: AsyncEngine,
) -> None:
    """Recovery decision and mutation must share one transaction."""
    session_factory = make_session_factory(
        database_engine,
    )

    execution_id = (
        "execution:postgres:recovery:rollback:001"
    )

    # Remove leftovers from any previous interrupted test run.
    async with session_factory.begin() as cleanup:
        await cleanup.execute(
            text(
                "DELETE FROM recovery_decisions "
                "WHERE execution_id = :execution_id"
            ),
            {"execution_id": execution_id},
        )
        await cleanup.execute(
            text(
                "DELETE FROM runtime_leases "
                "WHERE resource_id = :execution_id"
            ),
            {"execution_id": execution_id},
        )
        await cleanup.execute(
            text(
                "DELETE FROM persistent_executions "
                "WHERE execution_id = :execution_id"
            ),
            {"execution_id": execution_id},
        )

    class FailingExecutionStore:
        """Execution-store proxy that fails during requeue."""

        def __init__(
            self,
            inner: ExecutionStore,
        ) -> None:
            """Store the transaction-bound execution store."""
            self._inner = inner

        async def create(
            self,
            record: PersistentExecutionRecord,
        ) -> PersistentExecutionRecord:
            """Delegate execution creation."""
            return await self._inner.create(record)

        async def get(
            self,
            requested_execution_id: str,
        ) -> PersistentExecutionRecord | None:
            """Load through the real execution store."""
            return await self._inner.get(
                requested_execution_id,
            )

        async def claim(
            self,
            *,
            execution_id: str,
            worker_id: str,
            lease_id: str,
            claimed_at: datetime,
            expected_revision: int,
        ) -> PersistentExecutionRecord | None:
            """Delegate execution claiming."""
            return await self._inner.claim(
                execution_id=execution_id,
                worker_id=worker_id,
                lease_id=lease_id,
                claimed_at=claimed_at,
                expected_revision=expected_revision,
            )

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
            """Delegate lifecycle transitions."""
            return await self._inner.transition(
                execution_id=execution_id,
                worker_id=worker_id,
                lease_id=lease_id,
                expected_revision=expected_revision,
                target_state=target_state,
                occurred_at=occurred_at,
                checkpoint_ref=checkpoint_ref,
                error_code=error_code,
                error_message=error_message,
            )

        async def requeue(
            self,
            *,
            execution_id: str,
            expected_revision: int,
            occurred_at: datetime,
        ) -> PersistentExecutionRecord:
            """Force the recovery mutation to fail."""
            del execution_id
            del expected_revision
            del occurred_at

            raise RuntimeError(
                "force recovery rollback",
            )

        async def find_recoverable(
            self,
            *,
            states: Sequence[PersistentExecutionState],
            now: datetime,
            limit: int,
        ) -> Sequence[PersistentExecutionRecord]:
            """Delegate recovery lookup."""
            return await self._inner.find_recoverable(
                states=states,
                now=now,
                limit=limit,
            )

    with pytest.raises(
        RuntimeError,
        match="force recovery rollback",
    ):
        async with SQLAlchemyPersistenceUnitOfWork(
            session_factory,
        ) as uow:
            execution = make_execution(
                execution_id=execution_id,
                state=PersistentExecutionState.CLAIMED,
                revision=2,
                claimed=True,
            )

            await uow.executions.create(execution)

            lease = make_lease(
                resource_id=execution_id,
            )

            acquired = await uow.leases.acquire(
                resource_id=lease.resource_id,
                worker_id=lease.worker_id,
                lease_id=lease.lease_id,
                acquired_at=lease.acquired_at,
                expires_at=lease.expires_at,
            )

            assert acquired is not None

            orchestrator = PersistentRecoveryOrchestrator(
                FailingExecutionStore(uow.executions),
                uow.leases,
                uow.recovery,
            )

            await orchestrator.recover_one(
                execution_id=execution_id,
                now=BASE_TIME + timedelta(seconds=30),
            )

    async with session_factory() as session:
        execution_model = await session.scalar(
            select(PersistentExecutionModel).where(
                PersistentExecutionModel.execution_id
                == execution_id,
            )
        )
        lease_model = await session.scalar(
            select(RuntimeLeaseModel).where(
                RuntimeLeaseModel.resource_id
                == execution_id,
            )
        )
        decision_model = await session.scalar(
            select(RecoveryDecisionModel).where(
                RecoveryDecisionModel.execution_id
                == execution_id,
            )
        )

    assert execution_model is None
    assert lease_model is None
    assert decision_model is None
