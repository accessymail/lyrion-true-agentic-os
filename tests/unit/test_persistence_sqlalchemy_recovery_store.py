"""Behavioral tests for the SQLAlchemy recovery store."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy.sql import ClauseElement

from lyrion.persistence.contracts import RecoveryAction, RecoveryDecision
from lyrion.persistence.sqlalchemy.recovery_store import (
    SQLAlchemyRecoveryStore,
)

BASE_TIME = datetime(
    2026,
    8,
    31,
    12,
    0,
    tzinfo=UTC,
)


def make_decision(
    *,
    execution_id: str = "execution:001",
    action: RecoveryAction = RecoveryAction.REQUEUE,
    reason: str = "Lease expired.",
    evaluated_at: datetime = BASE_TIME,
    source_revision: int = 1,
) -> RecoveryDecision:
    """Create a valid recovery decision."""
    return RecoveryDecision(
        execution_id=execution_id,
        action=action,
        reason=reason,
        evaluated_at=evaluated_at,
        source_revision=source_revision,
    )


def make_row(
    decision: RecoveryDecision,
    *,
    row_id: int = 1,
) -> object:
    """Create a fake ORM row."""
    return type(
        "RecoveryDecisionRow",
        (),
        {
            "id": row_id,
            "execution_id": decision.execution_id,
            "action": decision.action.value,
            "reason": decision.reason,
            "evaluated_at": decision.evaluated_at,
            "source_revision": decision.source_revision,
        },
    )()


class FakeScalarResult:
    """Minimal scalar-result implementation."""

    def __init__(
        self,
        values: list[object],
    ) -> None:
        """Store configured rows."""
        self._values = values

    def scalars(self) -> FakeScalarResult:
        """Return this result for scalar iteration."""
        return self

    def all(self) -> list[object]:
        """Return all configured rows."""
        return self._values


class FakeSession:
    """Minimal asynchronous session double."""

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

    def __init__(
        self,
        *,
        values: list[object] | None = None,
    ) -> None:
        """Initialize configured results."""
        self.values = values or []
        self.executed: list[ClauseElement] = []

    async def execute(
        self,
        statement: ClauseElement,
    ) -> object:
        """Record the statement and return configured rows."""
        self.executed.append(statement)

        return FakeScalarResult(self.values)


class FakeSessionFactory:
    """Async session factory supporting transaction contexts."""

    def __init__(
        self,
        session: FakeSession,
    ) -> None:
        """Store the fake session."""
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


async def test_record_returns_decision() -> None:
    """Recording should persist and return the supplied decision."""
    decision = make_decision()
    session = FakeSession()

    store = SQLAlchemyRecoveryStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.record(decision)

    assert result == decision
    assert len(session.executed) == 1

    statement_text = str(session.executed[0]).upper()

    assert "INSERT" in statement_text


async def test_find_for_execution_returns_ordered_decisions() -> None:
    """Recovery evidence should round-trip in deterministic order."""
    first = make_decision(
        evaluated_at=BASE_TIME,
    )
    second = make_decision(
        action=RecoveryAction.RECONCILE,
        reason="Outcome requires reconciliation.",
        evaluated_at=BASE_TIME + timedelta(seconds=1),
        source_revision=2,
    )

    session = FakeSession(
        values=[
            make_row(first, row_id=1),
            make_row(second, row_id=2),
        ],
    )

    store = SQLAlchemyRecoveryStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.find_for_execution(
        "execution:001",
    )

    assert result == [first, second]


async def test_find_for_execution_missing_returns_empty_list() -> None:
    """An execution with no recovery history should return no decisions."""
    session = FakeSession()

    store = SQLAlchemyRecoveryStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.find_for_execution(
        "execution:missing",
    )

    assert result == []


async def test_find_for_execution_blank_id_is_rejected() -> None:
    """Blank execution identifiers must be rejected."""
    session = FakeSession()

    store = SQLAlchemyRecoveryStore(
        cast(Any, FakeSessionFactory(session)),
    )

    try:
        await store.find_for_execution(" ")
    except ValueError as exc:
        assert str(exc) == "execution_id must not be empty"
    else:
        raise AssertionError("Expected ValueError")
