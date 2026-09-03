"""Real PostgreSQL integration tests for recovery persistence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from lyrion.persistence.contracts import RecoveryAction, RecoveryDecision
from lyrion.persistence.sqlalchemy.models import RecoveryDecisionModel
from lyrion.persistence.sqlalchemy.recovery_store import (
    SQLAlchemyRecoveryStore,
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


def make_store(
    database_engine: AsyncEngine,
) -> SQLAlchemyRecoveryStore:
    """Create a recovery store using an independent session factory."""
    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return SQLAlchemyRecoveryStore(session_factory)


def make_decision(
    *,
    execution_id: str,
    action: RecoveryAction,
    reason: str,
    evaluated_at: datetime,
    source_revision: int,
) -> RecoveryDecision:
    """Create a valid recovery decision."""
    return RecoveryDecision(
        execution_id=execution_id,
        action=action,
        reason=reason,
        evaluated_at=evaluated_at,
        source_revision=source_revision,
    )


@pytest.mark.asyncio
async def test_record_persists_across_sessions(
    database_engine: AsyncEngine,
) -> None:
    """A recovery decision must survive a new database session."""
    decision = make_decision(
        execution_id="execution:recovery:integration",
        action=RecoveryAction.REQUEUE,
        reason="Lease expired.",
        evaluated_at=BASE_TIME,
        source_revision=3,
    )

    store = make_store(database_engine)

    result = await store.record(decision)

    assert result == decision

    decisions = await store.find_for_execution(
        decision.execution_id,
    )

    assert decisions == [decision]


@pytest.mark.asyncio
async def test_multiple_decisions_are_returned_deterministically(
    database_engine: AsyncEngine,
) -> None:
    """Recovery evidence must remain ordered by time and record id."""
    execution_id = "execution:recovery:ordered"

    first = make_decision(
        execution_id=execution_id,
        action=RecoveryAction.REQUEUE,
        reason="Claim lease expired.",
        evaluated_at=BASE_TIME,
        source_revision=2,
    )

    second = make_decision(
        execution_id=execution_id,
        action=RecoveryAction.RECONCILE,
        reason="Execution outcome requires reconciliation.",
        evaluated_at=BASE_TIME + timedelta(seconds=1),
        source_revision=3,
    )

    store = make_store(database_engine)

    await store.record(first)
    await store.record(second)

    decisions = await store.find_for_execution(
        execution_id,
    )

    assert decisions == [first, second]


@pytest.mark.asyncio
async def test_recovery_history_is_scoped_to_execution(
    database_engine: AsyncEngine,
) -> None:
    """Recovery history for another execution must not leak into results."""
    first = make_decision(
        execution_id="execution:recovery:one",
        action=RecoveryAction.REQUEUE,
        reason="Requeue one.",
        evaluated_at=BASE_TIME,
        source_revision=1,
    )

    second = make_decision(
        execution_id="execution:recovery:two",
        action=RecoveryAction.QUARANTINE,
        reason="Quarantine two.",
        evaluated_at=BASE_TIME,
        source_revision=4,
    )

    store = make_store(database_engine)

    await store.record(first)
    await store.record(second)

    result = await store.find_for_execution(
        first.execution_id,
    )

    assert result == [first]


@pytest.mark.asyncio
async def test_recovery_decision_is_stored_as_evidence(
    database_engine: AsyncEngine,
) -> None:
    """The database row must preserve action and source revision."""
    decision = make_decision(
        execution_id="execution:recovery:evidence",
        action=RecoveryAction.QUARANTINE,
        reason="Manual investigation required.",
        evaluated_at=BASE_TIME,
        source_revision=9,
    )

    store = make_store(database_engine)

    await store.record(decision)

    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        row = await session.scalar(
            select(RecoveryDecisionModel)
            .where(
                RecoveryDecisionModel.execution_id
                == decision.execution_id,
            )
            .order_by(RecoveryDecisionModel.id)
        )

    assert row is not None
    assert row.action == decision.action.value
    assert row.reason == decision.reason
    assert row.source_revision == decision.source_revision
