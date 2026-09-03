"""SQLAlchemy implementation of the durable opportunity store."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Self

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lyrion.core.types import OpportunityId
from lyrion.persistence.contracts import (
    PersistentOpportunity,
    PersistentOpportunityState,
)
from lyrion.persistence.sqlalchemy.errors import PersistenceConflictError
from lyrion.persistence.sqlalchemy.models import PersistentOpportunityModel


class SQLAlchemyOpportunityStore:
    """Persist proactive opportunity lifecycle records through SQLAlchemy."""

    _RECOVERABLE_STATES = (
        PersistentOpportunityState.CLAIMED.value,
        PersistentOpportunityState.EXECUTING.value,
        PersistentOpportunityState.UNKNOWN.value,
    )

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        *,
        session: AsyncSession | None = None,
    ) -> None:
        """Initialize the opportunity store."""
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

    def _require_session_factory(
        self,
    ) -> async_sessionmaker[AsyncSession]:
        """Return the standalone session factory."""
        factory = self._session_factory

        if factory is None:
            raise RuntimeError(
                "opportunity store has no session factory",
            )

        return factory

    @staticmethod
    def _require_aware(
        value: datetime,
        field_name: str,
    ) -> datetime:
        """Require a timezone-aware datetime."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                f"{field_name} must be timezone-aware",
            )

        return value

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

    async def create(
        self,
        opportunity: PersistentOpportunity,
    ) -> PersistentOpportunity:
        """Persist one newly queued opportunity."""
        async with self._write_session() as session:
            try:
                await session.execute(
                    insert(PersistentOpportunityModel).values(
                        opportunity_id=str(opportunity.opportunity_id),
                        state=opportunity.state.value,
                        created_at=opportunity.created_at,
                        expires_at=opportunity.expires_at,
                        worker_id=opportunity.worker_id,
                        lease_id=opportunity.lease_id,
                        claimed_at=opportunity.claimed_at,
                        completed_at=opportunity.completed_at,
                        execution_id=opportunity.execution_id,
                        revision=opportunity.revision,
                    )
                )
            except IntegrityError as exc:
                raise PersistenceConflictError(
                    "opportunity already exists",
                ) from exc

        return opportunity

    async def get(
        self,
        opportunity_id: str,
    ) -> PersistentOpportunity | None:
        """Return one durable opportunity."""
        normalized_id = opportunity_id.strip()

        if not normalized_id:
            raise ValueError(
                "opportunity_id must not be empty",
            )

        async with self._read_session() as session:
            result = await session.execute(
                select(PersistentOpportunityModel).where(
                    PersistentOpportunityModel.opportunity_id
                    == normalized_id,
                )
            )

            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_contract(model)

    async def claim(
        self,
        *,
        opportunity_id: str,
        worker_id: str,
        lease_id: str,
        claimed_at: datetime,
        expected_revision: int,
    ) -> PersistentOpportunity | None:
        """Atomically claim one queued, unexpired opportunity."""
        normalized_id = opportunity_id.strip()
        normalized_worker_id = worker_id.strip()
        normalized_lease_id = lease_id.strip()
        normalized_claimed_at = self._require_aware(
            claimed_at,
            "claimed_at",
        )

        if not normalized_id:
            raise ValueError(
                "opportunity_id must not be empty",
            )

        if not normalized_worker_id:
            raise ValueError(
                "worker_id must not be empty",
            )

        if not normalized_lease_id:
            raise ValueError(
                "lease_id must not be empty",
            )

        if expected_revision < 1:
            raise ValueError(
                "expected_revision must be positive",
            )

        async with self._write_session() as session:
            result = await session.execute(
                update(PersistentOpportunityModel)
                .where(
                    PersistentOpportunityModel.opportunity_id
                    == normalized_id,
                    PersistentOpportunityModel.state
                    == PersistentOpportunityState.QUEUED.value,
                    PersistentOpportunityModel.revision
                    == expected_revision,
                    (
                        PersistentOpportunityModel.expires_at.is_(None)
                        | (
                            PersistentOpportunityModel.expires_at
                            > normalized_claimed_at
                        )
                    ),
                )
                .values(
                    state=PersistentOpportunityState.CLAIMED.value,
                    worker_id=normalized_worker_id,
                    lease_id=normalized_lease_id,
                    claimed_at=normalized_claimed_at,
                    revision=expected_revision + 1,
                )
                .returning(PersistentOpportunityModel)
            )

            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_contract(model)

    async def transition(
        self,
        *,
        opportunity_id: str,
        worker_id: str,
        lease_id: str,
        expected_revision: int,
        target_state: PersistentOpportunityState,
        occurred_at: datetime,
        execution_id: str | None = None,
    ) -> PersistentOpportunity:
        """Atomically advance one owned opportunity."""
        normalized_id = opportunity_id.strip()
        normalized_worker_id = worker_id.strip()
        normalized_lease_id = lease_id.strip()
        normalized_occurred_at = self._require_aware(
            occurred_at,
            "occurred_at",
        )

        if not normalized_id:
            raise ValueError(
                "opportunity_id must not be empty",
            )

        if not normalized_worker_id:
            raise ValueError(
                "worker_id must not be empty",
            )

        if not normalized_lease_id:
            raise ValueError(
                "lease_id must not be empty",
            )

        if expected_revision < 1:
            raise ValueError(
                "expected_revision must be positive",
            )

        if (
            target_state is PersistentOpportunityState.EXECUTING
            and execution_id is None
        ):
            raise ValueError(
                "EXECUTING transition requires execution_id",
            )

        values: dict[str, object] = {
            "state": target_state.value,
            "revision": expected_revision + 1,
        }

        if target_state is PersistentOpportunityState.CLAIMED:
            values["claimed_at"] = normalized_occurred_at

        if target_state is PersistentOpportunityState.EXECUTING:
            values["execution_id"] = execution_id

        if target_state in {
            PersistentOpportunityState.COMPLETED,
            PersistentOpportunityState.FAILED,
            PersistentOpportunityState.CANCELLED,
            PersistentOpportunityState.ABANDONED,
        }:
            values["completed_at"] = normalized_occurred_at

        async with self._write_session() as session:
            result = await session.execute(
                update(PersistentOpportunityModel)
                .where(
                    PersistentOpportunityModel.opportunity_id
                    == normalized_id,
                    PersistentOpportunityModel.worker_id
                    == normalized_worker_id,
                    PersistentOpportunityModel.lease_id
                    == normalized_lease_id,
                    PersistentOpportunityModel.revision
                    == expected_revision,
                )
                .values(**values)
                .returning(PersistentOpportunityModel)
            )

            model = result.scalar_one_or_none()

            if model is None:
                raise PersistenceConflictError(
                    "opportunity transition conflict",
                )

            return self._to_contract(model)

    async def find_claimable(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> list[PersistentOpportunity]:
        """Return bounded, unexpired queued opportunities."""
        normalized_now = self._require_aware(now, "now")

        if limit < 1:
            raise ValueError(
                "limit must be positive",
            )

        async with self._read_session() as session:
            result = await session.execute(
                select(PersistentOpportunityModel)
                .where(
                    PersistentOpportunityModel.state
                    == PersistentOpportunityState.QUEUED.value,
                    (
                        PersistentOpportunityModel.expires_at.is_(None)
                        | (
                            PersistentOpportunityModel.expires_at
                            > normalized_now
                        )
                    ),
                )
                .order_by(
                    PersistentOpportunityModel.created_at,
                    PersistentOpportunityModel.opportunity_id,
                )
                .limit(limit)
            )

            models = result.scalars().all()

            return [
                self._to_contract(model)
                for model in models
            ]

    async def find_recoverable(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> list[PersistentOpportunity]:
        """Return bounded opportunities requiring recovery."""
        normalized_now = self._require_aware(now, "now")

        if limit < 1:
            raise ValueError(
                "limit must be positive",
            )

        async with self._read_session() as session:
            result = await session.execute(
                select(PersistentOpportunityModel)
                .where(
                    PersistentOpportunityModel.state.in_(
                        self._RECOVERABLE_STATES,
                    ),
                    PersistentOpportunityModel.created_at
                    <= normalized_now,
                )
                .order_by(
                    PersistentOpportunityModel.created_at,
                    PersistentOpportunityModel.opportunity_id,
                )
                .limit(limit)
            )

            models = result.scalars().all()

            return [
                self._to_contract(model)
                for model in models
            ]

    @staticmethod
    def _to_contract(
        model: PersistentOpportunityModel,
    ) -> PersistentOpportunity:
        """Convert one ORM row into the domain contract."""
        return PersistentOpportunity(
            opportunity_id=OpportunityId(model.opportunity_id),
            state=PersistentOpportunityState(model.state),
            created_at=model.created_at,
            expires_at=model.expires_at,
            worker_id=model.worker_id,
            lease_id=model.lease_id,
            claimed_at=model.claimed_at,
            completed_at=model.completed_at,
            execution_id=model.execution_id,
            revision=model.revision,
        )
