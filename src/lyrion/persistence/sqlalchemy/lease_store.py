"""SQLAlchemy implementation of the durable lease store."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lyrion.persistence.contracts import RuntimeLease
from lyrion.persistence.sqlalchemy.errors import PersistenceConflictError
from lyrion.persistence.sqlalchemy.models import RuntimeLeaseModel


class SQLAlchemyLeaseStore:
    """Persist exclusive runtime-resource leases through SQLAlchemy."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        *,
        session: AsyncSession | None = None,
    ) -> None:
        """Initialize the lease store."""
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
    ) -> SQLAlchemyLeaseStore:
        """Create a store bound to an existing transaction session."""
        return cls(session=session)

    @asynccontextmanager
    async def _read_session(self) -> AsyncIterator[AsyncSession]:
        """Provide a read session without owning the transaction."""
        if self._session is not None:
            yield self._session
            return

        assert self._session_factory is not None

        async with self._session_factory() as session:
            yield session

    @asynccontextmanager
    async def _write_session(self) -> AsyncIterator[AsyncSession]:
        """Provide a write session with ownership-aware transaction scope."""
        if self._session is not None:
            yield self._session
            return

        assert self._session_factory is not None

        async with self._session_factory.begin() as session:
            yield session

    async def acquire(
        self,
        *,
        resource_id: str,
        worker_id: str,
        lease_id: str,
        acquired_at: datetime,
        expires_at: datetime,
    ) -> RuntimeLease | None:
        """Atomically acquire an unowned or expired resource."""
        normalized_resource_id = resource_id.strip()
        normalized_worker_id = worker_id.strip()
        normalized_lease_id = lease_id.strip()

        if not normalized_resource_id:
            raise ValueError("resource_id must not be empty")
        if not normalized_worker_id:
            raise ValueError("worker_id must not be empty")
        if not normalized_lease_id:
            raise ValueError("lease_id must not be empty")

        candidate = RuntimeLease(
            lease_id=normalized_lease_id,
            resource_id=normalized_resource_id,
            worker_id=normalized_worker_id,
            acquired_at=acquired_at,
            expires_at=expires_at,
            revision=1,
        )

        statement = (
            insert(RuntimeLeaseModel)
            .values(
                lease_id=candidate.lease_id,
                resource_id=candidate.resource_id,
                worker_id=candidate.worker_id,
                acquired_at=candidate.acquired_at,
                expires_at=candidate.expires_at,
                revision=candidate.revision,
            )
            .on_conflict_do_update(
                index_elements=[RuntimeLeaseModel.resource_id],
                set_={
                    "lease_id": candidate.lease_id,
                    "worker_id": candidate.worker_id,
                    "acquired_at": candidate.acquired_at,
                    "expires_at": candidate.expires_at,
                    "revision": RuntimeLeaseModel.revision + 1,
                },
                where=RuntimeLeaseModel.expires_at <= acquired_at,
            )
            .returning(
                RuntimeLeaseModel.lease_id,
                RuntimeLeaseModel.resource_id,
                RuntimeLeaseModel.worker_id,
                RuntimeLeaseModel.acquired_at,
                RuntimeLeaseModel.expires_at,
                RuntimeLeaseModel.revision,
            )
        )

        async with self._write_session() as session:
            result = await session.execute(statement)
            row = result.first()

            if row is None:
                return None

            return RuntimeLease(
                lease_id=row.lease_id,
                resource_id=row.resource_id,
                worker_id=row.worker_id,
                acquired_at=row.acquired_at,
                expires_at=row.expires_at,
                revision=row.revision,
            )

    async def get(
        self,
        resource_id: str,
    ) -> RuntimeLease | None:
        """Return the current lease for a resource."""
        normalized_resource_id = resource_id.strip()

        if not normalized_resource_id:
            raise ValueError("resource_id must not be empty")

        async with self._read_session() as session:
            result = await session.execute(
                select(RuntimeLeaseModel).where(
                    RuntimeLeaseModel.resource_id
                    == normalized_resource_id,
                )
            )
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return RuntimeLease(
                lease_id=model.lease_id,
                resource_id=model.resource_id,
                worker_id=model.worker_id,
                acquired_at=model.acquired_at,
                expires_at=model.expires_at,
                revision=model.revision,
            )

    async def renew(
        self,
        *,
        lease_id: str,
        worker_id: str,
        expected_revision: int,
        expires_at: datetime,
    ) -> RuntimeLease:
        """Atomically renew a lease owned by the worker."""
        normalized_lease_id = lease_id.strip()
        normalized_worker_id = worker_id.strip()

        if not normalized_lease_id:
            raise ValueError("lease_id must not be empty")
        if not normalized_worker_id:
            raise ValueError("worker_id must not be empty")
        if expected_revision < 1:
            raise ValueError(
                "expected_revision must be positive"
            )

        async with self._write_session() as session:
            result = await session.execute(
                update(RuntimeLeaseModel)
                .where(
                    RuntimeLeaseModel.lease_id
                    == normalized_lease_id,
                    RuntimeLeaseModel.worker_id
                    == normalized_worker_id,
                    RuntimeLeaseModel.revision
                    == expected_revision,
                    RuntimeLeaseModel.expires_at
                    < expires_at,
                )
                .values(
                    expires_at=expires_at,
                    revision=expected_revision + 1,
                )
                .returning(
                    RuntimeLeaseModel.lease_id,
                    RuntimeLeaseModel.resource_id,
                    RuntimeLeaseModel.worker_id,
                    RuntimeLeaseModel.acquired_at,
                    RuntimeLeaseModel.expires_at,
                    RuntimeLeaseModel.revision,
                )
            )

            row = result.first()

            if row is None:
                raise PersistenceConflictError(
                    "lease renewal conflict"
                )

            return RuntimeLease(
                lease_id=row.lease_id,
                resource_id=row.resource_id,
                worker_id=row.worker_id,
                acquired_at=row.acquired_at,
                expires_at=row.expires_at,
                revision=row.revision,
            )

    async def release(
        self,
        *,
        lease_id: str,
        worker_id: str,
    ) -> None:
        """Release a lease owned by the worker."""
        normalized_lease_id = lease_id.strip()
        normalized_worker_id = worker_id.strip()

        if not normalized_lease_id:
            raise ValueError("lease_id must not be empty")
        if not normalized_worker_id:
            raise ValueError("worker_id must not be empty")

        async with self._write_session() as session:
            await session.execute(
                delete(RuntimeLeaseModel).where(
                    RuntimeLeaseModel.lease_id
                    == normalized_lease_id,
                    RuntimeLeaseModel.worker_id
                    == normalized_worker_id,
                )
            )

    async def find_expired(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> list[RuntimeLease]:
        """Return expired leases up to an explicit bound."""
        if limit < 1:
            raise ValueError("limit must be positive")

        async with self._read_session() as session:
            result = await session.execute(
                select(RuntimeLeaseModel)
                .where(
                    RuntimeLeaseModel.expires_at <= now,
                )
                .order_by(
                    RuntimeLeaseModel.expires_at,
                    RuntimeLeaseModel.lease_id,
                )
                .limit(limit)
            )

            models = result.scalars().all()

            return [
                RuntimeLease(
                    lease_id=model.lease_id,
                    resource_id=model.resource_id,
                    worker_id=model.worker_id,
                    acquired_at=model.acquired_at,
                    expires_at=model.expires_at,
                    revision=model.revision,
                )
                for model in models
            ]
