"""Behavioral tests for the SQLAlchemy runtime store."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.engine import CursorResult
from sqlalchemy.sql import ClauseElement

from lyrion.persistence.contracts import (
    RuntimeInstance,
    RuntimeLifecycleState,
)
from lyrion.persistence.sqlalchemy.errors import PersistenceConflictError
from lyrion.persistence.sqlalchemy.runtime_store import (
    SQLAlchemyRuntimeStore,
)

BASE_TIME = datetime(
    2026,
    8,
    31,
    12,
    0,
    tzinfo=UTC,
)


class FakeScalarResult:
    """Minimal scalar-result implementation for adapter tests."""

    def __init__(
        self,
        value: object,
    ) -> None:
        """Store the scalar value."""
        self._value = value

    def scalar_one_or_none(self) -> object:
        """Return the configured scalar value."""
        return self._value


class FakeCursorResult:
    """Minimal DML result carrying affected-row count."""

    def __init__(
        self,
        rowcount: int,
    ) -> None:
        """Store the affected-row count."""
        self.rowcount = rowcount


class FakeSession:
    """Minimal asynchronous session test double."""

    def __init__(
        self,
        *,
        get_value: object = None,
        update_rowcount: int = 1,
        update_mode: bool = False,
    ) -> None:
        """Initialize configured SQLAlchemy result behavior."""
        self.get_value = get_value
        self.update_rowcount = update_rowcount
        self.update_mode = update_mode
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
        """Record and return a configured SQL result."""
        self.executed.append(statement)

        if self.update_mode:
            return cast(
                CursorResult[Any],
                FakeCursorResult(self.update_rowcount),
            )

        return FakeScalarResult(self.get_value)


class FakeSessionFactory:
    """Async session factory supporting both context-manager forms."""

    def __init__(
        self,
        session: FakeSession,
    ) -> None:
        """Store the session instance."""
        self.session = session

    def __call__(self) -> FakeSession:
        """Return the configured session."""
        return self.session

    @asynccontextmanager
    async def begin(
        self,
    ) -> AsyncIterator[FakeSession]:
        """Provide a transaction context."""
        yield self.session


def make_instance(
    *,
    state: RuntimeLifecycleState = RuntimeLifecycleState.RUNNING,
    revision: int = 1,
) -> RuntimeInstance:
    """Create a valid runtime instance."""
    return RuntimeInstance(
        instance_id="runtime:001",
        state=state,
        started_at=BASE_TIME,
        heartbeat_at=BASE_TIME,
        revision=revision,
    )


@pytest.mark.asyncio
async def test_get_missing_returns_none() -> None:
    """Missing durable runtime state should return None."""
    session = FakeSession(
        get_value=None,
    )
    store = SQLAlchemyRuntimeStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.get("runtime:001")

    assert result is None
    assert len(session.executed) == 1


@pytest.mark.asyncio
async def test_get_existing_converts_persisted_state() -> None:
    """Stored string state should become its domain enum."""
    session = FakeSession(
        get_value=type(
            "RuntimeRow",
            (),
            {
                "instance_id": "runtime:001",
                "state": "RUNNING",
                "started_at": BASE_TIME,
                "heartbeat_at": BASE_TIME,
                "revision": 3,
            },
        )(),
    )

    store = SQLAlchemyRuntimeStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.get("runtime:001")

    assert result is not None
    assert result.instance_id == "runtime:001"
    assert result.state is RuntimeLifecycleState.RUNNING
    assert result.revision == 3


@pytest.mark.asyncio
async def test_get_rejects_blank_identifier() -> None:
    """Blank runtime identifiers must fail closed."""
    session = FakeSession()
    store = SQLAlchemyRuntimeStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        ValueError,
        match="instance_id must not be empty",
    ):
        await store.get("   ")


@pytest.mark.asyncio
async def test_save_returns_original_instance() -> None:
    """Successful insertion should return the domain instance."""
    instance = make_instance()

    session = FakeSession()
    store = SQLAlchemyRuntimeStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.save(instance)

    assert result == instance
    assert len(session.executed) == 1


@pytest.mark.asyncio
async def test_save_duplicate_raises_conflict() -> None:
    """Insert conflicts must become persistence conflicts."""
    from sqlalchemy.exc import IntegrityError

    class IntegrityErrorSession(FakeSession):
        """Session double that raises on insertion."""

        async def execute(
            self,
            statement: ClauseElement,
        ) -> object:
            """Raise a database integrity error."""
            self.executed.append(statement)
            raise IntegrityError(
                "duplicate",
                {},
                Exception("duplicate"),
            )

    session = IntegrityErrorSession()
    store = SQLAlchemyRuntimeStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        PersistenceConflictError,
        match="already exists",
    ):
        await store.save(make_instance())


@pytest.mark.asyncio
async def test_transition_increments_revision() -> None:
    """A valid transition must advance the optimistic revision."""
    session = FakeSession(
        update_rowcount=1,
        update_mode=True,
    )
    store = SQLAlchemyRuntimeStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.transition(
        "runtime:001",
        expected_revision=1,
        state=make_instance(
            state=RuntimeLifecycleState.PAUSED,
            revision=1,
        ),
    )

    assert result.state is RuntimeLifecycleState.PAUSED
    assert result.revision == 2
    assert len(session.executed) == 1


@pytest.mark.asyncio
async def test_transition_stale_revision_raises_conflict() -> None:
    """A lost optimistic-concurrency race must fail closed."""
    session = FakeSession(
        update_rowcount=0,
        update_mode=True,
    )
    store = SQLAlchemyRuntimeStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        PersistenceConflictError,
        match="revision conflict",
    ):
        await store.transition(
            "runtime:001",
            expected_revision=4,
            state=make_instance(
                state=RuntimeLifecycleState.PAUSED,
                revision=4,
            ),
        )


@pytest.mark.asyncio
async def test_transition_rejects_identity_mismatch() -> None:
    """Transition identity must match the requested runtime identifier."""
    session = FakeSession()
    store = SQLAlchemyRuntimeStore(
        cast(Any, FakeSessionFactory(session)),
    )

    state = RuntimeInstance(
        instance_id="runtime:other",
        state=RuntimeLifecycleState.PAUSED,
        started_at=BASE_TIME,
        heartbeat_at=BASE_TIME,
        revision=1,
    )

    with pytest.raises(
        ValueError,
        match="must match instance_id",
    ):
        await store.transition(
            "runtime:001",
            expected_revision=1,
            state=state,
        )


@pytest.mark.asyncio
async def test_transition_rejects_non_positive_revision() -> None:
    """Optimistic-concurrency revisions must be positive."""
    session = FakeSession()
    store = SQLAlchemyRuntimeStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        ValueError,
        match="must be positive",
    ):
        await store.transition(
            "runtime:001",
            expected_revision=0,
            state=make_instance(),
        )
