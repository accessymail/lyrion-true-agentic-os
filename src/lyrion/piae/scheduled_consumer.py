"""Externally stepped scheduler integration for bounded PIAE consumption."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from lyrion.piae.contracts import DecisionCandidate, Opportunity
from lyrion.piae.controlled_queue_consumer import (
    ControlledQueueConsumer,
    ControlledQueueCycleResult,
)
from lyrion.piae.scheduler import (
    ControlledScheduler,
    SchedulerDecision,
)

CandidateFactory = Callable[
    [Opportunity],
    tuple[DecisionCandidate, ...],
]


class BoundedConsumer(Protocol):
    """Consume one bounded queue cycle."""

    def run_once(
        self,
        *,
        candidates_factory: CandidateFactory,
        now: datetime | None = None,
    ) -> ControlledQueueCycleResult:
        """Run one bounded consumption cycle."""


@dataclass(frozen=True)
class ScheduledConsumptionResult:
    """Immutable result of one externally stepped scheduler invocation."""

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


class ScheduledPIAEConsumer:
    """Gate bounded PIAE consumption through the controlled scheduler."""

    def __init__(
        self,
        scheduler: ControlledScheduler,
        consumer: BoundedConsumer,
    ) -> None:
        """Initialize scheduler-controlled consumption."""
        self._scheduler = scheduler
        self._consumer = consumer

    @property
    def scheduler(self) -> ControlledScheduler:
        """Return the scheduler."""
        return self._scheduler

    @property
    def consumer(self) -> BoundedConsumer:
        """Return the bounded consumer."""
        return self._consumer

    def run_once(
        self,
        *,
        candidates_factory: CandidateFactory,
        now: datetime | None = None,
    ) -> ScheduledConsumptionResult:
        """Run one scheduled, externally stepped consumption attempt."""
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
            return ScheduledConsumptionResult(
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
            # Advance the schedule before propagating infrastructure
            # failures so an external caller cannot create an implicit
            # tight retry loop by invoking the scheduler again immediately.
            self._scheduler.mark_cycle_completed(
                now=current_time,
            )
            raise

        next_run_at = self._scheduler.mark_cycle_completed(
            now=current_time,
        )

        return ScheduledConsumptionResult(
            scheduler=decision,
            cycle=cycle,
            next_run_at=next_run_at,
        )


def as_controlled_consumer(
    consumer: ControlledQueueConsumer,
) -> BoundedConsumer:
    """Expose the production consumer through its bounded protocol."""
    return consumer
