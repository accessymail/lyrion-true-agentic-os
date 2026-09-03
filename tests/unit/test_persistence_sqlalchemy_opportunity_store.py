"""Behavioral tests for the SQLAlchemy opportunity store."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from sqlalchemy.engine import CursorResult
from sqlalchemy.sql import ClauseElement

from lyrion.core.types import OpportunityId
from lyrion.persistence.contracts import (
    PersistentOpportunity,
    PersistentOpportunityState,
)
from lyrion.persistence.sqlalchemy.errors import PersistenceConflictError
from lyrion.persistence.sqlalchemy.opportunity_store import (
    SQLAlchemyOpportunityStore,
)

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
    """Create a valid opportunity contract."""
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


def make_row(
    opportunity: PersistentOpportunity,
) -> object:
    """Create a fake SQLAlchemy row."""
    return type(
        "OpportunityRow",
        (),
        {
            "opportunity_id": str(opportunity.opportunity_id),
            "state": opportunity.state.value,
            "created_at": opportunity.created_at,
            "expires_at": opportunity.expires_at,
            "worker_id": opportunity.worker_id,
            "lease_id": opportunity.lease_id,
            "claimed_at": opportunity.claimed_at,
            "completed_at": opportunity.completed_at,
            "execution_id": opportunity.execution_id,
            "revision": opportunity.revision,
        },
    )()


class FakeScalarResult:
    """Minimal scalar result implementation."""

    def __init__(
        self,
        value: object = None,
        values: Sequence[object] = (),
    ) -> None:
        """Store configured result data."""
        self._value = value
        self._values = list(values)

    def scalar_one_or_none(self) -> object:
        """Return one scalar row."""
        return self._value

    def scalars(self) -> FakeScalarResult:
        """Return this result for scalar iteration."""
        return self

    def all(self) -> list[object]:
        """Return all configured rows."""
        return self._values


class FakeCursorResult:
    """Minimal DML result supporting RETURNING."""

    def __init__(
        self,
        row: object = None,
    ) -> None:
        """Store configured DML output."""
        self._row = row

    def scalar_one_or_none(self) -> object:
        """Return one configured ORM row."""
        return self._row


class FakeSession:
    """Minimal asynchronous session double."""

    def __init__(
        self,
        *,
        query_value: object = None,
        query_values: Sequence[object] = (),
        write_value: object = None,
    ) -> None:
        """Initialize configured database behavior."""
        self.query_value = query_value
        self.query_values = list(query_values)
        self.write_value = write_value
        self.executed: list[ClauseElement] = []

    async def __aenter__(self) -> FakeSession:
        """Enter the async session context."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        """Exit the async session context."""

    async def execute(
        self,
        statement: ClauseElement,
    ) -> object:
        """Record and return configured SQL results."""
        self.executed.append(statement)

        statement_text = str(statement).lstrip().upper()

        if (
            statement_text.startswith("INSERT")
            or statement_text.startswith("UPDATE")
        ):
            return cast(
                CursorResult[Any],
                FakeCursorResult(
                    row=self.write_value,
                ),
            )

        return FakeScalarResult(
            value=self.query_value,
            values=self.query_values,
        )


class FakeSessionFactory:
    """Async session factory for adapter tests."""

    def __init__(
        self,
        session: FakeSession,
    ) -> None:
        """Store the configured session."""
        self.session = session

    def __call__(self) -> FakeSession:
        """Return the configured session."""
        return self.session

    @asynccontextmanager
    async def begin(
        self,
    ) -> AsyncIterator[FakeSession]:
        """Provide an async transaction context."""
        yield self.session


@pytest.mark.asyncio
async def test_create_returns_opportunity() -> None:
    """Creation should persist and return the supplied opportunity."""
    opportunity = make_opportunity()
    session = FakeSession()
    store = SQLAlchemyOpportunityStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.create(opportunity)

    assert result == opportunity
    assert len(session.executed) == 1


@pytest.mark.asyncio
async def test_create_duplicate_raises_conflict() -> None:
    """Duplicate opportunity identity should become a conflict."""
    opportunity = make_opportunity()

    class ConflictSession(FakeSession):
        async def execute(
            self,
            statement: ClauseElement,
        ) -> object:
            """Raise an insert conflict."""
            raise __import__(
                "sqlalchemy.exc",
                fromlist=["IntegrityError"],
            ).IntegrityError(
                "duplicate",
                {},
                Exception("duplicate"),
            )

    session = ConflictSession()
    store = SQLAlchemyOpportunityStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        PersistenceConflictError,
        match="opportunity already exists",
    ):
        await store.create(opportunity)


@pytest.mark.asyncio
async def test_get_existing_returns_domain_record() -> None:
    """Existing rows should become domain opportunities."""
    opportunity = make_opportunity()
    session = FakeSession(
        query_value=make_row(opportunity),
    )
    store = SQLAlchemyOpportunityStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.get("opportunity:001")

    assert result == opportunity


@pytest.mark.asyncio
async def test_get_missing_returns_none() -> None:
    """Missing opportunities should return None."""
    session = FakeSession()
    store = SQLAlchemyOpportunityStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.get("opportunity:missing")

    assert result is None


@pytest.mark.asyncio
async def test_blank_opportunity_id_is_rejected() -> None:
    """Opportunity identifiers must be non-empty."""
    session = FakeSession()
    store = SQLAlchemyOpportunityStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        ValueError,
        match="opportunity_id must not be empty",
    ):
        await store.get(" ")


@pytest.mark.asyncio
async def test_claim_queued_opportunity() -> None:
    """An unexpired queued opportunity should become claimed."""
    claimed = make_opportunity(
        state=PersistentOpportunityState.CLAIMED,
        claimed_at=BASE_TIME + timedelta(seconds=1),
        worker_id="worker:001",
        lease_id="lease:001",
        revision=2,
    )
    session = FakeSession(
        write_value=make_row(claimed),
    )
    store = SQLAlchemyOpportunityStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.claim(
        opportunity_id=claimed.opportunity_id,
        worker_id="worker:001",
        lease_id="lease:001",
        claimed_at=claimed.claimed_at or BASE_TIME,
        expected_revision=1,
    )

    assert result == claimed


@pytest.mark.asyncio
async def test_claim_expired_opportunity_returns_none() -> None:
    """Expired opportunities must not be claimable."""
    session = FakeSession(
        write_value=None,
    )
    store = SQLAlchemyOpportunityStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.claim(
        opportunity_id="opportunity:001",
        worker_id="worker:001",
        lease_id="lease:001",
        claimed_at=BASE_TIME + timedelta(minutes=1),
        expected_revision=1,
    )

    assert result is None


@pytest.mark.asyncio
async def test_claim_wrong_revision_returns_none() -> None:
    """A stale claim must not mutate the opportunity."""
    session = FakeSession(
        write_value=None,
    )
    store = SQLAlchemyOpportunityStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.claim(
        opportunity_id="opportunity:001",
        worker_id="worker:001",
        lease_id="lease:001",
        claimed_at=BASE_TIME + timedelta(seconds=1),
        expected_revision=2,
    )

    assert result is None


@pytest.mark.asyncio
async def test_transition_to_executing_requires_execution_id() -> None:
    """EXECUTING transitions must identify their execution."""
    store = SQLAlchemyOpportunityStore(
        cast(Any, FakeSessionFactory(FakeSession())),
    )

    with pytest.raises(
        ValueError,
        match="EXECUTING transition requires execution_id",
    ):
        await store.transition(
            opportunity_id="opportunity:001",
            worker_id="worker:001",
            lease_id="lease:001",
            expected_revision=2,
            target_state=PersistentOpportunityState.EXECUTING,
            occurred_at=BASE_TIME + timedelta(seconds=2),
        )


@pytest.mark.asyncio
async def test_transition_to_executing_preserves_execution_identity() -> None:
    """EXECUTING transitions should persist execution identity."""
    executing = make_opportunity(
        state=PersistentOpportunityState.EXECUTING,
        claimed_at=BASE_TIME + timedelta(seconds=1),
        worker_id="worker:001",
        lease_id="lease:001",
        execution_id="execution:001",
        revision=3,
    )
    session = FakeSession(
        write_value=make_row(executing),
    )
    store = SQLAlchemyOpportunityStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.transition(
        opportunity_id="opportunity:001",
        worker_id="worker:001",
        lease_id="lease:001",
        expected_revision=2,
        target_state=PersistentOpportunityState.EXECUTING,
        occurred_at=BASE_TIME + timedelta(seconds=2),
        execution_id="execution:001",
    )

    assert result == executing


@pytest.mark.asyncio
async def test_terminal_transition_sets_completed_at() -> None:
    """Terminal transitions should persist completion evidence."""
    completed = make_opportunity(
        state=PersistentOpportunityState.COMPLETED,
        claimed_at=BASE_TIME + timedelta(seconds=1),
        completed_at=BASE_TIME + timedelta(seconds=3),
        worker_id="worker:001",
        lease_id="lease:001",
        execution_id="execution:001",
        revision=4,
    )
    session = FakeSession(
        write_value=make_row(completed),
    )
    store = SQLAlchemyOpportunityStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.transition(
        opportunity_id="opportunity:001",
        worker_id="worker:001",
        lease_id="lease:001",
        expected_revision=3,
        target_state=PersistentOpportunityState.COMPLETED,
        occurred_at=BASE_TIME + timedelta(seconds=3),
    )

    assert result == completed


@pytest.mark.asyncio
async def test_transition_conflict_raises() -> None:
    """Ownership or revision mismatches must raise conflict."""
    session = FakeSession(
        write_value=None,
    )
    store = SQLAlchemyOpportunityStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        PersistenceConflictError,
        match="opportunity transition conflict",
    ):
        await store.transition(
            opportunity_id="opportunity:001",
            worker_id="worker:wrong",
            lease_id="lease:001",
            expected_revision=2,
            target_state=PersistentOpportunityState.EXECUTING,
            occurred_at=BASE_TIME + timedelta(seconds=2),
            execution_id="execution:001",
        )


@pytest.mark.asyncio
async def test_find_claimable_returns_bounded_rows() -> None:
    """Claimable lookup should return bounded queued opportunities."""
    first = make_opportunity(
        opportunity_id="opportunity:001",
    )
    second = make_opportunity(
        opportunity_id="opportunity:002",
    )

    session = FakeSession(
        query_values=(
            make_row(first),
            make_row(second),
        ),
    )
    store = SQLAlchemyOpportunityStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.find_claimable(
        now=BASE_TIME + timedelta(seconds=1),
        limit=2,
    )

    assert result == [first, second]


@pytest.mark.asyncio
async def test_find_claimable_requires_positive_limit() -> None:
    """Claimable lookup limits must be positive."""
    store = SQLAlchemyOpportunityStore(
        cast(Any, FakeSessionFactory(FakeSession())),
    )

    with pytest.raises(
        ValueError,
        match="limit must be positive",
    ):
        await store.find_claimable(
            now=BASE_TIME,
            limit=0,
        )


@pytest.mark.asyncio
async def test_find_recoverable_returns_recovery_states() -> None:
    """Recovery lookup should expose unresolved lifecycle states."""
    claimed = make_opportunity(
        opportunity_id="opportunity:001",
        state=PersistentOpportunityState.CLAIMED,
        claimed_at=BASE_TIME + timedelta(seconds=1),
        worker_id="worker:001",
        lease_id="lease:001",
    )
    executing = make_opportunity(
        opportunity_id="opportunity:002",
        state=PersistentOpportunityState.EXECUTING,
        claimed_at=BASE_TIME + timedelta(seconds=1),
        execution_id="execution:002",
    )
    unknown = make_opportunity(
        opportunity_id="opportunity:003",
        state=PersistentOpportunityState.UNKNOWN,
        completed_at=BASE_TIME + timedelta(seconds=1),
    )

    session = FakeSession(
        query_values=(
            make_row(claimed),
            make_row(executing),
            make_row(unknown),
        ),
    )
    store = SQLAlchemyOpportunityStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.find_recoverable(
        now=BASE_TIME + timedelta(minutes=1),
        limit=3,
    )

    assert result == [claimed, executing, unknown]


@pytest.mark.asyncio
async def test_find_recoverable_requires_positive_limit() -> None:
    """Recovery lookup limits must be positive."""
    store = SQLAlchemyOpportunityStore(
        cast(Any, FakeSessionFactory(FakeSession())),
    )

    with pytest.raises(
        ValueError,
        match="limit must be positive",
    ):
        await store.find_recoverable(
            now=BASE_TIME,
            limit=0,
        )


@pytest.mark.asyncio
async def test_find_claimable_sql_contains_state_expiry_order_and_limit() -> None:
    """Claimable SQL must enforce queue, expiry, ordering, and bounds."""
    session = FakeSession(
        query_values=(),
    )
    store = SQLAlchemyOpportunityStore(
        cast(Any, FakeSessionFactory(session)),
    )

    await store.find_claimable(
        now=BASE_TIME + timedelta(seconds=5),
        limit=7,
    )

    assert len(session.executed) == 1

    statement = str(session.executed[0])

    assert "persistent_opportunities.state" in statement
    assert "persistent_opportunities.expires_at" in statement
    assert "persistent_opportunities.created_at" in statement
    assert "persistent_opportunities.opportunity_id" in statement
    assert " LIMIT " in statement


@pytest.mark.asyncio
async def test_find_recoverable_sql_contains_recovery_states_and_bound() -> None:
    """Recovery SQL must restrict lifecycle states and apply a bound."""
    session = FakeSession(
        query_values=(),
    )
    store = SQLAlchemyOpportunityStore(
        cast(Any, FakeSessionFactory(session)),
    )

    await store.find_recoverable(
        now=BASE_TIME + timedelta(minutes=1),
        limit=9,
    )

    assert len(session.executed) == 1

    statement = str(session.executed[0])

    assert "persistent_opportunities.state" in statement
    assert "persistent_opportunities.created_at" in statement
    assert "persistent_opportunities.opportunity_id" in statement
    assert " LIMIT " in statement
