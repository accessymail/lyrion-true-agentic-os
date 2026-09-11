"""Adversarial tests for the bounded PIAE opportunity queue."""

from datetime import UTC, datetime, timedelta
from threading import Thread

import pytest

from lyrion.core.types import (
    AutonomyLevel,
    CorrelationId,
    EventId,
    OpportunityId,
)
from lyrion.events.models import EventSensitivity, EventTrustLevel
from lyrion.piae.contracts import (
    Opportunity,
    OpportunityStatus,
)
from lyrion.piae.opportunity_queue import (
    OpportunityQueue,
    OpportunityQueueConfig,
)


def make_opportunity(
    opportunity_id: str,
    *,
    now: datetime | None = None,
    urgency: float = 0.5,
    benefit: float = 0.5,
    interruption_cost: float = 0.2,
    risk: float = 0.1,
    status: OpportunityStatus = OpportunityStatus.OPEN,
    expires_at: datetime | None = None,
) -> Opportunity:
    """Create a valid opportunity for queue tests."""
    current_time = now or datetime.now(UTC)

    return Opportunity(
        opportunity_id=OpportunityId(
            opportunity_id,
        ),
        correlation_id=CorrelationId(
            f"corr:{opportunity_id}",
        ),
        trigger_event_ids=(
            EventId(
                f"event:{opportunity_id}",
            ),
        ),
        relevant_state_ids=(),
        goal_context=(),
        title=f"Opportunity {opportunity_id}",
        description="Queue test opportunity.",
        user_relevance=0.8,
        expected_benefit=benefit,
        interruption_cost=interruption_cost,
        risk_score=risk,
        reversibility=0.9,
        urgency=urgency,
        confidence=0.9,
        required_capabilities=(),
        required_autonomy_level=AutonomyLevel.L0,
        sensitivity=EventSensitivity.INTERNAL,
        trust_level=EventTrustLevel.SYSTEM,
        status=status,
        created_at=current_time,
        expires_at=expires_at,
    )


def test_enqueue_and_dequeue() -> None:
    """A valid opportunity should enter and leave the queue."""
    now = datetime.now(UTC)
    queue = OpportunityQueue()

    opportunity = make_opportunity(
        "opp_basic",
        now=now,
    )

    assert queue.enqueue(
        opportunity,
        now=now,
    ) is True
    assert queue.size(now=now) == 1
    assert queue.contains(
        opportunity.opportunity_id,
        now=now,
    )

    selected = queue.dequeue(
        now=now,
    )

    assert selected == opportunity
    assert queue.size(now=now) == 0


def test_peek_does_not_remove() -> None:
    """Peek must preserve queue contents."""
    now = datetime.now(UTC)
    queue = OpportunityQueue()

    opportunity = make_opportunity(
        "opp_peek",
        now=now,
    )

    queue.enqueue(
        opportunity,
        now=now,
    )

    assert queue.peek(now=now) == opportunity
    assert queue.size(now=now) == 1


def test_priority_ordering_is_deterministic() -> None:
    """Higher urgency should be selected first."""
    now = datetime.now(UTC)

    queue = OpportunityQueue()

    low = make_opportunity(
        "opp_low",
        now=now,
        urgency=0.20,
        benefit=0.90,
    )

    high = make_opportunity(
        "opp_high",
        now=now,
        urgency=0.90,
        benefit=0.20,
    )

    queue.enqueue(low, now=now)
    queue.enqueue(high, now=now)

    assert queue.dequeue(now=now) == high
    assert queue.dequeue(now=now) == low


def test_benefit_breaks_urgency_tie() -> None:
    """Expected benefit should break equal urgency."""
    now = datetime.now(UTC)

    queue = OpportunityQueue()

    first = make_opportunity(
        "opp_benefit_low",
        now=now,
        urgency=0.7,
        benefit=0.4,
    )

    second = make_opportunity(
        "opp_benefit_high",
        now=now,
        urgency=0.7,
        benefit=0.9,
    )

    queue.enqueue(first, now=now)
    queue.enqueue(second, now=now)

    assert queue.dequeue(now=now) == second


