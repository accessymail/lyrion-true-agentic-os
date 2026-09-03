"""Persistence-aware orchestration for the proactive scheduler."""

from __future__ import annotations

from datetime import UTC, datetime

from lyrion.persistence.contracts import (
    PersistentScheduler,
    PersistentSchedulerState,
)
from lyrion.persistence.protocols import SchedulerStore
from lyrion.piae.scheduler import (
    ControlledScheduler,
    ControlledSchedulerConfig,
    SchedulerDecision,
    SchedulerState,
)


class PersistentSchedulerCoordinator:
    """Coordinate scheduler behavior with durable scheduler state."""

    def __init__(
        self,
        store: SchedulerStore,
        *,
        scheduler_id: str,
        config: ControlledSchedulerConfig | None = None,
    ) -> None:
        """Initialize persistent scheduler orchestration."""
        normalized_id = scheduler_id.strip()

        if not normalized_id:
            raise ValueError(
                "scheduler_id must not be empty",
            )

        self._store = store
        self._scheduler_id = normalized_id
        self._config = config or ControlledSchedulerConfig()

        self._scheduler: ControlledScheduler | None = None
        self._revision: int | None = None

    @property
    def scheduler(self) -> ControlledScheduler:
        """Return the restored scheduler."""
        scheduler = self._scheduler

        if scheduler is None:
            raise RuntimeError(
                "persistent scheduler is not initialized",
            )

        return scheduler

    @property
    def revision(self) -> int:
        """Return the durable scheduler revision."""
        revision = self._revision

        if revision is None:
            raise RuntimeError(
                "persistent scheduler is not initialized",
            )

        return revision

    @property
    def scheduler_id(self) -> str:
        """Return the durable scheduler identifier."""
        return self._scheduler_id

    @property
    def config(self) -> ControlledSchedulerConfig:
        """Return the configured scheduler policy."""
        return self._config

    async def initialize(self) -> ControlledScheduler:
        """Load durable scheduler state or create initial state."""
        if self._scheduler is not None:
            raise RuntimeError(
                "persistent scheduler is already initialized",
            )

        persisted = await self._store.get(
            self._scheduler_id,
        )

        if persisted is None:
            persisted = PersistentScheduler(
                scheduler_id=self._scheduler_id,
                state=PersistentSchedulerState.READY,
                next_run_at=None,
                revision=1,
            )

            persisted = await self._store.save(
                persisted,
            )

        self._scheduler = ControlledScheduler.from_persisted_state(
            SchedulerState(persisted.state.value),
            persisted.next_run_at,
            config=self._config,
        )
        self._revision = persisted.revision

        return self._scheduler

    def evaluate(
        self,
        *,
        now: datetime | None = None,
    ) -> SchedulerDecision:
        """Evaluate the restored scheduler."""
        return self.scheduler.evaluate(
            now=now,
        )

    async def pause(self) -> PersistentScheduler:
        """Pause scheduling and persist the state transition."""
        scheduler = self.scheduler

        candidate = ControlledScheduler.from_persisted_state(
            SchedulerState.PAUSED,
            scheduler.next_run_at,
            config=self._config,
        )

        persisted = await self._store.transition(
            self._scheduler_id,
            expected_revision=self.revision,
            state=PersistentSchedulerState.PAUSED,
            next_run_at=candidate.next_run_at,
        )

        self._scheduler = candidate
        self._revision = persisted.revision

        return persisted

    async def resume(
        self,
        *,
        now: datetime | None = None,
    ) -> PersistentScheduler:
        """Resume scheduling and persist the immediate next-run time."""
        current_time = now or datetime.now(UTC)

        candidate = ControlledScheduler.from_persisted_state(
            SchedulerState.READY,
            current_time,
            config=self._config,
        )

        persisted = await self._store.transition(
            self._scheduler_id,
            expected_revision=self.revision,
            state=PersistentSchedulerState.READY,
            next_run_at=candidate.next_run_at,
        )

        self._scheduler = candidate
        self._revision = persisted.revision

        return persisted

    async def mark_cycle_completed(
        self,
        *,
        now: datetime | None = None,
    ) -> PersistentScheduler:
        """Advance the schedule and persist the new deadline."""
        current_time = now or datetime.now(UTC)

        scheduler = self.scheduler

        candidate = ControlledScheduler.from_persisted_state(
            scheduler.state,
            scheduler.next_run_at,
            config=self._config,
        )

        candidate.mark_cycle_completed(
            now=current_time,
        )

        persisted = await self._store.transition(
            self._scheduler_id,
            expected_revision=self.revision,
            state=PersistentSchedulerState(
                candidate.state.value,
            ),
            next_run_at=candidate.next_run_at,
        )

        self._scheduler = candidate
        self._revision = persisted.revision

        return persisted

