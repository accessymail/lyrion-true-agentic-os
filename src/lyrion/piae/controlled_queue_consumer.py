"""Bounded queue-consumption orchestration for PIAE."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, cast

from lyrion.piae.action_loop import PIAEActionCycleResult
from lyrion.piae.contracts import DecisionCandidate, Opportunity
from lyrion.piae.opportunity_binding import OpportunityContextFactory
from lyrion.piae.opportunity_queue import OpportunityQueue

CandidateFactory = Callable[
    [Opportunity],
    tuple[DecisionCandidate, ...],
]


class OpportunityConsumerProtocol(Protocol):
    """Synchronous consumer capability required by the normal cycle."""

    def consume_bound_once(
        self,
        *,
        context_factory: OpportunityContextFactory,
        candidates_factory: CandidateFactory,
        now: datetime | None = None,
    ) -> PIAEActionCycleResult | None:
        """Consume one opportunity synchronously."""


class PersistentOpportunityConsumerProtocol(Protocol):
    """Persistent consumer capability required by the durable cycle."""

    async def consume_bound_once_persistent(
        self,
        *,
        context_factory: OpportunityContextFactory,
        candidates_factory: CandidateFactory,
        worker_id: str,
        lease_id: str,
        now: datetime | None = None,
    ) -> PIAEActionCycleResult | None:
        """Consume one opportunity through durable execution."""


@dataclass(frozen=True)
class ControlledQueueConsumerConfig:
    """Explicit bounds for one controlled consumption cycle."""

    max_opportunities_per_cycle: int = 8

    def __post_init__(self) -> None:
        """Validate consumption bounds."""
        if self.max_opportunities_per_cycle <= 0:
            raise ValueError(
                "max_opportunities_per_cycle must be greater than zero"
            )


@dataclass(frozen=True)
class ControlledQueueItemResult:
    """Result of processing one queued opportunity."""

    opportunity_id: str
    result: PIAEActionCycleResult | None
    error_type: str | None = None
    error_message: str | None = None

    @property
    def succeeded(self) -> bool:
        """Return whether processing completed without an exception."""
        return self.error_type is None


@dataclass(frozen=True)
class ControlledQueueCycleResult:
    """Immutable result of one bounded queue-consumption cycle."""

    items: tuple[ControlledQueueItemResult, ...]
    stop_reason: str

    @property
    def attempted_count(self) -> int:
        """Return the number of opportunities attempted."""
        return len(self.items)

    @property
    def succeeded_count(self) -> int:
        """Return the number of successful opportunities."""
        return sum(
            item.succeeded
            for item in self.items
        )

    @property
    def failed_count(self) -> int:
        """Return the number of failed opportunities."""
        return sum(
            not item.succeeded
            for item in self.items
        )


class ControlledQueueConsumer:
    """Run a bounded, failure-isolated queue-consumption cycle."""

    def __init__(
        self,
        queue: OpportunityQueue,
        consumer: OpportunityConsumerProtocol,
        context_factory: OpportunityContextFactory,
        config: ControlledQueueConsumerConfig | None = None,
    ) -> None:
        """Initialize the controlled queue consumer."""
        self._queue = queue
        self._consumer = consumer
        self._context_factory = context_factory
        self._config = (
            config
            or ControlledQueueConsumerConfig()
        )

    @property
    def queue(self) -> OpportunityQueue:
        """Return the configured opportunity queue."""
        return self._queue

    @property
    def consumer(self) -> OpportunityConsumerProtocol:
        """Return the underlying opportunity consumer."""
        return self._consumer

    @property
    def context_factory(self) -> OpportunityContextFactory:
        """Return the per-opportunity context factory."""
        return self._context_factory

    @property
    def config(self) -> ControlledQueueConsumerConfig:
        """Return the configured consumption bounds."""
        return self._config


    async def run_once_persistent(
        self,
        *,
        candidates_factory: CandidateFactory,
        worker_id: str,
        lease_id_factory: Callable[[str], str],
        now: datetime | None = None,
    ) -> ControlledQueueCycleResult:
        """Consume a bounded cycle through durable execution persistence."""
        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        items: list[ControlledQueueItemResult] = []

        for _ in range(
            self._config.max_opportunities_per_cycle,
        ):
            opportunity = self._queue.peek(
                now=current_time,
            )

            if opportunity is None:
                return ControlledQueueCycleResult(
                    items=tuple(items),
                    stop_reason="QUEUE_EMPTY",
                )

            opportunity_id = str(
                opportunity.opportunity_id,
            )

            result = await cast(
                        PersistentOpportunityConsumerProtocol,
                        self._consumer,
                    ).consume_bound_once_persistent(
                context_factory=self._context_factory,
                candidates_factory=candidates_factory,
                worker_id=worker_id,
                lease_id=lease_id_factory(
                    opportunity_id,
                ),
                now=current_time,
            )

            items.append(
                ControlledQueueItemResult(
                    opportunity_id=opportunity_id,
                    result=result,
                )
            )
        return ControlledQueueCycleResult(
            items=tuple(items),
            stop_reason="MAX_OPPORTUNITIES_REACHED",
        )

    def run_once(
        self,
        *,
        candidates_factory: CandidateFactory,
        now: datetime | None = None,
    ) -> ControlledQueueCycleResult:
        """Consume at most the configured number of opportunities."""
        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        items: list[ControlledQueueItemResult] = []

        for _ in range(
            self._config.max_opportunities_per_cycle,
        ):
            opportunity = self._queue.peek(
                now=current_time,
            )

            if opportunity is None:
                return ControlledQueueCycleResult(
                    items=tuple(items),
                    stop_reason="QUEUE_EMPTY",
                )

            opportunity_id = str(
                opportunity.opportunity_id,
            )

            try:
                result = self._consumer.consume_bound_once(
                    context_factory=self._context_factory,
                    candidates_factory=candidates_factory,
                    now=current_time,
                )

                items.append(
                    ControlledQueueItemResult(
                        opportunity_id=opportunity_id,
                        result=result,
                    )
                )
            except Exception as exc:
                items.append(
                    ControlledQueueItemResult(
                        opportunity_id=opportunity_id,
                        result=None,
                        error_type=type(exc).__name__,
                        error_message=str(exc),
                    )
                )

        return ControlledQueueCycleResult(
            items=tuple(items),
            stop_reason="MAX_OPPORTUNITIES_REACHED",
        )
