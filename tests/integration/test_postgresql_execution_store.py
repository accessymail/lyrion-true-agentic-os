"""Real PostgreSQL integration tests for the execution store."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from lyrion.core.types import IdempotencyKey, OpportunityId, TaskId
from lyrion.persistence.contracts import (
    PersistentExecutionRecord,
    PersistentExecutionState,
)
from lyrion.persistence.sqlalchemy.errors import PersistenceConflictError
from lyrion.persistence.sqlalchemy.execution_store import SQLAlchemyExecutionStore
from lyrion.persistence.sqlalchemy.models import PersistentExecutionModel

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
    execution_id: str = "execution:integration:001",
) -> PersistentExecutionRecord:
    """Create a valid queued execution."""
    return PersistentExecutionRecord(
        execution_id=execution_id,
        request_id=f"request:{execution_id}",
        opportunity_id=OpportunityId(
            f"opportunity:{execution_id}",
        ),
        task_id=TaskId(
            f"task:{execution_id}",
        ),
        idempotency_key=IdempotencyKey(
            f"idem:{execution_id}",
        ),
        state=PersistentExecutionState.QUEUED,
        created_at=BASE_TIME,
        revision=1,
    )


async def fresh_store(
    database_engine: AsyncEngine,
) -> SQLAlchemyExecutionStore:
    """Create an execution store with its own session factory."""
    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return SQLAlchemyExecutionStore(session_factory)


@pytest.mark.asyncio
async def test_create_persists_across_sessions(
    database_engine: AsyncEngine,
) -> None:
    """A created execution must be visible from a later session."""
    execution = make_execution()

    store = await fresh_store(database_engine)

    created = await store.create(execution)

    assert created == execution

    loaded = await store.get(execution.execution_id)

    assert loaded == execution


@pytest.mark.asyncio
async def test_claim_persists_ownership_and_revision(
    database_engine: AsyncEngine,
) -> None:
    """Claiming must durably establish ownership and advance revision."""
    execution = make_execution()

    store = await fresh_store(database_engine)

    await store.create(execution)

    claimed = await store.claim(
        execution_id=execution.execution_id,
        worker_id="worker:001",
        lease_id="lease:001",
        claimed_at=BASE_TIME + timedelta(seconds=1),
        expected_revision=1,
    )

    assert claimed is not None
    assert claimed.state is PersistentExecutionState.CLAIMED
    assert claimed.worker_id == "worker:001"
    assert claimed.lease_id == "lease:001"
    assert claimed.revision == 2


@pytest.mark.asyncio
async def test_two_workers_compete_for_one_execution_claim(
    database_engine: AsyncEngine,
) -> None:
    """Exactly one worker may claim one queued execution revision."""
    execution = make_execution(
        execution_id="execution:integration:race",
    )

    seed_store = await fresh_store(database_engine)
    await seed_store.create(execution)

    start = asyncio.Event()

    async def attempt(
        worker_id: str,
        lease_id: str,
    ) -> bool:
        store = await fresh_store(database_engine)

        await start.wait()

        result = await store.claim(
            execution_id=execution.execution_id,
            worker_id=worker_id,
            lease_id=lease_id,
            claimed_at=BASE_TIME + timedelta(seconds=1),
            expected_revision=1,
        )

        return result is not None

    tasks = [
        asyncio.create_task(
            attempt("worker:A", "lease:A"),
        ),
        asyncio.create_task(
            attempt("worker:B", "lease:B"),
        ),
    ]

    start.set()

    results = await asyncio.gather(*tasks)

    assert sum(results) == 1

    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        result = await session.execute(
            select(PersistentExecutionModel).where(
                PersistentExecutionModel.execution_id
                == execution.execution_id,
            )
        )
        row = result.scalar_one_or_none()

    assert row is not None
    assert row.state == PersistentExecutionState.CLAIMED.value
    assert row.revision == 2
    assert row.worker_id in {"worker:A", "worker:B"}


@pytest.mark.asyncio
async def test_concurrent_same_revision_transition_has_one_winner(
    database_engine: AsyncEngine,
) -> None:
    """Two transitions from one revision must have exactly one winner."""
    execution = make_execution(
        execution_id="execution:integration:transition-race",
    )

    seed_store = await fresh_store(database_engine)

    await seed_store.create(execution)

    claimed = await seed_store.claim(
        execution_id=execution.execution_id,
        worker_id="worker:001",
        lease_id="lease:001",
        claimed_at=BASE_TIME + timedelta(seconds=1),
        expected_revision=1,
    )

    assert claimed is not None
    assert claimed.revision == 2

    start = asyncio.Event()

    async def transition() -> bool:
        store = await fresh_store(database_engine)

        await start.wait()

        try:
            await store.transition(
                execution_id=execution.execution_id,
                worker_id="worker:001",
                lease_id="lease:001",
                expected_revision=2,
                target_state=PersistentExecutionState.EXECUTING,
                occurred_at=BASE_TIME + timedelta(seconds=2),
            )
        except PersistenceConflictError:
            return False

        return True

    tasks = [
        asyncio.create_task(transition()),
        asyncio.create_task(transition()),
    ]

    start.set()

    results = await asyncio.gather(*tasks)

    assert sum(results) == 1


@pytest.mark.asyncio
async def test_wrong_worker_cannot_transition(
    database_engine: AsyncEngine,
) -> None:
    """Execution ownership must prevent mutation by another worker."""
    execution = make_execution(
        execution_id="execution:integration:ownership",
    )

    store = await fresh_store(database_engine)

    await store.create(execution)

    claimed = await store.claim(
        execution_id=execution.execution_id,
        worker_id="worker:owner",
        lease_id="lease:owner",
        claimed_at=BASE_TIME + timedelta(seconds=1),
        expected_revision=1,
    )

    assert claimed is not None

    with pytest.raises(
        PersistenceConflictError,
        match="execution transition conflict",
    ):
        await store.transition(
            execution_id=execution.execution_id,
            worker_id="worker:attacker",
            lease_id="lease:owner",
            expected_revision=2,
            target_state=PersistentExecutionState.EXECUTING,
            occurred_at=BASE_TIME + timedelta(seconds=2),
        )
