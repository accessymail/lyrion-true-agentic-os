"""SQLAlchemy implementation of the durable recovery store."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lyrion.persistence.contracts import RecoveryAction, RecoveryDecision
from lyrion.persistence.sqlalchemy.models import RecoveryDecisionModel


class SQLAlchemyRecoveryStore:
    """Persist explicit recovery decisions as durable evidence."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        *,
        session: AsyncSession | None = None,
    ) -> None:
        """Initialize the recovery store."""
        if (session_factory is None) == (session is None):
            raise ValueError(
                "exactly one session source is required"
            )

        self._session_factory = session_factory
        self._session = session

    @classmethod
    def _from_session(
        cls,
        session: AsyncSession,
    ) -> SQLAlchemyRecoveryStore:
        """Create a store bound to an existing transaction session."""
        return cls(session=session)

    @asynccontextmanager
    async def _read_session(
        self,
    ) -> AsyncIterator[AsyncSession]:
        """Provide a read session without owning the transaction."""
        if self._session is not None:
            yield self._session
            return

        factory = self._session_factory
        if factory is None:
            raise RuntimeError(
                "recovery store has no session factory"
            )

        async with factory() as session:
            yield session

    @asynccontextmanager
    async def _write_session(
        self,
    ) -> AsyncIterator[AsyncSession]:
        """Provide a write session with ownership-aware transaction scope."""
        if self._session is not None:
            yield self._session
            return

        factory = self._session_factory
        if factory is None:
            raise RuntimeError(
                "recovery store has no session factory"
            )

        async with factory.begin() as session:
            yield session

    async def record(
        self,
        decision: RecoveryDecision,
    ) -> RecoveryDecision:
        """Persist one recovery decision."""
        async with self._write_session() as session:
            await session.execute(
                insert(RecoveryDecisionModel).values(
                    execution_id=decision.execution_id,
                    action=decision.action.value,
                    reason=decision.reason,
                    evaluated_at=decision.evaluated_at,
                    source_revision=decision.source_revision,
                )
            )

        return decision

    async def find_for_execution(
        self,
        execution_id: str,
    ) -> list[RecoveryDecision]:
        """Return recovery decisions for one execution."""
        normalized_id = execution_id.strip()

        if not normalized_id:
            raise ValueError(
                "execution_id must not be empty",
            )

        async with self._read_session() as session:
            result = await session.execute(
                select(RecoveryDecisionModel)
                .where(
                    RecoveryDecisionModel.execution_id
                    == normalized_id,
                )
                .order_by(
                    RecoveryDecisionModel.evaluated_at,
                    RecoveryDecisionModel.id,
                )
            )

            models = result.scalars().all()

            return [
                RecoveryDecision(
                    execution_id=model.execution_id,
                    action=RecoveryAction(model.action),
                    reason=model.reason,
                    evaluated_at=model.evaluated_at,
                    source_revision=model.source_revision,
                )
                for model in models
            ]
