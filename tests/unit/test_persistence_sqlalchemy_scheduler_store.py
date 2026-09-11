"""Behavioral tests for the SQLAlchemy scheduler store."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from sqlalchemy.engine import CursorResult
from sqlalchemy.sql import ClauseElement

from lyrion.persistence.contracts import (
    PersistentScheduler,
    PersistentSchedulerState,
)
from lyrion.persistence.sqlalchemy.errors import PersistenceConflictError
from lyrion.persistence.sqlalchemy.scheduler_store import (
    SQLAlchemySchedulerStore,
)

BASE_TIME = datetime(
    2026,
    8,
    31,
    12,
    0,
    tzinfo=UTC,
)


def make_scheduler(
    *,
    scheduler_id: str = "scheduler:001",
    state: PersistentSchedulerState = (
        PersistentSchedulerState.READY
    ),
    next_run_at: datetime | None = None,
    revision: int = 1,
) -> PersistentScheduler:
    """Create a valid scheduler contract."""
    return PersistentScheduler(
        scheduler_id=scheduler_id,
        state=state,
        next_run_at=next_run_at,
        revision=revision,
    )


def make_row(
    scheduler: PersistentScheduler,
) -> object:
    """Create a fake SQLAlchemy ORM row."""
    return type(
        "SchedulerRow",
        (),
        {
            "scheduler_id": scheduler.scheduler_id,
            "state": scheduler.state.value,
            "next_run_at": scheduler.next_run_at,
            "revision": scheduler.revision,
        },
    )()


class FakeScalarResult:
    """Minimal scalar query result."""

    def __init__(
        self,
        value: object = None,
    ) -> None:
        """Store the configured scalar value."""
        self._value = value

    def scalar_one_or_none(self) -> object:
        """Return the configured scalar."""
        return self._value


class FakeSession:
    """Minimal asynchronous SQLAlchemy session double."""

    def __init__(
        self,
        *,
        query_value: object = None,
        write_value: object = None,
    ) -> None:
        """Initialize configured results."""
        self.query_value = query_value
        self.write_value = write_value
        self.executed: list[ClauseElement] = []

    async def __aenter__(self) -> FakeSession:
        """Enter the session context."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        """Exit the session context."""

    async def execute(
        self,
        statement: ClauseElement,
    ) -> object:
        """Record and return a configured result."""
        self.executed.append(statement)

        statement_text = str(statement).lstrip().upper()

        if (
            statement_text.startswith("INSERT")
            or statement_text.startswith("UPDATE")
        ):
            return cast(
                CursorResult[Any],
                FakeScalarResult(self.write_value),
            )

        return FakeScalarResult(self.query_value)


class FakeSessionFactory:
    """Async session factory for scheduler store tests."""

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
async def test_get_missing_returns_none() -> None:
    """Missing scheduler state should return None."""
    session = FakeSession()

    store = SQLAlchemySchedulerStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.get("scheduler:missing")

    assert result is None
    assert len(session.executed) == 1


@pytest.mark.asyncio
async def test_get_existing_returns_domain_scheduler() -> None:
    """Persisted scheduler rows should convert to the domain contract."""
    scheduler = make_scheduler(
        state=PersistentSchedulerState.PAUSED,
        next_run_at=BASE_TIME + timedelta(minutes=2),
        revision=4,
    )

    session = FakeSession(
        query_value=make_row(scheduler),
    )

    store = SQLAlchemySchedulerStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.get("scheduler:001")

    assert result == scheduler


@pytest.mark.asyncio
async def test_get_rejects_blank_identifier() -> None:
    """Scheduler identity must not be blank."""
    store = SQLAlchemySchedulerStore(
        cast(Any, FakeSessionFactory(FakeSession())),
    )

    with pytest.raises(
        ValueError,
        match="scheduler_id must not be empty",
    ):
        await store.get("   ")


@pytest.mark.asyncio
async def test_save_returns_scheduler() -> None:
    """Successful insertion should return the supplied scheduler."""
    scheduler = make_scheduler()
    session = FakeSession()

    store = SQLAlchemySchedulerStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.save(scheduler)

    assert result == scheduler
    assert len(session.executed) == 1


@pytest.mark.asyncio
async def test_save_supports_null_next_run_at() -> None:
    """An initial scheduler may persist a null next-run deadline."""
    scheduler = make_scheduler(
        next_run_at=None,
    )
    session = FakeSession()

    store = SQLAlchemySchedulerStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.save(scheduler)

    assert result.next_run_at is None


@pytest.mark.asyncio
async def test_save_duplicate_raises_conflict() -> None:
    """Duplicate scheduler identity should become a persistence conflict."""
    from sqlalchemy.exc import IntegrityError

    class ConflictSession(FakeSession):
        """Session double that raises on insertion."""

        async def execute(
            self,
            statement: ClauseElement,
        ) -> object:
            """Raise an insert conflict."""
            self.executed.append(statement)
            raise IntegrityError(
                "duplicate",
                {},
                Exception("duplicate"),
            )

    session = ConflictSession()

    store = SQLAlchemySchedulerStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        PersistenceConflictError,
        match="scheduler already exists",
    ):
        await store.save(make_scheduler())


@pytest.mark.asyncio
async def test_transition_increments_revision() -> None:
    """A valid scheduler transition should advance revision."""
    transitioned = make_scheduler(
        state=PersistentSchedulerState.PAUSED,
        next_run_at=BASE_TIME + timedelta(minutes=5),
        revision=2,
    )

    session = FakeSession(
        write_value=make_row(transitioned),
    )

    store = SQLAlchemySchedulerStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.transition(
        "scheduler:001",
        expected_revision=1,
        state=PersistentSchedulerState.PAUSED,
        next_run_at=BASE_TIME + timedelta(minutes=5),
    )

    assert result == transitioned
    assert result.revision == 2


@pytest.mark.asyncio
async def test_transition_supports_null_next_run_at() -> None:
    """A transition may deliberately clear the next-run deadline."""
    transitioned = make_scheduler(
        next_run_at=None,
        revision=2,
    )

    session = FakeSession(
        write_value=make_row(transitioned),
    )

    store = SQLAlchemySchedulerStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.transition(
        "scheduler:001",
        expected_revision=1,
        state=PersistentSchedulerState.READY,
        next_run_at=None,
    )

    assert result.next_run_at is None


@pytest.mark.asyncio
async def test_transition_stale_revision_raises_conflict() -> None:
    """A stale optimistic-concurrency update must fail closed."""
    session = FakeSession(
        write_value=None,
    )

    store = SQLAlchemySchedulerStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        PersistenceConflictError,
        match="scheduler revision conflict",
    ):
        await store.transition(
            "scheduler:001",
            expected_revision=7,
            state=PersistentSchedulerState.READY,
            next_run_at=BASE_TIME,
        )


@pytest.mark.asyncio
async def test_transition_rejects_blank_identifier() -> None:
    """Scheduler transition identifiers must be non-empty."""
    store = SQLAlchemySchedulerStore(
        cast(Any, FakeSessionFactory(FakeSession())),
    )

    with pytest.raises(
        ValueError,
        match="scheduler_id must not be empty",
    ):
        await store.transition(
            " ",
            expected_revision=1,
            state=PersistentSchedulerState.READY,
            next_run_at=None,
        )


@pytest.mark.asyncio
async def test_transition_rejects_non_positive_revision() -> None:
    """Scheduler revisions must be positive."""
    store = SQLAlchemySchedulerStore(
        cast(Any, FakeSessionFactory(FakeSession())),
    )

    with pytest.raises(
        ValueError,
        match="expected_revision must be positive",
    ):
        await store.transition(
            "scheduler:001",
            expected_revision=0,
            state=PersistentSchedulerState.READY,
            next_run_at=None,
        )


@pytest.mark.asyncio
async def test_from_session_binds_existing_session() -> None:
    """The scheduler store must support UoW session composition."""
    session = FakeSession()

    store = SQLAlchemySchedulerStore._from_session(
        cast(Any, session),
    )

    assert cast(Any, store._session) is session


@pytest.mark.asyncio
async def test_transition_sql_contains_revision_predicate() -> None:
    """Transition SQL must participate in optimistic concurrency."""
    session = FakeSession(
        write_value=None,
    )

    store = SQLAlchemySchedulerStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(PersistenceConflictError):
        await store.transition(
            "scheduler:001",
            expected_revision=3,
            state=PersistentSchedulerState.PAUSED,
            next_run_at=BASE_TIME,
        )

    assert len(session.executed) == 1

    statement = str(session.executed[0])

    assert "persistent_scheduler.scheduler_id" in statement
    assert "persistent_scheduler.revision" in statement
