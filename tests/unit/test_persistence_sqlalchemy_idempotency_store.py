"""Behavioral tests for the SQLAlchemy idempotency store."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy.engine import CursorResult
from sqlalchemy.sql import ClauseElement

from lyrion.persistence.contracts import PersistentIdempotencyRecord
from lyrion.persistence.sqlalchemy.idempotency_store import (
    SQLAlchemyIdempotencyStore,
)

BASE_TIME = datetime(
    2026,
    8,
    31,
    12,
    0,
    tzinfo=UTC,
)


def make_record(
    *,
    idempotency_key: str = "idem:001",
    request_id: str = "request:001",
    execution_id: str = "execution:001",
) -> PersistentIdempotencyRecord:
    """Create a valid idempotency record."""
    return PersistentIdempotencyRecord(
        idempotency_key=idempotency_key,
        request_id=request_id,
        execution_id=execution_id,
        reserved_at=BASE_TIME,
    )


class FakeRow:
    """Minimal row exposing a key attribute."""

    def __init__(
        self,
        idempotency_key: str,
    ) -> None:
        """Store the returned key."""
        self.idempotency_key = idempotency_key


class FakeResult:
    """Minimal SQL result implementation."""

    def __init__(
        self,
        *,
        row: object = None,
        scalar: object = None,
    ) -> None:
        """Store configured query results."""
        self._row = row
        self._scalar = scalar

    def first(self) -> object:
        """Return the configured first row or scalar value."""
        if self._row is not None:
            return self._row

        return self._scalar

    def scalar_one_or_none(self) -> object:
        """Return the configured scalar result."""
        return self._scalar


class FakeCursorResult:
    """Minimal DML result exposing RETURNING behavior."""

    def __init__(
        self,
        row: object = None,
    ) -> None:
        """Store the configured returned row."""
        self._row = row

    def first(self) -> object:
        """Return the configured returned row."""
        return self._row


class FakeSession:
    """Minimal async SQLAlchemy session double."""

    def __init__(
        self,
        *,
        dml_row: object = None,
        query_value: object = None,
    ) -> None:
        """Configure DML and query results."""
        self.dml_row = dml_row
        self.query_value = query_value
        self.executed: list[ClauseElement] = []

    async def __aenter__(self) -> FakeSession:
        """Enter the session."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        """Exit the session."""

    async def execute(
        self,
        statement: ClauseElement,
    ) -> object:
        """Record SQL and return a configured result."""
        self.executed.append(statement)

        statement_text = str(statement).lstrip().upper()

        if statement_text.startswith("INSERT"):
            return cast(
                CursorResult[Any],
                FakeCursorResult(self.dml_row),
            )

        return FakeResult(
            scalar=self.query_value,
        )


class FakeSessionFactory:
    """Async session factory supporting transaction contexts."""

    def __init__(
        self,
        session: FakeSession,
    ) -> None:
        """Store the session double."""
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


async def test_reserve_returns_true_when_insert_returns_row() -> None:
    """A successful INSERT RETURNING should reserve the key."""
    record = make_record()

    session = FakeSession(
        dml_row=FakeRow(record.idempotency_key),
    )
    store = SQLAlchemyIdempotencyStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.reserve(record)

    assert result is True
    assert len(session.executed) == 1

    statement_text = str(session.executed[0]).upper()

    assert "INSERT" in statement_text
    assert "ON CONFLICT" in statement_text
    assert "DO NOTHING" in statement_text
    assert "RETURNING" in statement_text


async def test_reserve_returns_false_on_conflict() -> None:
    """A conflicting idempotency key should return False."""
    record = make_record()

    session = FakeSession(
        dml_row=None,
    )
    store = SQLAlchemyIdempotencyStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.reserve(record)

    assert result is False


async def test_get_existing_record() -> None:
    """An existing reservation should round-trip through the adapter."""
    record = make_record()

    class ExistingSession(FakeSession):
        async def execute(
            self,
            statement: ClauseElement,
        ) -> object:
            """Return the configured ORM row."""
            self.executed.append(statement)

            row = type(
                "IdempotencyRow",
                (),
                {
                    "idempotency_key": record.idempotency_key,
                    "request_id": record.request_id,
                    "execution_id": record.execution_id,
                    "reserved_at": record.reserved_at,
                },
            )()

            return FakeResult(
                scalar=row,
            )

    session = ExistingSession()
    store = SQLAlchemyIdempotencyStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.get(record.idempotency_key)

    assert result == record


async def test_get_missing_record_returns_none() -> None:
    """A missing reservation should return None."""
    session = FakeSession(
        query_value=None,
    )
    store = SQLAlchemyIdempotencyStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.get("idem:missing")

    assert result is None


async def test_contains_existing_key() -> None:
    """contains() should return True for an existing key."""
    session = FakeSession(
        query_value=FakeRow("idem:001"),
    )
    store = SQLAlchemyIdempotencyStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.contains("idem:001")

    assert result is True


async def test_contains_missing_key() -> None:
    """contains() should return False for a missing key."""
    session = FakeSession(
        query_value=None,
    )
    store = SQLAlchemyIdempotencyStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.contains("idem:missing")

    assert result is False


async def test_blank_get_key_is_rejected() -> None:
    """Blank lookup keys must be rejected."""
    session = FakeSession()
    store = SQLAlchemyIdempotencyStore(
        cast(Any, FakeSessionFactory(session)),
    )

    try:
        await store.get(" ")
    except ValueError as exc:
        assert str(exc) == "idempotency_key must not be empty"
    else:
        raise AssertionError("Expected ValueError")


async def test_blank_contains_key_is_rejected() -> None:
    """Blank contains keys must be rejected."""
    session = FakeSession()
    store = SQLAlchemyIdempotencyStore(
        cast(Any, FakeSessionFactory(session)),
    )

    try:
        await store.contains(" ")
    except ValueError as exc:
        assert str(exc) == "idempotency_key must not be empty"
    else:
        raise AssertionError("Expected ValueError")
