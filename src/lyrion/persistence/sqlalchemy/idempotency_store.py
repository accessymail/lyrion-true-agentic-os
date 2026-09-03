"""SQLAlchemy implementation of the durable idempotency store."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lyrion.persistence.contracts import PersistentIdempotencyRecord
from lyrion.persistence.sqlalchemy.models import PersistentIdempotencyModel


class SQLAlchemyIdempotencyStore:
    """Persist cross-restart idempotency reservations."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        *,
        session: AsyncSession | None = None,
    ) -> None:
        """Initialize the idempotency store."""
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
    ) -> SQLAlchemyIdempotencyStore:
        """Create a store bound to an existing transaction session."""
        return cls(session=session)

    def _require_session_factory(
        self,
    ) -> async_sessionmaker[AsyncSession]:
        """Return the standalone session factory or fail clearly."""
        factory = self._session_factory

        if factory is None:
            raise RuntimeError(
                "idempotency store has no session factory"
            )

        return factory

    @asynccontextmanager
    async def _read_session(
        self,
    ) -> AsyncIterator[AsyncSession]:
        """Provide a read session without owning the transaction."""
        if self._session is not None:
            yield self._session
            return

        factory = self._require_session_factory()

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

        factory = self._require_session_factory()

        async with factory.begin() as session:
            yield session

    async def reserve(
        self,
        record: PersistentIdempotencyRecord,
    ) -> bool:
        """Atomically reserve one idempotency key."""
        statement = (
            insert(PersistentIdempotencyModel)
            .values(
                idempotency_key=record.idempotency_key,
                request_id=record.request_id,
                execution_id=record.execution_id,
                reserved_at=record.reserved_at,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    PersistentIdempotencyModel.idempotency_key,
                ],
            )
            .returning(
                PersistentIdempotencyModel.idempotency_key,
            )
        )

        async with self._write_session() as session:
            result = await session.execute(statement)
            return result.first() is not None

    async def get(
        self,
        idempotency_key: str,
    ) -> PersistentIdempotencyRecord | None:
        """Return the durable record associated with a key."""
        normalized_key = idempotency_key.strip()

        if not normalized_key:
            raise ValueError(
                "idempotency_key must not be empty",
            )

        async with self._read_session() as session:
            result = await session.execute(
                select(PersistentIdempotencyModel).where(
                    PersistentIdempotencyModel.idempotency_key
                    == normalized_key,
                )
            )

            model = result.scalar_one_or_none()

            if model is None:
                return None

            return PersistentIdempotencyRecord(
                idempotency_key=model.idempotency_key,
                request_id=model.request_id,
                execution_id=model.execution_id,
                reserved_at=model.reserved_at,
            )

    async def contains(
        self,
        idempotency_key: str,
    ) -> bool:
        """Return whether an idempotency key is registered."""
        normalized_key = idempotency_key.strip()

        if not normalized_key:
            raise ValueError(
                "idempotency_key must not be empty",
            )

        async with self._read_session() as session:
            result = await session.execute(
                select(PersistentIdempotencyModel.idempotency_key)
                .where(
                    PersistentIdempotencyModel.idempotency_key
                    == normalized_key,
                )
                .limit(1)
            )

            return result.first() is not None
