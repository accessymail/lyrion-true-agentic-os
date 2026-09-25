"""Runtime validation for R097 recovery re-entry."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from lyrion.piae.contracts import Opportunity
from lyrion.piae.opportunity_queue import OpportunityQueue
from lyrion.persistence.opportunity_recovery_context import (
    OpportunityRecoveryContextFactory,
)
from lyrion.persistence.opportunity_recovery_context_resolver import (
    OpportunityRecoveryContextResolver,
)
from lyrion.persistence.opportunity_recovery_reentry import (
    OpportunityRecoveryReentryCoordinator,
)
from lyrion.persistence.protocols import OpportunityRecoveryContextStore


class InMemoryRecoveryContextStore:
    """Minimal runtime store implementing the production protocol."""

    def __init__(self) -> None:
        self._items = {}

    async def create(self, context):
        if context.opportunity_id in self._items:
            raise ValueError("duplicate recovery context")
        self._items[context.opportunity_id] = context
        return context

    async def get(self, opportunity_id):
        return self._items.get(opportunity_id)

    async def exists(self, opportunity_id):
        return opportunity_id in self._items


def _make_opportunity(*, expires_at: datetime | None) -> Opportunity:
    from lyrion.core.types import (
        AutonomyLevel,
        CorrelationId,
        EventId,
        OpportunityId,
    )
    from lyrion.events.models import EventSensitivity, EventTrustLevel

    now = datetime.now(UTC)

    return Opportunity(
        opportunity_id=OpportunityId("r097-runtime-opportunity"),
        correlation_id=CorrelationId("r097-runtime-correlation"),
        trigger_event_ids=(EventId("r097-runtime-event"),),
        relevant_state_ids=("state-r097",),
        goal_context=("r097 stale authority validation",),
        title="R097 runtime validation",
        description="Validate controlled recovery re-entry.",
        user_relevance=0.9,
        expected_benefit=0.8,
        interruption_cost=0.1,
        risk_score=0.2,
        reversibility=0.9,
        urgency=0.5,
        confidence=0.95,
        required_capabilities=("test.capability",),
        required_autonomy_level=AutonomyLevel.L1,
        sensitivity=EventSensitivity.INTERNAL,
        trust_level=EventTrustLevel.HIGH,
        status="OPEN",
        created_at=now,
        expires_at=expires_at,
    )


@pytest.mark.asyncio
async def test_r097_recovery_reentry_reconstructs_and_enqueues() -> None:
    now = datetime.now(UTC)
    opportunity = _make_opportunity(
        expires_at=now + timedelta(minutes=10),
    )

    store = InMemoryRecoveryContextStore()
    context = OpportunityRecoveryContextFactory.from_opportunity(
        opportunity,
        source_provenance_ref="r097-runtime-test",
    )
    await store.create(context)

    resolver = OpportunityRecoveryContextResolver(store)
    queue = OpportunityQueue()

    coordinator = OpportunityRecoveryReentryCoordinator(
        resolver=resolver,
        opportunity_queue=queue,
    )

    result = await coordinator.reenter(
        str(opportunity.opportunity_id),
        current_time=now,
    )

    assert result.enqueued is True
    assert result.opportunity_id == str(opportunity.opportunity_id)

    queued = queue.peek(now=now)

    assert queued is not None
    assert queued.opportunity_id == opportunity.opportunity_id
    assert queued.required_capabilities == opportunity.required_capabilities


@pytest.mark.asyncio
async def test_r097_recovery_reentry_is_idempotent_for_duplicate_queue_entry() -> None:
    now = datetime.now(UTC)
    opportunity = _make_opportunity(
        expires_at=now + timedelta(minutes=10),
    )

    store = InMemoryRecoveryContextStore()
    context = OpportunityRecoveryContextFactory.from_opportunity(
        opportunity,
        source_provenance_ref="r097-runtime-test",
    )
    await store.create(context)

    resolver = OpportunityRecoveryContextResolver(store)
    queue = OpportunityQueue()

    coordinator = OpportunityRecoveryReentryCoordinator(
        resolver=resolver,
        opportunity_queue=queue,
    )

    first = await coordinator.reenter(
        str(opportunity.opportunity_id),
        current_time=now,
    )
    second = await coordinator.reenter(
        str(opportunity.opportunity_id),
        current_time=now,
    )

    assert first.enqueued is True
    assert second.enqueued is False
    assert queue.size(now=now) == 1


@pytest.mark.asyncio
async def test_r097_expired_recovery_context_fails_closed() -> None:
    created_at = datetime.now(UTC)
    expires_at = created_at + timedelta(seconds=1)

    opportunity = _make_opportunity(
        expires_at=expires_at,
    )

    store = InMemoryRecoveryContextStore()
    context = OpportunityRecoveryContextFactory.from_opportunity(
        opportunity,
        source_provenance_ref="r097-runtime-test",
    )
    await store.create(context)

    resolver = OpportunityRecoveryContextResolver(store)
    queue = OpportunityQueue()

    coordinator = OpportunityRecoveryReentryCoordinator(
        resolver=resolver,
        opportunity_queue=queue,
    )

    recovery_time = expires_at + timedelta(seconds=1)

    with pytest.raises(ValueError, match="expired"):
        await coordinator.reenter(
            str(opportunity.opportunity_id),
            current_time=recovery_time,
        )

    assert queue.size(now=recovery_time) == 0


@pytest.mark.asyncio
async def test_r097_missing_recovery_context_fails_closed() -> None:
    now = datetime.now(UTC)

    store = InMemoryRecoveryContextStore()
    resolver = OpportunityRecoveryContextResolver(store)
    queue = OpportunityQueue()

    coordinator = OpportunityRecoveryReentryCoordinator(
        resolver=resolver,
        opportunity_queue=queue,
    )

    with pytest.raises(ValueError, match="does not exist"):
        await coordinator.reenter(
            "missing-r097-opportunity",
            current_time=now,
        )

    assert queue.size(now=now) == 0


@pytest.mark.asyncio
async def test_r097_integrity_failure_fails_closed() -> None:
    now = datetime.now(UTC)
    opportunity = _make_opportunity(
        expires_at=now + timedelta(minutes=10),
    )

    store = InMemoryRecoveryContextStore()
    context = OpportunityRecoveryContextFactory.from_opportunity(
        opportunity,
        source_provenance_ref="r097-runtime-test",
    )

    corrupted = context.model_copy(
        update={"integrity_digest": "0" * 64},
    )
    await store.create(corrupted)

    resolver = OpportunityRecoveryContextResolver(store)
    queue = OpportunityQueue()

    coordinator = OpportunityRecoveryReentryCoordinator(
        resolver=resolver,
        opportunity_queue=queue,
    )

    with pytest.raises(ValueError, match="integrity"):
        await coordinator.reenter(
            str(opportunity.opportunity_id),
            current_time=now,
        )

    assert queue.size(now=now) == 0