def test_interruption_cost_breaks_benefit_tie() -> None:
    """Lower interruption cost should win an otherwise equal priority."""
    now = datetime.now(UTC)

    queue = OpportunityQueue()

    expensive = make_opportunity(
        "opp_interrupt_high",
        now=now,
        urgency=0.8,
        benefit=0.8,
        interruption_cost=0.8,
    )

    cheap = make_opportunity(
        "opp_interrupt_low",
        now=now,
        urgency=0.8,
        benefit=0.8,
        interruption_cost=0.1,
    )

    queue.enqueue(expensive, now=now)
    queue.enqueue(cheap, now=now)

    assert queue.dequeue(now=now) == cheap


def test_risk_breaks_remaining_tie() -> None:
    """Lower risk should win when earlier priorities are equal."""
    now = datetime.now(UTC)

    queue = OpportunityQueue()

    risky = make_opportunity(
        "opp_risky",
        now=now,
        urgency=0.8,
        benefit=0.8,
        interruption_cost=0.2,
        risk=0.8,
    )

    safe = make_opportunity(
        "opp_safe",
        now=now,
        urgency=0.8,
        benefit=0.8,
        interruption_cost=0.2,
        risk=0.1,
    )

    queue.enqueue(risky, now=now)
    queue.enqueue(safe, now=now)

    assert queue.dequeue(now=now) == safe


def test_creation_time_breaks_priority_tie() -> None:
    """Older opportunities should win the remaining tie."""
    now = datetime.now(UTC)

    queue = OpportunityQueue()

    older = make_opportunity(
        "opp_older",
        now=now,
        urgency=0.5,
    )

    newer = make_opportunity(
        "opp_newer",
        now=now + timedelta(seconds=1),
        urgency=0.5,
    )

    queue.enqueue(newer, now=now)
    queue.enqueue(older, now=now)

    assert queue.dequeue(now=now) == older


def test_opportunity_id_is_final_tie_breaker() -> None:
    """Identical priorities must have deterministic ID ordering."""
    now = datetime.now(UTC)

    queue = OpportunityQueue()

    first = make_opportunity(
        "opp_a",
        now=now,
    )

    second = make_opportunity(
        "opp_b",
        now=now,
    )

    queue.enqueue(second, now=now)
    queue.enqueue(first, now=now)

    assert queue.dequeue(now=now) == first
    assert queue.dequeue(now=now) == second


def test_duplicate_opportunity_is_rejected() -> None:
    """Duplicate opportunity IDs must not consume capacity."""
    now = datetime.now(UTC)
    queue = OpportunityQueue()

    opportunity = make_opportunity(
        "opp_duplicate",
        now=now,
    )

    assert queue.enqueue(opportunity, now=now) is True
    assert queue.enqueue(opportunity, now=now) is False
    assert queue.size(now=now) == 1


def test_capacity_is_bounded() -> None:
    """The queue must reject opportunities beyond configured capacity."""
    now = datetime.now(UTC)

    queue = OpportunityQueue(
        OpportunityQueueConfig(
            max_size=2,
        ),
    )

    assert queue.enqueue(
        make_opportunity("opp_1", now=now),
        now=now,
    )
    assert queue.enqueue(
        make_opportunity("opp_2", now=now),
        now=now,
    )
    assert queue.enqueue(
        make_opportunity("opp_3", now=now),
        now=now,
    ) is False

    assert queue.size(now=now) == 2


def test_zero_capacity_is_rejected() -> None:
    """Zero capacity is invalid."""
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        OpportunityQueueConfig(
            max_size=0,
        )


def test_negative_capacity_is_rejected() -> None:
    """Negative capacity is invalid."""
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        OpportunityQueueConfig(
            max_size=-1,
        )


def test_expired_opportunity_is_not_enqueued() -> None:
    """Expired opportunities must be rejected."""
    now = datetime.now(UTC)

    opportunity = make_opportunity(
        "opp_expired",
        now=now,
        expires_at=now,
    )

    queue = OpportunityQueue()

    assert queue.enqueue(
        opportunity,
        now=now,
    ) is False
    assert queue.size(now=now) == 0


