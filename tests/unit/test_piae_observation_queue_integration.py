"""Adversarial tests for observation-to-opportunity-queue integration."""

from datetime import UTC, datetime, timedelta

import pytest

from lyrion.capabilities.gateway import CapabilityGateway
from lyrion.core.types import (
    CorrelationId,
    EventId,
    IdempotencyKey,
    OpportunityId,
)
from lyrion.events.models import (
    Event,
    EventSensitivity,
    EventTrustLevel,
)
from lyrion.execution.executor import SecureExecutor
from lyrion.integration.proactive_execution import (
    ProactiveExecutionCoordinator,
)
from lyrion.piae.action_loop import PIAEActionLoop
from lyrion.piae.continuous_runner import PIAEContinuousRunner
from lyrion.piae.engine import PIAEDecisionEngine
from lyrion.piae.observation_loop import (
    EventSource,
    ObservationLoopConfig,
    PIAEObservationLoop,
)
from lyrion.piae.opportunity_detector import OpportunityDetector
from lyrion.piae.opportunity_queue import (
    OpportunityQueue,
    OpportunityQueueConfig,
)
from lyrion.piae.proactive_cycle import PIAEProactiveCycle
from lyrion.security.authorization import AegisAuthorizationService
from lyrion.security.guards import AuthorizationGuard
from lyrion.security.policy import AegisPolicyEvaluator
from lyrion.security.replay import ReplayGuard
from lyrion.security.rules import default_aegis_policy


class FakeEventSource:
    """Deterministic bounded event source."""

    def __init__(
        self,
        events: tuple[Event, ...],
    ) -> None:
        self.events = events
        self.poll_calls: list[int] = []

    def poll(
        self,
        limit: int,
    ) -> tuple[Event, ...]:
        """Return at most the requested number of events."""
        self.poll_calls.append(limit)
        return self.events[:limit]


class OverflowEventSource:
    """Invalid source that violates its polling contract."""

    def __init__(
        self,
        events: tuple[Event, ...],
    ) -> None:
        self.events = events

    def poll(
        self,
        limit: int,
    ) -> tuple[Event, ...]:
        """Return more events than requested."""
        del limit
        return self.events


def make_event(
    event_id: str,
    *,
    creates_opportunity: bool = True,
    now: datetime | None = None,
) -> Event:
    """Create a deterministic test event."""
    current_time = now or datetime.now(UTC)

    payload: dict[str, object] = {}

    if creates_opportunity:
        payload = {
            "creates_opportunity": True,
            "opportunity_title": f"Opportunity {event_id}",
            "opportunity_description": "Queue integration test.",
            "user_relevance": 0.90,
            "expected_benefit": 0.90,
            "interruption_cost": 0.10,
            "risk_score": 0.10,
            "reversibility": 0.90,
            "urgency": 0.70,
            "confidence": 0.95,
            "required_capabilities": (
                "development.prepare",
            ),
            "required_autonomy_level": "L1",
        }

    return Event(
        event_id=EventId(event_id),
        event_type="observation.test",
        source="queue-integration-test",
        timestamp=current_time,
        observed_at=current_time,
        payload=payload,
        sensitivity=EventSensitivity.INTERNAL,
        provenance="queue-integration-test",
        trust_level=EventTrustLevel.SYSTEM,
        correlation_id=CorrelationId(
            f"corr:{event_id}",
        ),
        idempotency_key=IdempotencyKey(
            f"idem:{event_id}",
        ),
    )


def make_action_loop() -> PIAEActionLoop:
    """Create the minimum secure action-loop dependency."""
    policy = default_aegis_policy()

    gateway = CapabilityGateway(
        AegisAuthorizationService(
            AegisPolicyEvaluator(policy),
            AuthorizationGuard(policy.policy_version),
            ReplayGuard(),
        )
    )

    coordinator = ProactiveExecutionCoordinator(
        piae=PIAEDecisionEngine(),
        gateway=gateway,
        executor=SecureExecutor(),
    )

    return PIAEActionLoop(coordinator)


def make_loop(
    source: EventSource,
    queue: OpportunityQueue | None,
    config: ObservationLoopConfig | None = None,
) -> PIAEObservationLoop:
    """Create an observation loop for queue integration tests."""
    cycle = PIAEProactiveCycle(
        OpportunityDetector(),
        make_action_loop(),
    )

    runner = PIAEContinuousRunner(
        cycle,
    )

    return PIAEObservationLoop(
        source,
        runner,
        config,
        detector=OpportunityDetector(),
        opportunity_queue=queue,
    )


def test_observation_enqueues_detected_opportunities() -> None:
    """Qualifying observations should become queued opportunities."""
    now = datetime.now(UTC)

    source = FakeEventSource(
        (
            make_event(
                "evt_queue_1",
                now=now,
            ),
            make_event(
                "evt_queue_2",
                now=now,
            ),
        )
    )

    queue = OpportunityQueue()

    result = make_loop(
        source,
        queue,
    ).observe_to_queue_once(
        now=now,
    )

    assert result.events_seen == 2
    assert result.opportunities_detected == 2
    assert result.opportunities_enqueued == 2
    assert result.rejected_indices == ()

    snapshot = queue.snapshot(
        now=now,
    )

    assert len(snapshot) == 2
    assert {
        item.opportunity_id
        for item in snapshot
    } == {
        OpportunityId(
            "opportunity:evt_queue_1",
        ),
        OpportunityId(
            "opportunity:evt_queue_2",
        ),
    }


