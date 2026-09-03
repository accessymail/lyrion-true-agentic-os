"""Real PostgreSQL integration tests for the durable opportunity store."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from lyrion.core.types import OpportunityId
from lyrion.persistence.contracts import (
    PersistentOpportunity,
    PersistentOpportunityState,
)
from lyrion.persistence.sqlalchemy.errors import PersistenceConflictError
from lyrion.persistence.sqlalchemy.models import PersistentOpportunityModel
from lyrion.persistence.sqlalchemy.opportunity_store import (
    SQLAlchemyOpportunityStore,
)

pytestmark = pytest.mark.integration

BASE_TIME = datetime(
    2026,
    8,
    31,
    12,
    0,
    tzinfo=UTC,
)


def make_opportunity(
    *,
    opportunity_id: str = "opportunity:001",
    state: PersistentOpportunityState = (
        PersistentOpportunityState.QUEUED
    ),
    expires_at: datetime | None = None,
    worker_id: str | None = None,
    lease_id: str | None = None,
    claimed_at: datetime | None = None,
    completed_at: datetime | None = None,
    execution_id: str | None = None,
    revision: int = 1,
) -> PersistentOpportunity:
    """Create a valid durable opportunity."""
    return PersistentOpportunity(
        opportunity_id=OpportunityId(opportunity_id),
        state=state,
        created_at=BASE_TIME,
        expires_at=expires_at,
        worker_id=worker_id,
        lease_id=lease_id,
        claimed_at=claimed_at,
        completed_at=completed_at,
        execution_id=execution_id,
        revision=revision,
    )


async def fresh_store(
    engine: AsyncEngine,
) -> SQLAlchemyOpportunityStore:
    """Create a store backed by a fresh async session factory."""
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return SQLAlchemyOpportunityStore(factory)


@pytest.mark.asyncio
async def test_create_round_trips_through_postgresql(
    database_engine: AsyncEngine,
) -> None:
    """An opportunity should persist and round-trip from PostgreSQL."""
    store = await fresh_store(database_engine)
    opportunity = make_opportunity()

    result = await store.create(opportunity)
    loaded = await store.get(str(opportunity.opportunity_id))

    assert result == opportunity
    assert loaded == opportunity


@pytest.mark.asyncio
async def test_duplicate_create_raises_conflict(
    database_engine: AsyncEngine,
) -> None:
    """Duplicate opportunity identity must be rejected."""
    store = await fresh_store(database_engine)
    opportunity = make_opportunity()

    await store.create(opportunity)

    with pytest.raises(
        PersistenceConflictError,
        match="opportunity already exists",
    ):
        await store.create(opportunity)


@pytest.mark.asyncio
async def test_claim_persists_revision_and_ownership(
    database_engine: AsyncEngine,
) -> None:
    """A successful claim must persist owner, lease, state, and revision."""
    store = await fresh_store(database_engine)
    opportunity = make_opportunity()

    await store.create(opportunity)

    claimed_at = BASE_TIME + timedelta(seconds=1)

    claimed = await store.claim(
        opportunity_id=str(opportunity.opportunity_id),
        worker_id="worker:001",
        lease_id="lease:001",
        claimed_at=claimed_at,
        expected_revision=1,
    )

    assert claimed is not None
    assert claimed.state is PersistentOpportunityState.CLAIMED
    assert claimed.worker_id == "worker:001"
    assert claimed.lease_id == "lease:001"
    assert claimed.claimed_at == claimed_at
    assert claimed.revision == 2


@pytest.mark.asyncio
async def test_expired_opportunity_cannot_be_claimed(
    database_engine: AsyncEngine,
) -> None:
    """An opportunity expiring at or before claim time must not be claimed."""
    store = await fresh_store(database_engine)

    opportunity = make_opportunity(
        expires_at=BASE_TIME + timedelta(seconds=30),
    )
    await store.create(opportunity)

    result = await store.claim(
        opportunity_id=str(opportunity.opportunity_id),
        worker_id="worker:001",
        lease_id="lease:001",
        claimed_at=BASE_TIME + timedelta(seconds=30),
        expected_revision=1,
    )

    assert result is None


@pytest.mark.asyncio
async def test_two_workers_compete_for_one_opportunity_claim(
    database_engine: AsyncEngine,
) -> None:
    """Exactly one concurrent worker may claim one opportunity revision."""
    seed_store = await fresh_store(database_engine)
    opportunity = make_opportunity(
        opportunity_id="opportunity:race",
    )
    await seed_store.create(opportunity)

    async def attempt(
        worker_id: str,
        lease_id: str,
    ) -> bool:
        store = await fresh_store(database_engine)

        result = await store.claim(
            opportunity_id=str(opportunity.opportunity_id),
            worker_id=worker_id,
            lease_id=lease_id,
            claimed_at=BASE_TIME + timedelta(seconds=1),
            expected_revision=1,
        )

        return result is not None

    results = await asyncio.gather(
        attempt("worker:A", "lease:A"),
        attempt("worker:B", "lease:B"),
    )

    assert sum(results) == 1


@pytest.mark.asyncio
async def test_transition_requires_matching_owner_and_revision(
    database_engine: AsyncEngine,
) -> None:
    """Stale ownership must be rejected by PostgreSQL."""
    store = await fresh_store(database_engine)
    opportunity = make_opportunity(
        state=PersistentOpportunityState.CLAIMED,
        claimed_at=BASE_TIME + timedelta(seconds=1),
        worker_id="worker:001",
        lease_id="lease:001",
        revision=2,
    )

    await store.create(opportunity)

    with pytest.raises(
        PersistenceConflictError,
        match="opportunity transition conflict",
    ):
        await store.transition(
            opportunity_id=str(opportunity.opportunity_id),
            worker_id="worker:wrong",
            lease_id="lease:001",
            expected_revision=2,
            target_state=PersistentOpportunityState.COMPLETED,
            occurred_at=BASE_TIME + timedelta(seconds=2),
        )


@pytest.mark.asyncio
async def test_find_claimable_excludes_expired_rows_and_respects_limit(
    database_engine: AsyncEngine,
) -> None:
    """Claimable lookup must exclude expired rows and obey its bound."""
    store = await fresh_store(database_engine)

    await store.create(
        make_opportunity(
            opportunity_id="opportunity:active",
            expires_at=BASE_TIME + timedelta(minutes=5),
        )
    )
    await store.create(
        make_opportunity(
            opportunity_id="opportunity:expired",
            expires_at=BASE_TIME + timedelta(seconds=30),
        )
    )
    await store.create(
        make_opportunity(
            opportunity_id="opportunity:active-2",
            expires_at=BASE_TIME + timedelta(minutes=5),
        )
    )

    result = await store.find_claimable(
        now=BASE_TIME + timedelta(seconds=31),
        limit=1,
    )

    assert len(result) == 1
    assert result[0].opportunity_id == OpportunityId(
        "opportunity:active",
    )


@pytest.mark.asyncio
async def test_find_recoverable_returns_only_recovery_states(
    database_engine: AsyncEngine,
) -> None:
    """Recovery lookup must exclude terminal opportunity states."""
    store = await fresh_store(database_engine)

    await store.create(
        make_opportunity(
            opportunity_id="opportunity:0",
            state=PersistentOpportunityState.CLAIMED,
            claimed_at=BASE_TIME + timedelta(seconds=1),
            worker_id="worker:001",
            lease_id="lease:001",
        )
    )

    await store.create(
        make_opportunity(
            opportunity_id="opportunity:1",
            state=PersistentOpportunityState.EXECUTING,
            claimed_at=BASE_TIME + timedelta(seconds=1),
            execution_id="execution:1",
        )
    )

    await store.create(
        make_opportunity(
            opportunity_id="opportunity:2",
            state=PersistentOpportunityState.UNKNOWN,
            completed_at=BASE_TIME + timedelta(seconds=1),
        )
    )

    await store.create(
        make_opportunity(
            opportunity_id="opportunity:3",
            state=PersistentOpportunityState.COMPLETED,
            completed_at=BASE_TIME + timedelta(seconds=1),
        )
    )

    await store.create(
        make_opportunity(
            opportunity_id="opportunity:4",
            state=PersistentOpportunityState.FAILED,
            completed_at=BASE_TIME + timedelta(seconds=1),
        )
    )

    await store.create(
        make_opportunity(
            opportunity_id="opportunity:5",
            state=PersistentOpportunityState.CANCELLED,
            completed_at=BASE_TIME + timedelta(seconds=1),
        )
    )

    await store.create(
        make_opportunity(
            opportunity_id="opportunity:6",
            state=PersistentOpportunityState.ABANDONED,
            completed_at=BASE_TIME + timedelta(seconds=1),
        )
    )

    result = await store.find_recoverable(
        now=BASE_TIME + timedelta(minutes=1),
        limit=10,
    )

    assert [item.state for item in result] == [
        PersistentOpportunityState.CLAIMED,
        PersistentOpportunityState.EXECUTING,
        PersistentOpportunityState.UNKNOWN,
    ]


@pytest.mark.asyncio
async def test_persisted_row_matches_claimed_contract(
    database_engine: AsyncEngine,
) -> None:
    """The physical PostgreSQL row must match the durable contract."""
    store = await fresh_store(database_engine)

    opportunity = make_opportunity(
        opportunity_id="opportunity:physical",
    )

    await store.create(opportunity)

    await store.claim(
        opportunity_id="opportunity:physical",
        worker_id="worker:001",
        lease_id="lease:001",
        claimed_at=BASE_TIME + timedelta(seconds=1),
        expected_revision=1,
    )

    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        row = await session.scalar(
            select(PersistentOpportunityModel).where(
                PersistentOpportunityModel.opportunity_id
                == "opportunity:physical",
            )
        )

    assert row is not None
    assert row.state == PersistentOpportunityState.CLAIMED.value
    assert row.worker_id == "worker:001"
    assert row.lease_id == "lease:001"
    assert row.revision == 2
