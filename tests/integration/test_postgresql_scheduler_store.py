"""Real PostgreSQL integration tests for the durable scheduler store."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from lyrion.persistence.contracts import (
    PersistentScheduler,
    PersistentSchedulerState,
)
from lyrion.persistence.sqlalchemy.errors import PersistenceConflictError
from lyrion.persistence.sqlalchemy.models import PersistentSchedulerModel
from lyrion.persistence.sqlalchemy.scheduler_store import (
    SQLAlchemySchedulerStore,
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


def make_scheduler(
    *,
    scheduler_id: str = "scheduler:001",
    state: PersistentSchedulerState = PersistentSchedulerState.READY,
    next_run_at: datetime | None = None,
    revision: int = 1,
) -> PersistentScheduler:
    """Create a valid scheduler state."""
    return PersistentScheduler(
        scheduler_id=scheduler_id,
        state=state,
        next_run_at=next_run_at,
        revision=revision,
    )


def make_store(
    engine: AsyncEngine,
) -> SQLAlchemySchedulerStore:
    """Create a scheduler store backed by PostgreSQL."""
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    return SQLAlchemySchedulerStore(factory)


@pytest.mark.asyncio
async def test_scheduler_state_round_trips(
    database_engine: AsyncEngine,
) -> None:
    """Scheduler state must persist and round-trip."""
    store = make_store(database_engine)

    scheduler = make_scheduler(
        next_run_at=BASE_TIME + timedelta(minutes=1),
    )

    saved = await store.save(scheduler)
    loaded = await store.get(scheduler.scheduler_id)

    assert saved == scheduler
    assert loaded == scheduler


@pytest.mark.asyncio
async def test_initial_scheduler_can_persist_null_next_run(
    database_engine: AsyncEngine,
) -> None:
    """INITIAL_RUN state must be representable durably."""
    store = make_store(database_engine)

    scheduler = make_scheduler(
        next_run_at=None,
    )

    await store.save(scheduler)

    loaded = await store.get(scheduler.scheduler_id)

    assert loaded is not None
    assert loaded.state is PersistentSchedulerState.READY
    assert loaded.next_run_at is None
    assert loaded.revision == 1


@pytest.mark.asyncio
async def test_paused_scheduler_state_round_trips(
    database_engine: AsyncEngine,
) -> None:
    """PAUSED must survive persistence and reload."""
    store = make_store(database_engine)

    scheduler = make_scheduler(
        state=PersistentSchedulerState.PAUSED,
        next_run_at=None,
    )

    await store.save(scheduler)

    loaded = await store.get(scheduler.scheduler_id)

    assert loaded is not None
    assert loaded.state is PersistentSchedulerState.PAUSED
    assert loaded.next_run_at is None


@pytest.mark.asyncio
async def test_duplicate_scheduler_save_raises_conflict(
    database_engine: AsyncEngine,
) -> None:
    """Duplicate scheduler identity must be rejected."""
    store = make_store(database_engine)

    scheduler = make_scheduler()

    await store.save(scheduler)

    with pytest.raises(
        PersistenceConflictError,
        match="scheduler already exists",
    ):
        await store.save(scheduler)


@pytest.mark.asyncio
async def test_transition_persists_next_run_and_increments_revision(
    database_engine: AsyncEngine,
) -> None:
    """A scheduler transition must atomically persist state and revision."""
    store = make_store(database_engine)

    await store.save(make_scheduler())

    next_run_at = BASE_TIME + timedelta(minutes=5)

    result = await store.transition(
        "scheduler:001",
        expected_revision=1,
        state=PersistentSchedulerState.READY,
        next_run_at=next_run_at,
    )

    assert result.state is PersistentSchedulerState.READY
    assert result.next_run_at == next_run_at
    assert result.revision == 2

    loaded = await store.get("scheduler:001")

    assert loaded == result


@pytest.mark.asyncio
async def test_transition_can_clear_next_run_at(
    database_engine: AsyncEngine,
) -> None:
    """A transition may persist a null next-run deadline."""
    store = make_store(database_engine)

    await store.save(
        make_scheduler(
            next_run_at=BASE_TIME + timedelta(minutes=2),
        )
    )

    result = await store.transition(
        "scheduler:001",
        expected_revision=1,
        state=PersistentSchedulerState.PAUSED,
        next_run_at=None,
    )

    assert result.state is PersistentSchedulerState.PAUSED
    assert result.next_run_at is None
    assert result.revision == 2


@pytest.mark.asyncio
async def test_stale_revision_is_rejected(
    database_engine: AsyncEngine,
) -> None:
    """Optimistic concurrency must reject stale scheduler revisions."""
    store = make_store(database_engine)

    await store.save(make_scheduler())

    with pytest.raises(
        PersistenceConflictError,
        match="scheduler revision conflict",
    ):
        await store.transition(
            "scheduler:001",
            expected_revision=2,
            state=PersistentSchedulerState.PAUSED,
            next_run_at=None,
        )


@pytest.mark.asyncio
async def test_restart_semantics_reload_persisted_scheduler_state(
    database_engine: AsyncEngine,
) -> None:
    """A fresh store instance must recover the exact persisted scheduler state."""
    first_store = make_store(database_engine)

    persisted_next_run = BASE_TIME + timedelta(minutes=10)

    original = make_scheduler(
        state=PersistentSchedulerState.READY,
        next_run_at=persisted_next_run,
        revision=4,
    )

    await first_store.save(original)

    # Simulate a process restart by discarding the original store
    # and constructing a completely new persistence adapter.
    del first_store

    restarted_store = make_store(database_engine)

    recovered = await restarted_store.get("scheduler:001")

    assert recovered == original
    assert recovered is not original


@pytest.mark.asyncio
async def test_physical_postgresql_row_matches_scheduler_state(
    database_engine: AsyncEngine,
) -> None:
    """The PostgreSQL row must contain the durable scheduler state."""
    store = make_store(database_engine)

    scheduler = make_scheduler(
        state=PersistentSchedulerState.READY,
        next_run_at=BASE_TIME + timedelta(minutes=3),
        revision=2,
    )

    await store.save(scheduler)

    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        row = await session.scalar(
            select(PersistentSchedulerModel).where(
                PersistentSchedulerModel.scheduler_id
                == "scheduler:001",
            )
        )

    assert row is not None
    assert row.scheduler_id == "scheduler:001"
    assert row.state == PersistentSchedulerState.READY.value
    assert row.next_run_at == scheduler.next_run_at
    assert row.revision == 2
