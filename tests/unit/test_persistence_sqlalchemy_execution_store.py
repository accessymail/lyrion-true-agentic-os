"""Behavioral tests for the SQLAlchemy execution store."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from sqlalchemy.engine import CursorResult
from sqlalchemy.sql import ClauseElement

from lyrion.core.types import IdempotencyKey, OpportunityId, TaskId
from lyrion.persistence.contracts import (
    PersistentExecutionRecord,
    PersistentExecutionState,
)
from lyrion.persistence.sqlalchemy.errors import PersistenceConflictError
from lyrion.persistence.sqlalchemy.execution_store import SQLAlchemyExecutionStore

BASE_TIME = datetime(
    2026,
    8,
    31,
    12,
    0,
    tzinfo=UTC,
)


def make_execution(
    *,
    execution_id: str = "execution:001",
    state: PersistentExecutionState = PersistentExecutionState.QUEUED,
    claimed_at: datetime | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    worker_id: str | None = None,
    lease_id: str | None = None,
    checkpoint_ref: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    revision: int = 1,
) -> PersistentExecutionRecord:
    """Create a valid execution contract."""
    return PersistentExecutionRecord(
        execution_id=execution_id,
        request_id="request:001",
        opportunity_id=OpportunityId("opportunity:001"),
        task_id=TaskId("task:001"),
        idempotency_key=IdempotencyKey(
            f"idem:{execution_id}",
        ),
        state=state,
        created_at=BASE_TIME,
        claimed_at=claimed_at,
        started_at=started_at,
        completed_at=completed_at,
        worker_id=worker_id,
        lease_id=lease_id,
        checkpoint_ref=checkpoint_ref,
        error_code=error_code,
        error_message=error_message,
        revision=revision,
    )


def make_row(
    record: PersistentExecutionRecord,
) -> object:
    """Create a fake SQLAlchemy row."""
    return type(
        "ExecutionRow",
        (),
        {
            "execution_id": record.execution_id,
            "request_id": record.request_id,
            "opportunity_id": str(record.opportunity_id),
            "task_id": str(record.task_id),
            "idempotency_key": str(record.idempotency_key),
            "state": record.state.value,
            "created_at": record.created_at,
            "claimed_at": record.claimed_at,
            "started_at": record.started_at,
            "completed_at": record.completed_at,
            "worker_id": record.worker_id,
            "lease_id": record.lease_id,
            "checkpoint_ref": record.checkpoint_ref,
            "error_code": record.error_code,
            "error_message": record.error_message,
            "revision": record.revision,
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
        rowcount: int = 1,
    ) -> None:
        """Store configured DML output."""
        self._row = row
        self.rowcount = rowcount

    def scalar_one_or_none(self) -> object:
        """Return one configured ORM row."""
        return self._row

    def first(self) -> object:
        """Return the configured RETURNING row."""
        return self._row


class FakeSession:
    """Minimal asynchronous session double."""

    def __init__(
        self,
        *,
        query_value: object = None,
        query_values: Sequence[object] = (),
        write_value: object = None,
        write_rowcount: int = 1,
    ) -> None:
        """Initialize configured database behavior."""
        self.query_value = query_value
        self.query_values = list(query_values)
        self.write_value = write_value
        self.write_rowcount = write_rowcount
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
        """Record and return the configured result."""
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
                    rowcount=self.write_rowcount,
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
async def test_create_returns_record() -> None:
    """Creation should persist and return the supplied record."""
    record = make_execution()
    session = FakeSession()
    store = SQLAlchemyExecutionStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.create(record)

    assert result == record
    assert len(session.executed) == 1


@pytest.mark.asyncio
async def test_create_duplicate_raises_conflict() -> None:
    """Duplicate execution identity should become a persistence conflict."""
    record = make_execution()

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
    store = SQLAlchemyExecutionStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        PersistenceConflictError,
        match="execution record already exists",
    ):
        await store.create(record)


@pytest.mark.asyncio
async def test_get_missing_returns_none() -> None:
    """Missing execution should return None."""
    session = FakeSession()
    store = SQLAlchemyExecutionStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.get("execution:001")

    assert result is None


@pytest.mark.asyncio
async def test_get_existing_returns_domain_record() -> None:
    """Existing execution rows should become domain contracts."""
    record = make_execution()
    session = FakeSession(
        query_value=make_row(record),
    )
    store = SQLAlchemyExecutionStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.get("execution:001")

    assert result == record


@pytest.mark.asyncio
async def test_claim_queued_execution() -> None:
    """A queued execution should become claimed atomically."""
    claimed = make_execution(
        state=PersistentExecutionState.CLAIMED,
        claimed_at=BASE_TIME + timedelta(seconds=1),
        worker_id="worker:001",
        lease_id="lease:001",
        revision=2,
    )

    session = FakeSession(
        write_value=make_row(claimed),
    )
    store = SQLAlchemyExecutionStore(
        cast(Any, FakeSessionFactory(session)),
    )

    assert claimed.claimed_at is not None

    result = await store.claim(
        execution_id=claimed.execution_id,
        worker_id="worker:001",
        lease_id="lease:001",
        claimed_at=claimed.claimed_at,
        expected_revision=1,
    )

    assert result == claimed


@pytest.mark.asyncio
async def test_claim_wrong_revision_returns_none() -> None:
    """A stale claim must not mutate the record."""
    session = FakeSession(
        write_value=None,
    )
    store = SQLAlchemyExecutionStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.claim(
        execution_id="execution:001",
        worker_id="worker:001",
        lease_id="lease:001",
        claimed_at=BASE_TIME + timedelta(seconds=1),
        expected_revision=2,
    )

    assert result is None


@pytest.mark.asyncio
async def test_transition_to_executing_sets_started_at() -> None:
    """EXECUTING transitions must persist explicit start evidence."""
    executing = make_execution(
        state=PersistentExecutionState.EXECUTING,
        claimed_at=BASE_TIME + timedelta(seconds=1),
        started_at=BASE_TIME + timedelta(seconds=2),
        worker_id="worker:001",
        lease_id="lease:001",
        revision=3,
    )

    session = FakeSession(
        write_value=make_row(executing),
    )
    store = SQLAlchemyExecutionStore(
        cast(Any, FakeSessionFactory(session)),
    )

    assert executing.started_at is not None

    result = await store.transition(
        execution_id="execution:001",
        worker_id="worker:001",
        lease_id="lease:001",
        expected_revision=2,
        target_state=PersistentExecutionState.EXECUTING,
        occurred_at=executing.started_at,
    )

    assert result == executing


@pytest.mark.asyncio
async def test_transition_to_terminal_sets_completed_at() -> None:
    """Terminal transitions must persist completion evidence."""
    completed = make_execution(
        state=PersistentExecutionState.COMPLETED,
        claimed_at=BASE_TIME + timedelta(seconds=1),
        started_at=BASE_TIME + timedelta(seconds=2),
        completed_at=BASE_TIME + timedelta(seconds=3),
        worker_id="worker:001",
        lease_id="lease:001",
        revision=4,
        checkpoint_ref="checkpoint:001",
    )

    session = FakeSession(
        write_value=make_row(completed),
    )
    store = SQLAlchemyExecutionStore(
        cast(Any, FakeSessionFactory(session)),
    )

    assert completed.completed_at is not None

    result = await store.transition(
        execution_id="execution:001",
        worker_id="worker:001",
        lease_id="lease:001",
        expected_revision=3,
        target_state=PersistentExecutionState.COMPLETED,
        occurred_at=completed.completed_at,
        checkpoint_ref="checkpoint:001",
    )

    assert result == completed


@pytest.mark.asyncio
async def test_transition_conflict_raises() -> None:
    """Ownership or revision mismatch must raise conflict."""
    session = FakeSession(
        write_value=None,
    )
    store = SQLAlchemyExecutionStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        PersistenceConflictError,
        match="execution transition conflict",
    ):
        await store.transition(
            execution_id="execution:001",
            worker_id="worker:wrong",
            lease_id="lease:001",
            expected_revision=2,
            target_state=PersistentExecutionState.EXECUTING,
            occurred_at=BASE_TIME + timedelta(seconds=2),
        )


@pytest.mark.asyncio
async def test_find_recoverable_returns_bounded_ordered_rows() -> None:
    """Recovery lookup should be bounded and deterministic."""
    first = make_execution(
        execution_id="execution:001",
        state=PersistentExecutionState.CLAIMED,
        claimed_at=BASE_TIME + timedelta(seconds=1),
        worker_id="worker:001",
        lease_id="lease:001",
    )
    second = make_execution(
        execution_id="execution:002",
        state=PersistentExecutionState.UNKNOWN,
    )

    session = FakeSession(
        query_values=(
            make_row(first),
            make_row(second),
        ),
    )
    store = SQLAlchemyExecutionStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.find_recoverable(
        states=(
            PersistentExecutionState.CLAIMED,
            PersistentExecutionState.UNKNOWN,
        ),
        now=BASE_TIME + timedelta(minutes=1),
        limit=2,
    )

    assert result == [first, second]


@pytest.mark.asyncio
async def test_blank_execution_id_is_rejected() -> None:
    """Execution identifiers must be non-empty."""
    session = FakeSession()
    store = SQLAlchemyExecutionStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        ValueError,
        match="execution_id must not be empty",
    ):
        await store.get(" ")


@pytest.mark.asyncio
async def test_find_recoverable_requires_states() -> None:
    """Recovery lookup requires at least one lifecycle state."""
    session = FakeSession()
    store = SQLAlchemyExecutionStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        ValueError,
        match="states must not be empty",
    ):
        await store.find_recoverable(
            states=(),
            now=BASE_TIME,
            limit=1,
        )


@pytest.mark.asyncio
async def test_find_recoverable_requires_positive_limit() -> None:
    """Recovery lookup limits must be positive."""
    session = FakeSession()
    store = SQLAlchemyExecutionStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        ValueError,
        match="limit must be positive",
    ):
        await store.find_recoverable(
            states=(PersistentExecutionState.CLAIMED,),
            now=BASE_TIME,
            limit=0,
        )


@pytest.mark.asyncio
async def test_requeue_claimed_execution() -> None:
    """A recoverable CLAIMED execution returns to QUEUED."""
    queued = make_execution(
        state=PersistentExecutionState.QUEUED,
        revision=2,
    )

    session = FakeSession(
        write_value=make_row(queued),
    )

    store = SQLAlchemyExecutionStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.requeue(
        execution_id="execution:001",
        expected_revision=1,
        occurred_at=BASE_TIME + timedelta(seconds=5),
    )

    assert result.state is PersistentExecutionState.QUEUED
    assert result.revision == 2


@pytest.mark.asyncio
async def test_requeue_conflict_raises() -> None:
    """A stale or non-claimable execution must not be requeued."""
    session = FakeSession(
        write_value=None,
    )

    store = SQLAlchemyExecutionStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        PersistenceConflictError,
        match="execution requeue conflict",
    ):
        await store.requeue(
            execution_id="execution:001",
            expected_revision=2,
            occurred_at=BASE_TIME + timedelta(seconds=5),
        )
