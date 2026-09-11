"""Adversarial tests for bounded PIAE queue consumption."""

from datetime import UTC, datetime

import pytest

from lyrion.core.types import (
    EventId,
    OpportunityId,
)
from lyrion.piae.action_loop import PIAEActionCycleResult
from lyrion.piae.contracts import (
    Opportunity,
)
from lyrion.piae.controlled_queue_consumer import (
    CandidateFactory,
    ControlledQueueConsumer,
    ControlledQueueConsumerConfig,
    OpportunityConsumerProtocol,
)
from lyrion.piae.opportunity_binding import (
    OpportunityContext,
    OpportunityContextFactory,
)
from lyrion.piae.opportunity_queue import OpportunityQueue


class FakeOpportunityConsumer(OpportunityConsumerProtocol):
    """Minimal consumer double for orchestration tests."""

    def __init__(
        self,
        queue: OpportunityQueue,
        results: list[PIAEActionCycleResult | None]
        | None = None,
        errors: list[Exception] | None = None,
    ) -> None:
        self._queue = queue
        self._results = results or []
        self._errors = errors or []

    def consume_bound_once(
        self,
        *,
        context_factory: OpportunityContextFactory,
        candidates_factory: CandidateFactory,
        now: datetime | None = None,
    ) -> PIAEActionCycleResult | None:
        """Consume exactly one item from the queue."""
        del context_factory
        del candidates_factory

        opportunity = self._queue.dequeue(
            now=now,
        )

        if opportunity is None:
            return None

        if self._errors:
            error = self._errors.pop(0)
            raise error

        if self._results:
            return self._results.pop(0)

        return None


class FakeContextFactory:
    """Minimal context factory double."""

    def build(
        self,
        opportunity: Opportunity,
        *,
        now: datetime,
    ) -> OpportunityContext:
        """Fail if orchestration incorrectly invokes the fake directly."""
        del opportunity
        del now

        raise AssertionError(
            "context factory should be owned by the real consumer"
        )


def make_controller(
    queue: OpportunityQueue,
    *,
    config: ControlledQueueConsumerConfig | None = None,
    results: list[PIAEActionCycleResult | None] | None = None,
    errors: list[Exception] | None = None,
) -> ControlledQueueConsumer:
    """Create a controlled consumer around a consumer double."""
    fake_consumer = FakeOpportunityConsumer(
        queue,
        results=results,
        errors=errors,
    )

    return ControlledQueueConsumer(
        queue,
        fake_consumer,
        FakeContextFactory(),
        config,
    )


def test_config_requires_positive_bound() -> None:
    """A controlled cycle must have a positive bound."""
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        ControlledQueueConsumerConfig(
            max_opportunities_per_cycle=0,
        )


def test_negative_bound_is_rejected() -> None:
    """Negative cycle bounds are invalid."""
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        ControlledQueueConsumerConfig(
            max_opportunities_per_cycle=-1,
        )


def test_empty_queue_stops_cleanly() -> None:
    """An empty queue should terminate immediately."""
    queue = OpportunityQueue()

    result = make_controller(
        queue,
    ).run_once(
        candidates_factory=lambda _opportunity: (),
    )

    assert result.items == ()
    assert result.stop_reason == "QUEUE_EMPTY"
    assert result.attempted_count == 0


def test_maximum_opportunity_bound_is_explicit() -> None:
    """The configured cycle bound must be retained."""
    queue = OpportunityQueue()

    config = ControlledQueueConsumerConfig(
        max_opportunities_per_cycle=3,
    )

    controller = make_controller(
        queue,
        config=config,
    )

    assert controller.config.max_opportunities_per_cycle == 3


def test_timezone_aware_time_is_required() -> None:
    """Naive timestamps must fail closed."""
    queue = OpportunityQueue()

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        make_controller(
            queue,
        ).run_once(
            candidates_factory=lambda _opportunity: (),
            now=datetime.now(),
        )


def test_failure_isolated_without_second_dequeue() -> None:
    """A fake consumer failure must not trigger another dequeue."""
    queue = OpportunityQueue()

    result = make_controller(
        queue,
        errors=[RuntimeError("controlled failure")],
    ).run_once(
        candidates_factory=lambda _opportunity: (),
    )

    assert result.attempted_count == 0
    assert result.stop_reason == "QUEUE_EMPTY"


def test_cycle_result_counts_are_consistent() -> None:
    """Result counters must remain internally consistent."""
    queue = OpportunityQueue()

    result = make_controller(
        queue,
    ).run_once(
        candidates_factory=lambda _opportunity: (),
    )

    assert (
        result.succeeded_count
        + result.failed_count
        == result.attempted_count
    )


def test_default_cycle_is_explicitly_bounded() -> None:
    """The default cycle limit must never be unbounded."""
    config = ControlledQueueConsumerConfig()

    assert config.max_opportunities_per_cycle == 8


def test_cycle_can_be_reused() -> None:
    """A completed bounded cycle remains reusable."""
    queue = OpportunityQueue()

    controller = make_controller(
        queue,
    )

    first = controller.run_once(
        candidates_factory=lambda _opportunity: (),
    )
    second = controller.run_once(
        candidates_factory=lambda _opportunity: (),
    )

    assert first.stop_reason == "QUEUE_EMPTY"
    assert second.stop_reason == "QUEUE_EMPTY"


@pytest.mark.asyncio
async def test_persistent_cycle_propagates_execution_failure() -> None:
    """Persistent execution failures must escape the bounded cycle."""
    now = datetime.now(UTC)

    opportunity = Opportunity(
        opportunity_id=OpportunityId("opp_persistent_failure"),
        trigger_event_ids=(EventId("event:persistent_failure"),),
        title="Persistent execution failure",
        description="Exercise persistent failure propagation.",
        user_relevance=0.9,
        expected_benefit=0.9,
        interruption_cost=0.1,
        risk_score=0.1,
        reversibility=0.9,
        urgency=0.9,
        confidence=0.95,
        created_at=now,
    )

    queue = OpportunityQueue()

    assert queue.enqueue(
        opportunity,
        now=now,
    ) is True

    class RaisingPersistentConsumer(OpportunityConsumerProtocol):
        """Consumer double that raises during persistent execution."""

        def consume_bound_once(
            self,
            *,
            context_factory: OpportunityContextFactory,
            candidates_factory: CandidateFactory,
            now: datetime | None = None,
        ) -> PIAEActionCycleResult | None:
            """Satisfy the normal consumer capability."""
            del context_factory
            del candidates_factory
            del now

            raise NotImplementedError(
                "synchronous path is not used by this test"
            )

        async def consume_bound_once_persistent(
            self,
            *,
            context_factory: OpportunityContextFactory,
            candidates_factory: CandidateFactory,
            worker_id: str,
            lease_id: str,
            now: datetime | None = None,
        ) -> PIAEActionCycleResult | None:
            """Raise a deterministic persistent execution failure."""
            del context_factory
            del candidates_factory
            del worker_id
            del lease_id
            del now

            raise RuntimeError(
                "persistent execution failure",
            )

    controlled = ControlledQueueConsumer(
        queue,
        RaisingPersistentConsumer(),
        FakeContextFactory(),
        ControlledQueueConsumerConfig(
            max_opportunities_per_cycle=1,
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="persistent execution failure",
    ):
        await controlled.run_once_persistent(
            candidates_factory=lambda _opportunity: (),
            worker_id="worker:persistent",
            lease_id_factory=lambda opportunity_id: (
                f"lease:{opportunity_id}"
            ),
            now=now,
        )
