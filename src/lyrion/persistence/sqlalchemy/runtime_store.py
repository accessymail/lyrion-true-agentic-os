"""SQLAlchemy implementation of the durable runtime store."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from sqlalchemy import insert, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lyrion.persistence.contracts import (
    RuntimeInstance,
    RuntimeLifecycleState,
)
from lyrion.persistence.sqlalchemy.errors import PersistenceConflictError
from lyrion.persistence.sqlalchemy.models import RuntimeInstanceModel


class SQLAlchemyRuntimeStore:
    """Persist runtime lifecycle records through SQLAlchemy."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        *,
        session: AsyncSession | None = None,
    ) -> None:
        """Initialize the runtime store."""
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
    ) -> SQLAlchemyRuntimeStore:
        """Create a store bound to an existing transaction session."""
        return cls(session=session)

    @asynccontextmanager
    async def _read_session(self) -> AsyncIterator[AsyncSession]:
        """Provide a session without creating a transaction."""
        if self._session is not None:
            yield self._session
            return

        assert self._session_factory is not None

        async with self._session_factory() as session:
            yield session

    @asynccontextmanager
    async def _write_session(self) -> AsyncIterator[AsyncSession]:
        """Provide a writable session with ownership-aware transaction scope."""
        if self._session is not None:
            yield self._session
            return

        assert self._session_factory is not None

        async with self._session_factory.begin() as session:
            yield session

    async def get(
        self,
        instance_id: str,
    ) -> RuntimeInstance | None:
        """Return one runtime instance by identifier."""
        normalized_id = instance_id.strip()

        if not normalized_id:
            raise ValueError("instance_id must not be empty")

        async with self._read_session() as session:
            result = await session.execute(
                select(RuntimeInstanceModel).where(
                    RuntimeInstanceModel.instance_id == normalized_id,
                )
            )
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return RuntimeInstance(
                instance_id=model.instance_id,
                state=RuntimeLifecycleState(model.state),
                started_at=model.started_at,
                heartbeat_at=model.heartbeat_at,
                revision=model.revision,
            )

    async def save(
        self,
        instance: RuntimeInstance,
    ) -> RuntimeInstance:
        """Insert a new runtime instance."""
        if self._session is not None:
            try:
                async with self._session.begin_nested():
                    await self._session.execute(
                        insert(RuntimeInstanceModel).values(
                            instance_id=instance.instance_id,
                            state=instance.state.value,
                            started_at=instance.started_at,
                            heartbeat_at=instance.heartbeat_at,
                            revision=instance.revision,
                        )
                    )
            except IntegrityError as exc:
                raise PersistenceConflictError(
                    "runtime instance already exists"
                ) from exc

            return instance

        async with self._write_session() as session:
            try:
                await session.execute(
                    insert(RuntimeInstanceModel).values(
                        instance_id=instance.instance_id,
                        state=instance.state.value,
                        started_at=instance.started_at,
                        heartbeat_at=instance.heartbeat_at,
                        revision=instance.revision,
                    )
                )
            except IntegrityError as exc:
                raise PersistenceConflictError(
                    "runtime instance already exists"
                ) from exc

        return instance

    async def transition(
        self,
        instance_id: str,
        *,
        expected_revision: int,
        state: RuntimeInstance,
    ) -> RuntimeInstance:
        """Atomically update runtime state using optimistic concurrency."""
        normalized_id = instance_id.strip()

        if not normalized_id:
            raise ValueError("instance_id must not be empty")

        if state.instance_id != normalized_id:
            raise ValueError(
                "state.instance_id must match instance_id"
            )

        if expected_revision < 1:
            raise ValueError(
                "expected_revision must be positive"
            )

        next_revision = expected_revision + 1

        async with self._write_session() as session:
            result = await session.execute(
                update(RuntimeInstanceModel)
                .where(
                    RuntimeInstanceModel.instance_id == normalized_id,
                    RuntimeInstanceModel.revision == expected_revision,
                )
                .values(
                    state=state.state.value,
                    started_at=state.started_at,
                    heartbeat_at=state.heartbeat_at,
                    revision=next_revision,
                )
            )

            cursor_result = cast(
                CursorResult[Any],
                result,
            )

            if cursor_result.rowcount != 1:
                raise PersistenceConflictError(
                    "runtime revision conflict"
                )

        return RuntimeInstance(
            instance_id=state.instance_id,
            state=state.state,
            started_at=state.started_at,
            heartbeat_at=state.heartbeat_at,
            revision=next_revision,
        )
