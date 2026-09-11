"""Persistence-aware orchestration for scheduled PIAE consumption."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lyrion.integration.persistent_scheduler import (
    PersistentSchedulerCoordinator,
)
from lyrion.persistence.execution_runner import (
    PersistentExecutionRunner,
)
from lyrion.persistence.sqlalchemy.uow import (
    SQLAlchemyPersistenceUnitOfWork,
)
from lyrion.piae.action_loop import PIAEActionLoop
from lyrion.piae.controlled_queue_consumer import (
    ControlledQueueConsumer,
    ControlledQueueCycleResult,
)
from lyrion.piae.opportunity_consumer import (
    OpportunityConsumer,
)
from lyrion.piae.scheduled_consumer import CandidateFactory
from lyrion.piae.scheduler import SchedulerDecision


class BoundedConsumer(Protocol):
    """Consume one bounded queue cycle."""

    def run_once(
        self,
        *,
        candidates_factory: CandidateFactory,
        now: datetime | None = None,
    ) -> ControlledQueueCycleResult:
        """Run one bounded consumption cycle."""


class PersistentBoundedConsumer(Protocol):
    """Consume one bounded queue cycle through durable execution."""

    async def run_once_persistent(
        self,
        *,
        candidates_factory: CandidateFactory,
        worker_id: str,
        lease_id_factory: Callable[[str], str],
        now: datetime | None = None,
    ) -> ControlledQueueCycleResult:
        """Run one bounded persistent consumption cycle."""


PersistenceUnitOfWorkFactory = Callable[
    [],
    SQLAlchemyPersistenceUnitOfWork,
]


@dataclass(frozen=True)
class PersistentScheduledConsumptionResult:
    """Immutable result of one persistent scheduled invocation."""

    scheduler: SchedulerDecision
    cycle: ControlledQueueCycleResult | None
    next_run_at: datetime | None

    @property
    def ran(self) -> bool:
        """Return whether queue consumption actually ran."""
        return self.cycle is not None

    @property
    def attempted_count(self) -> int:
        """Return the number of consumed opportunities."""
        if self.cycle is None:
            return 0

        return self.cycle.attempted_count

    @property
    def failed_count(self) -> int:
        """Return the number of failed opportunities."""
        if self.cycle is None:
            return 0

        return self.cycle.failed_count


class PersistentScheduledPIAEConsumer:
    """Run bounded PIAE consumption with durable scheduling state."""

    def __init__(
        self,
        scheduler: PersistentSchedulerCoordinator,
        consumer: BoundedConsumer,
    ) -> None:
        """Initialize persistent scheduled consumption."""
        self._scheduler = scheduler
        self._consumer = consumer

    @property
    def scheduler(self) -> PersistentSchedulerCoordinator:
        """Return the persistent scheduler coordinator."""
        return self._scheduler

    @property
    def consumer(self) -> BoundedConsumer:
        """Return the bounded consumer."""
        return self._consumer

    async def run_once(
        self,
        *,
        candidates_factory: CandidateFactory,
        now: datetime | None = None,
    ) -> PersistentScheduledConsumptionResult:
        """Run one persistence-aware scheduled consumption attempt."""
        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        decision = self._scheduler.evaluate(
            now=current_time,
        )

        if not decision.due:
            return PersistentScheduledConsumptionResult(
                scheduler=decision,
                cycle=None,
                next_run_at=decision.next_run_at,
            )

        try:
            cycle = self._consumer.run_once(
                candidates_factory=candidates_factory,
                now=current_time,
            )
        except Exception:
            await self._scheduler.mark_cycle_completed(
                now=current_time,
            )
            raise

        persisted = await self._scheduler.mark_cycle_completed(
            now=current_time,
        )

        return PersistentScheduledConsumptionResult(
            scheduler=decision,
            cycle=cycle,
            next_run_at=persisted.next_run_at,
        )

    async def run_once_persistent(
        self,
        *,
        candidates_factory: CandidateFactory,
        worker_id: str,
        now: datetime | None = None,
        uow_factory: PersistenceUnitOfWorkFactory,
        lease_id_factory: Callable[[str], str],
    ) -> PersistentScheduledConsumptionResult:
        """Run one scheduled cycle inside one durable transaction."""
        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        async with uow_factory() as uow:
            coordinator = PersistentSchedulerCoordinator(
                uow.scheduler,
                scheduler_id=self._scheduler.scheduler_id,
                config=self._scheduler.config,
            )

            await coordinator.initialize()

            decision = coordinator.evaluate(
                now=current_time,
            )

            if not decision.due:
                return PersistentScheduledConsumptionResult(
                    scheduler=decision,
                    cycle=None,
                    next_run_at=decision.next_run_at,
                )

            existing_consumer = self._consumer

            if not isinstance(existing_consumer, ControlledQueueConsumer):
                raise TypeError(
                    "persistent scheduling requires "
                    "ControlledQueueConsumer"
                )

            opportunity_consumer = existing_consumer.consumer

            action_loop = getattr(
                opportunity_consumer,
                "action_loop",
                None,
            )

            if not isinstance(action_loop, PIAEActionLoop):
                raise TypeError(
                    "persistent scheduling requires "
                    "OpportunityConsumer backed by PIAEActionLoop"
                )

            runner = PersistentExecutionRunner.from_stores(
                action_loop.coordinator,
                execution_store=uow.executions,
                lease_store=uow.leases,
            )

            persistent_action_loop = PIAEActionLoop(
                action_loop.coordinator,
                persistent_runner=runner,
            )

            persistent_opportunity_consumer = OpportunityConsumer(
                existing_consumer.queue,
                persistent_action_loop,
            )

            persistent_consumer = ControlledQueueConsumer(
                existing_consumer.queue,
                persistent_opportunity_consumer,
                existing_consumer.context_factory,
                existing_consumer.config,
            )

            cycle = await persistent_consumer.run_once_persistent(
                candidates_factory=candidates_factory,
                worker_id=worker_id,
                lease_id_factory=lease_id_factory,
                now=current_time,
            )

            persisted = await coordinator.mark_cycle_completed(
                now=current_time,
            )

            return PersistentScheduledConsumptionResult(
                scheduler=decision,
                cycle=cycle,
                next_run_at=persisted.next_run_at,
            )


def sqlalchemy_uow_factory(
    session_factory: async_sessionmaker[AsyncSession],
) -> SQLAlchemyPersistenceUnitOfWork:
    """Create one SQLAlchemy persistence unit of work."""
    return SQLAlchemyPersistenceUnitOfWork(
        session_factory,
    )