def test_non_opportunity_events_are_not_queued() -> None:
    """Ordinary observations must not create queue entries."""
    now = datetime.now(UTC)

    source = FakeEventSource(
        (
            make_event(
                "evt_ordinary",
                creates_opportunity=False,
                now=now,
            ),
        )
    )

    queue = OpportunityQueue()

    result = make_loop(
        source,
        queue,
    ).observe_to_queue_once(
        now=now,
    )

    assert result.events_seen == 1
    assert result.opportunities_detected == 0
    assert result.opportunities_enqueued == 0
    assert queue.size(now=now) == 0


def test_duplicate_opportunities_are_rejected() -> None:
    """Repeated observations must not duplicate queue entries."""
    now = datetime.now(UTC)

    event = make_event(
        "evt_duplicate",
        now=now,
    )

    source = FakeEventSource(
        (event,),
    )

    queue = OpportunityQueue()

    loop = make_loop(
        source,
        queue,
    )

    first = loop.observe_to_queue_once(
        now=now,
    )
    second = loop.observe_to_queue_once(
        now=now,
    )

    assert first.opportunities_enqueued == 1
    assert second.opportunities_detected == 1
    assert second.opportunities_enqueued == 0
    assert second.rejected_indices == (0,)
    assert queue.size(now=now) == 1


def test_queue_capacity_is_respected() -> None:
    """Observation ingestion must respect queue capacity."""
    now = datetime.now(UTC)

    source = FakeEventSource(
        (
            make_event(
                "evt_capacity_1",
                now=now,
            ),
            make_event(
                "evt_capacity_2",
                now=now,
            ),
        )
    )

    queue = OpportunityQueue(
        OpportunityQueueConfig(
            max_size=1,
        ),
    )

    result = make_loop(
        source,
        queue,
    ).observe_to_queue_once(
        now=now,
    )

    assert result.opportunities_detected == 2
    assert result.opportunities_enqueued == 1
    assert result.rejected_indices == (1,)
    assert queue.size(now=now) == 1


def test_source_bound_is_enforced() -> None:
    """A source returning too many events must fail closed."""
    now = datetime.now(UTC)

    events = (
        make_event(
            "evt_overflow_1",
            now=now,
        ),
        make_event(
            "evt_overflow_2",
            now=now,
        ),
    )

    source = OverflowEventSource(
        events,
    )

    queue = OpportunityQueue()

    loop = make_loop(
        source,
        queue,
        ObservationLoopConfig(
            max_events_per_poll=1,
        ),
    )

    with pytest.raises(
        ValueError,
        match="exceeded max_events_per_poll",
    ):
        loop.observe_to_queue_once(
            now=now,
        )

    assert queue.size(now=now) == 0


def test_naive_time_is_rejected() -> None:
    """Observation ingestion requires timezone-aware time."""
    source = FakeEventSource(
        (
            make_event(
                "evt_naive",
            ),
        )
    )

    queue = OpportunityQueue()

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        make_loop(
            source,
            queue,
        ).observe_to_queue_once(
            now=datetime.now(),
        )


def test_missing_queue_is_rejected() -> None:
    """Queue ingestion cannot run without a queue."""
    source = FakeEventSource(
        (
            make_event(
                "evt_no_queue",
            ),
        )
    )

    loop = make_loop(
        source,
        None,
    )

    with pytest.raises(
        RuntimeError,
        match="opportunity_queue is required",
    ):
        loop.observe_to_queue_once()


def test_configured_poll_bound_reaches_source() -> None:
    """Configured polling limits must reach the source."""
    now = datetime.now(UTC)

    source = FakeEventSource(
        (
            make_event(
                "evt_limit_1",
                now=now,
            ),
            make_event(
                "evt_limit_2",
                now=now,
            ),
        )
    )

    queue = OpportunityQueue()

    result = make_loop(
        source,
        queue,
        ObservationLoopConfig(
            max_events_per_poll=1,
        ),
    ).observe_to_queue_once(
        now=now,
    )

    assert result.events_seen == 1
    assert source.poll_calls == [1]


def test_expired_opportunity_is_rejected_by_queue() -> None:
    """Expired detected opportunities must not enter the queue."""
    now = datetime.now(UTC)
    event_time = now - timedelta(seconds=2)

    event = make_event(
        "evt_expired",
        now=event_time,
    )

    event = event.model_copy(
        update={
            "payload": {
                **event.payload,
                "opportunity_expires_at": (
                    now - timedelta(seconds=1)
                ),
            },
        },
    )

    source = FakeEventSource(
        (event,),
    )

    queue = OpportunityQueue()

    result = make_loop(
        source,
        queue,
    ).observe_to_queue_once(
        now=now,
    )

    assert result.opportunities_detected == 1
    assert result.opportunities_enqueued == 0
    assert result.rejected_indices == (0,)
    assert queue.size(now=now) == 0
