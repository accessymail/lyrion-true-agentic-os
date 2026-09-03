"""Bounded observation loop for continuous proactive intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from lyrion.core.types import AutonomyLevel, TaskId
from lyrion.events.models import Event
from lyrion.execution.sandbox import SandboxConfig
from lyrion.integration.proactive_execution import CapabilityIntent
from lyrion.piae.continuous_runner import (
    ExecutionPlanFactory,
    PIAEContinuousRunner,
    ProactiveBatchResult,
)
from lyrion.piae.contracts import (
    DecisionCandidate,
    DecisionConstraints,
)
from lyrion.piae.opportunity_detector import OpportunityDetector
from lyrion.piae.opportunity_queue import OpportunityQueue
from lyrion.state.models import StateRecord


class EventSource(Protocol):
    """Provide a bounded sequence of observed events."""

    def poll(self, limit: int) -> tuple[Event, ...]:
        """Return at most ``limit`` currently available events."""


@dataclass(frozen=True)
class ObservationLoopConfig:
    """Explicit bounds for observation polling."""

    max_events_per_poll: int = 16

    def __post_init__(self) -> None:
        """Validate observation bounds."""
        if self.max_events_per_poll <= 0:
            raise ValueError(
                "max_events_per_poll must be greater than zero"
            )


@dataclass(frozen=True)
class ObservationPollResult:
    """Immutable result of one bounded observation poll."""

    events_seen: int
    cycle_result: ProactiveBatchResult

    @property
    def failed_count(self) -> int:
        """Return the number of cycle failures."""
        return self.cycle_result.failure_count

    @property
    def processed_count(self) -> int:
        """Return the number of processed events."""
        return self.cycle_result.processed_count


@dataclass(frozen=True)
class ObservationQueueResult:
    """Immutable result of observation-to-queue ingestion."""

    events_seen: int
    opportunities_detected: int
    opportunities_enqueued: int
    opportunity_ids: tuple[str, ...]
    rejected_indices: tuple[int, ...]

    @property
    def rejected_count(self) -> int:
        """Return the number of events whose opportunities were rejected."""
        return len(self.rejected_indices)


class PIAEObservationLoop:
    """Connect event observation to proactive intelligence."""

    def __init__(
        self,
        source: EventSource,
        runner: PIAEContinuousRunner,
        config: ObservationLoopConfig | None = None,
        *,
        detector: OpportunityDetector | None = None,
        opportunity_queue: OpportunityQueue | None = None,
    ) -> None:
        """Initialize the observation loop."""
        self._source = source
        self._runner = runner
        self._config = config or ObservationLoopConfig()
        self._detector = detector or OpportunityDetector()
        self._opportunity_queue = opportunity_queue

    @property
    def source(self) -> EventSource:
        """Return the configured event source."""
        return self._source

    @property
    def runner(self) -> PIAEContinuousRunner:
        """Return the bounded proactive runner."""
        return self._runner

    @property
    def config(self) -> ObservationLoopConfig:
        """Return observation-loop bounds."""
        return self._config

    @property
    def detector(self) -> OpportunityDetector:
        """Return the opportunity detector."""
        return self._detector

    @property
    def opportunity_queue(self) -> OpportunityQueue | None:
        """Return the configured opportunity queue."""
        return self._opportunity_queue

    def poll_once(
        self,
        *,
        candidates: tuple[DecisionCandidate, ...],
        intent: CapabilityIntent | None,
        plan_factory: ExecutionPlanFactory,
        sandbox: SandboxConfig | None,
        state_records: tuple[StateRecord, ...] = (),
        active_task_ids: tuple[TaskId, ...] = (),
        autonomy_level: AutonomyLevel | None = None,
        constraints: DecisionConstraints | None = None,
    ) -> ObservationPollResult:
        """Poll one bounded batch and process it through the legacy path."""
        events = self._source.poll(
            self._config.max_events_per_poll,
        )

        if len(events) > self._config.max_events_per_poll:
            raise ValueError(
                "event source exceeded max_events_per_poll"
            )

        cycle_result = self._runner.run_batch(
            events,
            candidates=candidates,
            intent=intent,
            plan_factory=plan_factory,
            sandbox=sandbox,
            state_records=state_records,
            active_task_ids=active_task_ids,
            autonomy_level=autonomy_level,
            constraints=constraints,
        )

        return ObservationPollResult(
            events_seen=len(events),
            cycle_result=cycle_result,
        )

    def observe_to_queue_once(
        self,
        *,
        now: datetime | None = None,
    ) -> ObservationQueueResult:
        """Poll observations, detect opportunities, and enqueue them."""
        if self._opportunity_queue is None:
            raise RuntimeError(
                "opportunity_queue is required for queue ingestion"
            )

        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        events = self._source.poll(
            self._config.max_events_per_poll,
        )

        if len(events) > self._config.max_events_per_poll:
            raise ValueError(
                "event source exceeded max_events_per_poll"
            )

        opportunity_ids: list[str] = []
        rejected_indices: list[int] = []
        opportunities_detected = 0
        opportunities_enqueued = 0

        for index, event in enumerate(events):
            opportunity = self._detector.detect(
                event,
                now=current_time,
            )

            if opportunity is None:
                continue

            opportunities_detected += 1

            if self._opportunity_queue.enqueue(
                opportunity,
                now=current_time,
            ):
                opportunities_enqueued += 1
                opportunity_ids.append(
                    str(opportunity.opportunity_id),
                )
            else:
                rejected_indices.append(index)

        return ObservationQueueResult(
            events_seen=len(events),
            opportunities_detected=opportunities_detected,
            opportunities_enqueued=opportunities_enqueued,
            opportunity_ids=tuple(opportunity_ids),
            rejected_indices=tuple(rejected_indices),
        )
