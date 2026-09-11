"""SQLAlchemy implementation of the durable scheduler store."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Self

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lyrion.persistence.contracts import (
    PersistentScheduler,
    PersistentSchedulerState,
)
from lyrion.persistence.sqlalchemy.errors import PersistenceConflictError
from lyrion.persistence.sqlalchemy.models import PersistentSchedulerModel


class SQLAlchemySchedulerStore:
    """Persist proactive scheduler lifecycle state through SQLAlchemy."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        *,
        session: AsyncSession | None = None,
    ) -> None:
        """Initialize the scheduler store."""
        if (session_factory is None) == (session is None):
            raise ValueError(
                "exactly one session source is required",
            )

        self._session_factory = session_factory
        self._session = session

    @classmethod
    def _from_session(
        cls,
        session: AsyncSession,
    ) -> Self:
        """Create a store bound to an existing transaction session."""
        return cls(session=session)

    @asynccontextmanager
    async def _read_session(
        self,
    ) -> AsyncIterator[AsyncSession]:
        """Provide a session without creating a transaction."""
        if self._session is not None:
            yield self._session
            return

        assert self._session_factory is not None

        async with self._session_factory() as session:
            yield session

    @asynccontextmanager
    async def _write_session(
        self,
    ) -> AsyncIterator[AsyncSession]:
        """Provide a writable session with ownership-aware transaction scope."""
        if self._session is not None:
            yield self._session
            return

        assert self._session_factory is not None

        async with self._session_factory.begin() as session:
            yield session

    async def get(
        self,
        scheduler_id: str,
    ) -> PersistentScheduler | None:
        """Return one durable scheduler state."""
        normalized_id = scheduler_id.strip()

        if not normalized_id:
            raise ValueError(
                "scheduler_id must not be empty",
            )

        async with self._read_session() as session:
            result = await session.execute(
                select(PersistentSchedulerModel).where(
                    PersistentSchedulerModel.scheduler_id
                    == normalized_id,
                )
            )

            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_contract(model)

    async def save(
        self,
        scheduler: PersistentScheduler,
    ) -> PersistentScheduler:
        """Insert one new durable scheduler state."""
        async with self._write_session() as session:
            try:
                await session.execute(
                    insert(PersistentSchedulerModel).values(
                        scheduler_id=scheduler.scheduler_id,
                        state=scheduler.state.value,
                        next_run_at=scheduler.next_run_at,
                        revision=scheduler.revision,
                    )
                )
            except IntegrityError as exc:
                raise PersistenceConflictError(
                    "scheduler already exists",
                ) from exc

        return scheduler

    async def transition(
        self,
        scheduler_id: str,
        *,
        expected_revision: int,
        state: PersistentSchedulerState,
        next_run_at: datetime | None,
    ) -> PersistentScheduler:
        """Atomically persist one scheduler state transition."""
        normalized_id = scheduler_id.strip()

        if not normalized_id:
            raise ValueError(
                "scheduler_id must not be empty",
            )

        if expected_revision < 1:
            raise ValueError(
                "expected_revision must be positive",
            )

        async with self._write_session() as session:
            result = await session.execute(
                update(PersistentSchedulerModel)
                .where(
                    PersistentSchedulerModel.scheduler_id
                    == normalized_id,
                    PersistentSchedulerModel.revision
                    == expected_revision,
                )
                .values(
                    state=state.value,
                    next_run_at=next_run_at,
                    revision=expected_revision + 1,
                )
                .returning(PersistentSchedulerModel)
            )

            model = result.scalar_one_or_none()

            if model is None:
                raise PersistenceConflictError(
                    "scheduler revision conflict",
                )

            return self._to_contract(model)

    @staticmethod
    def _to_contract(
        model: PersistentSchedulerModel,
    ) -> PersistentScheduler:
        """Convert one ORM row into the persistence contract."""
        return PersistentScheduler(
            scheduler_id=model.scheduler_id,
            state=PersistentSchedulerState(model.state),
            next_run_at=model.next_run_at,
            revision=model.revision,
        )
