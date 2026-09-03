"""Tests for persistence-aware scheduler orchestration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from lyrion.integration.persistent_scheduler import (
    PersistentSchedulerCoordinator,
)
from lyrion.persistence.contracts import (
    PersistentScheduler,
    PersistentSchedulerState,
)
from lyrion.persistence.sqlalchemy.errors import (
    PersistenceConflictError,
)
from lyrion.piae.scheduler import (
    ControlledSchedulerConfig,
    SchedulerState,
)

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
    state: PersistentSchedulerState = PersistentSchedulerState.READY,
    next_run_at: datetime | None = None,
    revision: int = 1,
) -> PersistentScheduler:
    """Create a valid persisted scheduler state."""
    return PersistentScheduler(
        scheduler_id="scheduler:001",
        state=state,
        next_run_at=next_run_at,
        revision=revision,
    )


class FakeSchedulerStore:
    """In-memory SchedulerStore test double."""

    def __init__(
        self,
        persisted: PersistentScheduler | None = None,
    ) -> None:
        """Initialize the store."""
        self.persisted = persisted
        self.saved: list[PersistentScheduler] = []
        self.transitions: list[dict[str, Any]] = []

    async def get(
        self,
        scheduler_id: str,
    ) -> PersistentScheduler | None:
        """Return persisted scheduler state."""
        if (
            self.persisted is not None
            and self.persisted.scheduler_id == scheduler_id
        ):
            return self.persisted

        return None

    async def save(
        self,
        scheduler: PersistentScheduler,
    ) -> PersistentScheduler:
        """Persist a new scheduler."""
        self.saved.append(scheduler)
        self.persisted = scheduler
        return scheduler

    async def transition(
        self,
        scheduler_id: str,
        *,
        expected_revision: int,
        state: PersistentSchedulerState,
        next_run_at: datetime | None,
    ) -> PersistentScheduler:
        """Persist a scheduler transition."""
        assert self.persisted is not None
        assert self.persisted.scheduler_id == scheduler_id
        assert self.persisted.revision == expected_revision

        scheduler = PersistentScheduler(
            scheduler_id=scheduler_id,
            state=state,
            next_run_at=next_run_at,
            revision=expected_revision + 1,
        )

        self.transitions.append(
            {
                "scheduler_id": scheduler_id,
                "expected_revision": expected_revision,
                "state": state,
                "next_run_at": next_run_at,
            }
        )

        self.persisted = scheduler
        return scheduler


@pytest.mark.asyncio
async def test_initialize_creates_missing_scheduler() -> None:
    """Missing durable state should create an initial scheduler."""
    store = FakeSchedulerStore()

    coordinator = PersistentSchedulerCoordinator(
        store,
        scheduler_id="scheduler:001",
    )

    scheduler = await coordinator.initialize()

    assert scheduler.state is SchedulerState.READY
    assert scheduler.next_run_at is None
    assert coordinator.revision == 1
    assert len(store.saved) == 1


@pytest.mark.asyncio
async def test_initialize_restores_persisted_state() -> None:
    """Existing durable state must restore scheduler behavior."""
    persisted = make_scheduler(
        state=PersistentSchedulerState.PAUSED,
        next_run_at=None,
        revision=4,
    )

    store = FakeSchedulerStore(persisted)

    coordinator = PersistentSchedulerCoordinator(
        store,
        scheduler_id="scheduler:001",
    )

    scheduler = await coordinator.initialize()

    assert scheduler.state is SchedulerState.PAUSED
    assert scheduler.next_run_at is None
    assert coordinator.revision == 4
    assert store.saved == []


@pytest.mark.asyncio
async def test_future_next_run_survives_restoration() -> None:
    """Persisted future timing must remain not-due after restoration."""
    next_run = BASE_TIME + timedelta(minutes=5)

    coordinator = PersistentSchedulerCoordinator(
        FakeSchedulerStore(
            make_scheduler(
                next_run_at=next_run,
                revision=7,
            )
        ),
        scheduler_id="scheduler:001",
        config=ControlledSchedulerConfig(
            interval_seconds=60,
        ),
    )

    await coordinator.initialize()

    decision = coordinator.evaluate(
        now=BASE_TIME + timedelta(minutes=4),
    )

    assert decision.due is False
    assert decision.reason == "NOT_DUE"
    assert decision.next_run_at == next_run


@pytest.mark.asyncio
async def test_pause_persists_state_transition() -> None:
    """Pause must update durable scheduler state."""
    store = FakeSchedulerStore(
        make_scheduler(
            revision=3,
        )
    )

    coordinator = PersistentSchedulerCoordinator(
        store,
        scheduler_id="scheduler:001",
    )

    await coordinator.initialize()
    persisted = await coordinator.pause()

    assert persisted.state is PersistentSchedulerState.PAUSED
    assert coordinator.scheduler.state is SchedulerState.PAUSED
    assert coordinator.revision == 4


@pytest.mark.asyncio
async def test_resume_persists_immediate_next_run() -> None:
    """Resume must persist READY plus the immediate deadline."""
    store = FakeSchedulerStore(
        make_scheduler(
            state=PersistentSchedulerState.PAUSED,
            revision=5,
        )
    )

    coordinator = PersistentSchedulerCoordinator(
        store,
        scheduler_id="scheduler:001",
    )

    await coordinator.initialize()

    persisted = await coordinator.resume(
        now=BASE_TIME,
    )

    assert persisted.state is PersistentSchedulerState.READY
    assert persisted.next_run_at == BASE_TIME
    assert persisted.revision == 6


@pytest.mark.asyncio
async def test_cycle_completion_persists_next_run() -> None:
    """Completed cycles must persist the new scheduling deadline."""
    store = FakeSchedulerStore(
        make_scheduler(
            revision=2,
        )
    )

    coordinator = PersistentSchedulerCoordinator(
        store,
        scheduler_id="scheduler:001",
        config=ControlledSchedulerConfig(
            interval_seconds=60,
        ),
    )

    await coordinator.initialize()

    persisted = await coordinator.mark_cycle_completed(
        now=BASE_TIME,
    )

    assert persisted.next_run_at == (
        BASE_TIME + timedelta(seconds=60)
    )
    assert persisted.revision == 3


@pytest.mark.asyncio
async def test_mutation_before_initialize_fails_closed() -> None:
    """Scheduler mutation must require durable initialization."""
    coordinator = PersistentSchedulerCoordinator(
        FakeSchedulerStore(),
        scheduler_id="scheduler:001",
    )

    with pytest.raises(
        RuntimeError,
        match="not initialized",
    ):
        await coordinator.pause()


@pytest.mark.asyncio
async def test_empty_scheduler_id_is_rejected() -> None:
    """Scheduler identity must be non-empty."""
    with pytest.raises(
        ValueError,
        match="scheduler_id must not be empty",
    ):
        PersistentSchedulerCoordinator(
            FakeSchedulerStore(),
            scheduler_id=" ",
        )


@pytest.mark.asyncio
async def test_revision_advances_after_each_persisted_transition() -> None:
    """Each successful transition must advance optimistic revision."""
    store = FakeSchedulerStore(
        make_scheduler(
            revision=10,
        )
    )

    coordinator = PersistentSchedulerCoordinator(
        store,
        scheduler_id="scheduler:001",
    )

    await coordinator.initialize()
    await coordinator.pause()
    await coordinator.resume(
        now=BASE_TIME,
    )

    assert coordinator.revision == 12
    assert [
        transition["expected_revision"]
        for transition in store.transitions
    ] == [10, 11]


@pytest.mark.asyncio
async def test_persistence_conflict_is_propagated() -> None:
    """Scheduler persistence conflicts must not be swallowed."""
    class ConflictStore(FakeSchedulerStore):
        async def transition(
            self,
            scheduler_id: str,
            *,
            expected_revision: int,
            state: PersistentSchedulerState,
            next_run_at: datetime | None,
        ) -> PersistentScheduler:
            """Reject the transition as a stale revision."""
            del scheduler_id
            del expected_revision
            del state
            del next_run_at

            raise PersistenceConflictError(
                "scheduler revision conflict",
            )

    coordinator = PersistentSchedulerCoordinator(
        ConflictStore(
            make_scheduler(
                revision=3,
            )
        ),
        scheduler_id="scheduler:001",
    )

    await coordinator.initialize()

    with pytest.raises(
        PersistenceConflictError,
        match="scheduler revision conflict",
    ):
        await coordinator.pause()


@pytest.mark.asyncio
async def test_persistence_conflict_preserves_previous_scheduler_state() -> None:
    """A failed durable transition must not mutate in-memory state."""
    class ConflictStore(FakeSchedulerStore):
        async def transition(
            self,
            scheduler_id: str,
            *,
            expected_revision: int,
            state: PersistentSchedulerState,
            next_run_at: datetime | None,
        ) -> PersistentScheduler:
            """Reject every transition."""
            del scheduler_id
            del expected_revision
            del state
            del next_run_at

            raise PersistenceConflictError(
                "scheduler revision conflict",
            )

    original_next_run = BASE_TIME + timedelta(minutes=5)

    coordinator = PersistentSchedulerCoordinator(
        ConflictStore(
            make_scheduler(
                state=PersistentSchedulerState.READY,
                next_run_at=original_next_run,
                revision=3,
            )
        ),
        scheduler_id="scheduler:001",
    )

    await coordinator.initialize()

    with pytest.raises(
        PersistenceConflictError,
        match="scheduler revision conflict",
    ):
        await coordinator.pause()

    assert coordinator.scheduler.state is SchedulerState.READY
    assert coordinator.scheduler.next_run_at == original_next_run
    assert coordinator.revision == 3