def test_expired_queued_opportunity_is_removed() -> None:
    """Queued opportunities should disappear after expiry."""
    created = datetime.now(UTC)
    expiry = created + timedelta(seconds=1)

    queue = OpportunityQueue()

    opportunity = make_opportunity(
        "opp_expiring",
        now=created,
        expires_at=expiry,
    )

    assert queue.enqueue(
        opportunity,
        now=created,
    )

    assert queue.size(
        now=created + timedelta(seconds=2),
    ) == 0

    assert queue.peek(
        now=created + timedelta(seconds=2),
    ) is None


@pytest.mark.parametrize(
    "status",
    [
        OpportunityStatus.SUPPRESSED,
        OpportunityStatus.EXPIRED,
        OpportunityStatus.SELECTED,
        OpportunityStatus.DISMISSED,
    ],
)
def test_non_open_status_is_rejected(
    status: OpportunityStatus,
) -> None:
    """Only OPEN opportunities may enter the queue."""
    now = datetime.now(UTC)

    opportunity = make_opportunity(
        f"opp_{status.lower()}",
        now=now,
        status=status,
    )

    assert OpportunityQueue().enqueue(
        opportunity,
        now=now,
    ) is False


def test_remove_by_id() -> None:
    """An opportunity can be explicitly removed."""
    now = datetime.now(UTC)
    queue = OpportunityQueue()

    opportunity = make_opportunity(
        "opp_remove",
        now=now,
    )

    queue.enqueue(
        opportunity,
        now=now,
    )

    assert queue.remove(
        opportunity.opportunity_id,
        now=now,
    ) is True
    assert queue.contains(
        opportunity.opportunity_id,
        now=now,
    ) is False


def test_remove_unknown_id_returns_false() -> None:
    """Removing an unknown opportunity should be harmless."""
    queue = OpportunityQueue()

    assert queue.remove(
        OpportunityId("unknown"),
    ) is False


def test_clear_returns_removed_count() -> None:
    """Clear should report how many items were removed."""
    now = datetime.now(UTC)

    queue = OpportunityQueue()

    queue.enqueue(
        make_opportunity("opp_clear_1", now=now),
        now=now,
    )
    queue.enqueue(
        make_opportunity("opp_clear_2", now=now),
        now=now,
    )

    assert queue.clear(now=now) == 2
    assert queue.size(now=now) == 0


def test_snapshot_is_sorted_and_non_destructive() -> None:
    """Snapshot should be ordered without modifying the queue."""
    now = datetime.now(UTC)

    queue = OpportunityQueue()

    first = make_opportunity(
        "opp_snapshot_a",
        now=now,
        urgency=0.3,
    )
    second = make_opportunity(
        "opp_snapshot_b",
        now=now,
        urgency=0.9,
    )

    queue.enqueue(first, now=now)
    queue.enqueue(second, now=now)

    snapshot = queue.snapshot(now=now)

    assert snapshot == (
        second,
        first,
    )
    assert queue.size(now=now) == 2


def test_naive_time_is_rejected() -> None:
    """Queue operations must use timezone-aware times."""
    opportunity = make_opportunity(
        "opp_naive",
    )

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        OpportunityQueue().enqueue(
            opportunity,
            now=datetime.now(),
        )


def test_queue_is_thread_safe_for_concurrent_enqueue() -> None:
    """Concurrent enqueue operations must preserve queue invariants."""
    queue = OpportunityQueue(
        OpportunityQueueConfig(
            max_size=20,
        ),
    )

    now = datetime.now(UTC)

    opportunities = tuple(
        make_opportunity(
            f"opp_thread_{index}",
            now=now,
        )
        for index in range(20)
    )

    threads = tuple(
        Thread(
            target=queue.enqueue,
            kwargs={
                "opportunity": opportunity,
                "now": now,
            },
        )
        for opportunity in opportunities
    )

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert queue.size(now=now) == 20
    assert len(queue.snapshot(now=now)) == 20


def test_dequeue_empty_queue_returns_none() -> None:
    """Empty queues should return None."""
    assert OpportunityQueue().dequeue() is None


def test_peek_empty_queue_returns_none() -> None:
    """Peeking an empty queue should return None."""
    assert OpportunityQueue().peek() is None
