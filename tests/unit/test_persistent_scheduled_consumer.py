"""Tests for persistence-aware scheduled PIAE consumption."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from lyrion.integration.persistent_scheduled_consumer import (
    PersistentScheduledPIAEConsumer,
)
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
from lyrion.piae.controlled_queue_consumer import (
    ControlledQueueCycleResult,
)
from lyrion.piae.scheduled_consumer import CandidateFactory
from lyrion.piae.scheduler import SchedulerState

BASE_TIME = datetime(
    2026,
    8,
    31,
    12,
    0,
    tzinfo=UTC,
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

        self.persisted = scheduler
        return scheduler


class FakeBoundedConsumer:
    """Record bounded consumer invocations."""

    def __init__(
        self,
        result: ControlledQueueCycleResult | None = None,
    ) -> None:
        """Initialize the fake consumer."""
        self.calls = 0
        self.times: list[datetime | None] = []
        self.result = result or ControlledQueueCycleResult(
            items=(),
            stop_reason="QUEUE_EMPTY",
        )

    def run_once(
        self,
        *,
        candidates_factory: CandidateFactory,
        now: datetime | None = None,
    ) -> ControlledQueueCycleResult:
        """Record one bounded consumer call."""
        del candidates_factory

        self.calls += 1
        self.times.append(now)

        return self.result


class RaisingBoundedConsumer:
    """Bounded consumer that raises infrastructure failure."""

    def __init__(self) -> None:
        """Initialize the fake."""
        self.calls = 0

    def run_once(
        self,
        *,
        candidates_factory: CandidateFactory,
        now: datetime | None = None,
    ) -> ControlledQueueCycleResult:
        """Raise a deterministic infrastructure failure."""
        del candidates_factory
        del now

        self.calls += 1

        raise RuntimeError(
            "intentional infrastructure failure",
        )


def make_coordinator(
    *,
    state: PersistentSchedulerState = (
        PersistentSchedulerState.READY
    ),
    next_run_at: datetime | None = None,
    revision: int = 1,
) -> PersistentSchedulerCoordinator:
    """Create a persistent scheduler coordinator."""
    store = FakeSchedulerStore(
        PersistentScheduler(
            scheduler_id="scheduler:001",
            state=state,
            next_run_at=next_run_at,
            revision=revision,
        )
    )

    return PersistentSchedulerCoordinator(
        store,
        scheduler_id="scheduler:001",
    )


@pytest.mark.asyncio
async def test_not_due_does_not_consume() -> None:
    """A non-due persistent schedule must remain blocked."""
    coordinator = make_coordinator(
        next_run_at=BASE_TIME + timedelta(seconds=60),
    )
    consumer = FakeBoundedConsumer()

    await coordinator.initialize()

    scheduled = PersistentScheduledPIAEConsumer(
        coordinator,
        consumer,
    )

    result = await scheduled.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME,
    )

    assert result.ran is False
    assert result.scheduler.reason == "NOT_DUE"
    assert consumer.calls == 0


@pytest.mark.asyncio
async def test_due_cycle_persists_next_run() -> None:
    """A due cycle must persist the next scheduler deadline."""
    coordinator = make_coordinator(
        next_run_at=BASE_TIME,
    )
    consumer = FakeBoundedConsumer()

    await coordinator.initialize()

    scheduled = PersistentScheduledPIAEConsumer(
        coordinator,
        consumer,
    )

    result = await scheduled.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME,
    )

    assert result.ran is True
    assert consumer.calls == 1
    assert result.next_run_at == (
        BASE_TIME + timedelta(seconds=60)
    )
    assert coordinator.revision == 2


@pytest.mark.asyncio
async def test_initial_run_persists_followup_schedule() -> None:
    """INITIAL_RUN must create a durable subsequent deadline."""
    coordinator = make_coordinator(
        next_run_at=None,
    )
    consumer = FakeBoundedConsumer()

    await coordinator.initialize()

    scheduled = PersistentScheduledPIAEConsumer(
        coordinator,
        consumer,
    )

    result = await scheduled.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME,
    )

    assert result.scheduler.reason == "INITIAL_RUN"
    assert result.ran is True
    assert result.next_run_at == (
        BASE_TIME + timedelta(seconds=60)
    )


@pytest.mark.asyncio
async def test_paused_scheduler_blocks_consumption() -> None:
    """A persisted PAUSED scheduler must never run the consumer."""
    coordinator = make_coordinator(
        state=PersistentSchedulerState.PAUSED,
        next_run_at=None,
    )
    consumer = FakeBoundedConsumer()

    await coordinator.initialize()

    scheduled = PersistentScheduledPIAEConsumer(
        coordinator,
        consumer,
    )

    result = await scheduled.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME,
    )

    assert result.ran is False
    assert result.scheduler.state is SchedulerState.PAUSED
    assert result.scheduler.reason == "PAUSED"
    assert consumer.calls == 0


@pytest.mark.asyncio
async def test_consumer_failure_still_persists_next_run() -> None:
    """Infrastructure failure must advance the durable schedule."""
    coordinator = make_coordinator()
    consumer = RaisingBoundedConsumer()

    await coordinator.initialize()

    scheduled = PersistentScheduledPIAEConsumer(
        coordinator,
        consumer,
    )

    with pytest.raises(
        RuntimeError,
        match="intentional infrastructure failure",
    ):
        await scheduled.run_once(
            candidates_factory=lambda _opportunity: (),
            now=BASE_TIME,
        )

    assert consumer.calls == 1
    assert coordinator.scheduler.next_run_at == (
        BASE_TIME + timedelta(seconds=60)
    )
    assert coordinator.revision == 2


@pytest.mark.asyncio
async def test_naive_now_fails_closed() -> None:
    """Naive scheduler timestamps must be rejected."""
    coordinator = make_coordinator()
    consumer = FakeBoundedConsumer()

    await coordinator.initialize()

    scheduled = PersistentScheduledPIAEConsumer(
        coordinator,
        consumer,
    )

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        await scheduled.run_once(
            candidates_factory=lambda _opportunity: (),
            now=datetime(
                2026,
                8,
                31,
                12,
                0,
            ),
        )

    assert consumer.calls == 0


@pytest.mark.asyncio
async def test_persistence_conflict_does_not_invent_success() -> None:
    """A persistence conflict must propagate to the caller."""
    class ConflictStore(FakeSchedulerStore):
        async def transition(
            self,
            scheduler_id: str,
            *,
            expected_revision: int,
            state: PersistentSchedulerState,
            next_run_at: datetime | None,
        ) -> PersistentScheduler:
            """Reject the durable transition."""
            del scheduler_id
            del expected_revision
            del state
            del next_run_at

            raise PersistenceConflictError(
                "scheduler revision conflict",
            )

    coordinator = PersistentSchedulerCoordinator(
        ConflictStore(
            PersistentScheduler(
                scheduler_id="scheduler:001",
                state=PersistentSchedulerState.READY,
                next_run_at=None,
                revision=1,
            )
        ),
        scheduler_id="scheduler:001",
    )

    consumer = FakeBoundedConsumer()

    await coordinator.initialize()

    scheduled = PersistentScheduledPIAEConsumer(
        coordinator,
        consumer,
    )

    with pytest.raises(
        PersistenceConflictError,
        match="scheduler revision conflict",
    ):
        await scheduled.run_once(
            candidates_factory=lambda _opportunity: (),
            now=BASE_TIME,
        )
