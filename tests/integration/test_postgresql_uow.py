"""Real PostgreSQL integration tests for the persistence unit of work."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from lyrion.core.types import IdempotencyKey, OpportunityId, TaskId
from lyrion.persistence.contracts import (
    PersistentExecutionRecord,
    PersistentExecutionState,
    PersistentIdempotencyRecord,
    PersistentOpportunity,
    PersistentOpportunityState,
    PersistentScheduler,
    PersistentSchedulerState,
    RecoveryAction,
    RecoveryDecision,
    RuntimeInstance,
    RuntimeLifecycleState,
)
from lyrion.persistence.sqlalchemy.models import (
    PersistentExecutionModel,
    PersistentIdempotencyModel,
    PersistentOpportunityModel,
    PersistentSchedulerModel,
    RecoveryDecisionModel,
    RuntimeInstanceModel,
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


def make_runtime() -> RuntimeInstance:
    """Create a valid runtime instance."""
    return RuntimeInstance(
        instance_id="instance:uow:001",
        state=RuntimeLifecycleState.STARTING,
        started_at=BASE_TIME,
        heartbeat_at=BASE_TIME,
        revision=1,
    )


def make_opportunity() -> PersistentOpportunity:
    """Create a valid queued opportunity."""
    return PersistentOpportunity(
        opportunity_id=OpportunityId("opportunity:uow:001"),
        state=PersistentOpportunityState.QUEUED,
        created_at=BASE_TIME,
        revision=1,
    )


def make_execution() -> PersistentExecutionRecord:
    """Create a valid queued execution."""
    return PersistentExecutionRecord(
        execution_id="execution:uow:001",
        request_id="request:uow:001",
        opportunity_id=OpportunityId("opportunity:uow:001"),
        task_id=TaskId("task:uow:001"),
        idempotency_key=IdempotencyKey("idem:uow:001"),
        state=PersistentExecutionState.QUEUED,
        created_at=BASE_TIME,
        revision=1,
    )


def make_idempotency() -> PersistentIdempotencyRecord:
    """Create a valid idempotency reservation."""
    return PersistentIdempotencyRecord(
        idempotency_key="idem:uow:001",
        request_id="request:uow:001",
        execution_id="execution:uow:001",
        reserved_at=BASE_TIME,
    )


def make_scheduler() -> PersistentScheduler:
    """Create a valid persisted scheduler state."""
    return PersistentScheduler(
        scheduler_id="scheduler:uow:001",
        state=PersistentSchedulerState.READY,
        next_run_at=BASE_TIME,
        revision=1,
    )


def make_recovery() -> RecoveryDecision:
    """Create a valid recovery decision."""
    return RecoveryDecision(
        execution_id="execution:uow:001",
        action=RecoveryAction.REQUEUE,
        reason="Lease expired.",
        evaluated_at=BASE_TIME,
        source_revision=1,
    )


@pytest.mark.asyncio
async def test_uow_commits_cross_store_mutations(
    database_engine: AsyncEngine,
) -> None:
    """Successful UoW mutations must commit as one transaction."""
    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with SQLAlchemyPersistenceUnitOfWork(session_factory) as uow:
        await uow.runtime.save(make_runtime())
        await uow.opportunities.create(make_opportunity())
        await uow.executions.create(make_execution())
        assert await uow.idempotency.reserve(make_idempotency()) is True
        await uow.recovery.record(make_recovery())
        await uow.scheduler.save(make_scheduler())

    async with session_factory() as session:
        runtime = await session.scalar(
            select(RuntimeInstanceModel).where(
                RuntimeInstanceModel.instance_id
                == "instance:uow:001",
            )
        )
        opportunity = await session.scalar(
            select(PersistentOpportunityModel).where(
                PersistentOpportunityModel.opportunity_id
                == "opportunity:uow:001",
            )
        )
        execution = await session.scalar(
            select(PersistentExecutionModel).where(
                PersistentExecutionModel.execution_id
                == "execution:uow:001",
            )
        )
        idempotency = await session.scalar(
            select(PersistentIdempotencyModel).where(
                PersistentIdempotencyModel.idempotency_key
                == "idem:uow:001",
            )
        )
        recovery = await session.scalar(
            select(RecoveryDecisionModel).where(
                RecoveryDecisionModel.execution_id
                == "execution:uow:001",
            )
        )
        scheduler = await session.scalar(
            select(PersistentSchedulerModel).where(
                PersistentSchedulerModel.scheduler_id
                == "scheduler:uow:001",
            )
        )

    assert runtime is not None
    assert opportunity is not None
    assert execution is not None
    assert idempotency is not None
    assert recovery is not None
    assert scheduler is not None


@pytest.mark.asyncio
async def test_uow_rolls_back_all_cross_store_mutations(
    database_engine: AsyncEngine,
) -> None:
    """Any exception must roll back every mutation in the UoW."""
    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    with pytest.raises(RuntimeError, match="force rollback"):
        async with SQLAlchemyPersistenceUnitOfWork(session_factory) as uow:
            await uow.runtime.save(make_runtime())
            await uow.opportunities.create(make_opportunity())
            await uow.executions.create(make_execution())
            assert await uow.idempotency.reserve(make_idempotency()) is True
            await uow.recovery.record(make_recovery())
            await uow.scheduler.save(make_scheduler())

            raise RuntimeError("force rollback")

    async with session_factory() as session:
        runtime = await session.scalar(
            select(RuntimeInstanceModel).where(
                RuntimeInstanceModel.instance_id
                == "instance:uow:001",
            )
        )
        opportunity = await session.scalar(
            select(PersistentOpportunityModel).where(
                PersistentOpportunityModel.opportunity_id
                == "opportunity:uow:001",
            )
        )
        execution = await session.scalar(
            select(PersistentExecutionModel).where(
                PersistentExecutionModel.execution_id
                == "execution:uow:001",
            )
        )
        idempotency = await session.scalar(
            select(PersistentIdempotencyModel).where(
                PersistentIdempotencyModel.idempotency_key
                == "idem:uow:001",
            )
        )
        recovery = await session.scalar(
            select(RecoveryDecisionModel).where(
                RecoveryDecisionModel.execution_id
                == "execution:uow:001",
            )
        )
        scheduler = await session.scalar(
            select(PersistentSchedulerModel).where(
                PersistentSchedulerModel.scheduler_id
                == "scheduler:uow:001",
            )
        )

    assert runtime is None
    assert opportunity is None
    assert execution is None
    assert idempotency is None
    assert recovery is None
    assert scheduler is None


@pytest.mark.asyncio
async def test_uow_stores_share_one_session(
    database_engine: AsyncEngine,
) -> None:
    """All stores in one UoW must execute through the same session."""
    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with SQLAlchemyPersistenceUnitOfWork(session_factory) as uow:
        assert uow.runtime._session is uow.opportunities._session
        assert uow.opportunities._session is uow.leases._session
        assert uow.leases._session is uow.executions._session
        assert uow.executions._session is uow.idempotency._session
        assert uow.idempotency._session is uow.recovery._session
        assert uow.recovery._session is uow.scheduler._session


@pytest.mark.asyncio
async def test_uow_observes_uncommitted_cross_store_state(
    database_engine: AsyncEngine,
) -> None:
    """Stores in one UoW must see mutations made earlier in that UoW."""
    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with SQLAlchemyPersistenceUnitOfWork(session_factory) as uow:
        execution = make_execution()

        await uow.executions.create(execution)

        loaded = await uow.executions.get(
            execution.execution_id,
        )

        assert loaded == execution

        assert await uow.idempotency.contains(
            execution.idempotency_key,
        ) is False


@pytest.mark.asyncio
async def test_scheduler_and_execution_commit_atomically(
    database_engine: AsyncEngine,
) -> None:
    """Scheduler and execution state must commit in one transaction."""
    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with SQLAlchemyPersistenceUnitOfWork(session_factory) as uow:
        await uow.scheduler.save(make_scheduler())
        await uow.opportunities.create(make_opportunity())
        await uow.executions.create(make_execution())

    async with session_factory() as session:
        scheduler = await session.scalar(
            select(PersistentSchedulerModel).where(
                PersistentSchedulerModel.scheduler_id
                == "scheduler:uow:001",
            )
        )
        opportunity = await session.scalar(
            select(PersistentOpportunityModel).where(
                PersistentOpportunityModel.opportunity_id
                == "opportunity:uow:001",
            )
        )
        execution = await session.scalar(
            select(PersistentExecutionModel).where(
                PersistentExecutionModel.execution_id
                == "execution:uow:001",
            )
        )

    assert scheduler is not None
    assert opportunity is not None
    assert execution is not None


@pytest.mark.asyncio
async def test_scheduler_and_execution_rollback_atomically(
    database_engine: AsyncEngine,
) -> None:
    """Scheduler and execution state must roll back together."""
    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    with pytest.raises(RuntimeError, match="force rollback"):
        async with SQLAlchemyPersistenceUnitOfWork(session_factory) as uow:
            await uow.scheduler.save(make_scheduler())
            await uow.opportunities.create(make_opportunity())
            await uow.executions.create(make_execution())

            raise RuntimeError("force rollback")

    async with session_factory() as session:
        scheduler = await session.scalar(
            select(PersistentSchedulerModel).where(
                PersistentSchedulerModel.scheduler_id
                == "scheduler:uow:001",
            )
        )
        opportunity = await session.scalar(
            select(PersistentOpportunityModel).where(
                PersistentOpportunityModel.opportunity_id
                == "opportunity:uow:001",
            )
        )
        execution = await session.scalar(
            select(PersistentExecutionModel).where(
                PersistentExecutionModel.execution_id
                == "execution:uow:001",
            )
        )

    assert scheduler is None
    assert opportunity is None
    assert execution is None


@pytest.mark.asyncio
async def test_persistent_scheduler_coordinator_uses_uow_transaction(
    database_engine: AsyncEngine,
) -> None:
    """Scheduler coordinator state must commit with the same UoW."""
    from lyrion.integration.persistent_scheduler import (
        PersistentSchedulerCoordinator,
    )

    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with SQLAlchemyPersistenceUnitOfWork(session_factory) as uow:
        coordinator = PersistentSchedulerCoordinator(
            uow.scheduler,
            scheduler_id="scheduler:uow:coordinator:001",
        )

        scheduler = await coordinator.initialize()

        assert scheduler.next_run_at is None
        assert coordinator.revision == 1

        await uow.executions.create(
            PersistentExecutionRecord(
                execution_id="execution:uow:coordinator:001",
                request_id="request:uow:coordinator:001",
                opportunity_id=OpportunityId(
                    "opportunity:uow:coordinator:001",
                ),
                task_id=TaskId(
                    "task:uow:coordinator:001",
                ),
                idempotency_key=IdempotencyKey(
                    "idem:uow:coordinator:001",
                ),
                state=PersistentExecutionState.QUEUED,
                created_at=BASE_TIME,
                revision=1,
            )
        )

        persisted = await coordinator.resume(
            now=BASE_TIME,
        )

        assert persisted.state is PersistentSchedulerState.READY
        assert persisted.next_run_at == BASE_TIME
        assert persisted.revision == 2

    async with session_factory() as session:
        scheduler = await session.scalar(
            select(PersistentSchedulerModel).where(
                PersistentSchedulerModel.scheduler_id
                == "scheduler:uow:coordinator:001",
            )
        )
        execution = await session.scalar(
            select(PersistentExecutionModel).where(
                PersistentExecutionModel.execution_id
                == "execution:uow:coordinator:001",
            )
        )

    assert scheduler is not None
    assert scheduler.state == PersistentSchedulerState.READY.value
    assert scheduler.next_run_at == BASE_TIME
    assert scheduler.revision == 2
    assert execution is not None


@pytest.mark.asyncio
async def test_persistent_scheduler_coordinator_rolls_back_with_uow(
    database_engine: AsyncEngine,
) -> None:
    """Scheduler coordinator mutations must roll back with the UoW."""
    from lyrion.integration.persistent_scheduler import (
        PersistentSchedulerCoordinator,
    )

    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    with pytest.raises(
        RuntimeError,
        match="force scheduler rollback",
    ):
        async with SQLAlchemyPersistenceUnitOfWork(session_factory) as uow:
            coordinator = PersistentSchedulerCoordinator(
                uow.scheduler,
                scheduler_id="scheduler:uow:coordinator:002",
            )

            await coordinator.initialize()

            await uow.opportunities.create(
                PersistentOpportunity(
                    opportunity_id=OpportunityId(
                        "opportunity:uow:coordinator:002",
                    ),
                    state=PersistentOpportunityState.QUEUED,
                    created_at=BASE_TIME,
                    revision=1,
                )
            )

            await coordinator.mark_cycle_completed(
                now=BASE_TIME,
            )

            raise RuntimeError(
                "force scheduler rollback",
            )

    async with session_factory() as session:
        scheduler = await session.scalar(
            select(PersistentSchedulerModel).where(
                PersistentSchedulerModel.scheduler_id
                == "scheduler:uow:coordinator:002",
            )
        )
        opportunity = await session.scalar(
            select(PersistentOpportunityModel).where(
                PersistentOpportunityModel.opportunity_id
                == "opportunity:uow:coordinator:002",
            )
        )

    assert scheduler is None
    assert opportunity is None
