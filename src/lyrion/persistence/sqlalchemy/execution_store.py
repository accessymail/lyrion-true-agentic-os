"""SQLAlchemy implementation of the durable execution store."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lyrion.core.types import (
    IdempotencyKey,
    OpportunityId,
    TaskId,
)
from lyrion.persistence.contracts import (
    PersistentExecutionRecord,
    PersistentExecutionState,
)
from lyrion.persistence.sqlalchemy.errors import PersistenceConflictError
from lyrion.persistence.sqlalchemy.models import PersistentExecutionModel


class SQLAlchemyExecutionStore:
    """Persist execution lifecycle records through SQLAlchemy."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        *,
        session: AsyncSession | None = None,
    ) -> None:
        """Initialize the execution store."""
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
    ) -> SQLAlchemyExecutionStore:
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

        assert self._session_factory is not None

        async with self._session_factory() as session:
            yield session

    @asynccontextmanager
    async def _write_session(
        self,
    ) -> AsyncIterator[AsyncSession]:
        """Provide a write session with ownership-aware transaction scope."""
        if self._session is not None:
            yield self._session
            return

        assert self._session_factory is not None

        async with self._session_factory.begin() as session:
            yield session

    async def create(
        self,
        record: PersistentExecutionRecord,
    ) -> PersistentExecutionRecord:
        """Create a new execution record."""
        async with self._write_session() as session:
            try:
                await session.execute(
                    insert(PersistentExecutionModel).values(
                        execution_id=record.execution_id,
                        request_id=record.request_id,
                        opportunity_id=str(record.opportunity_id),
                        task_id=str(record.task_id),
                        idempotency_key=str(record.idempotency_key),
                        state=record.state.value,
                        created_at=record.created_at,
                        claimed_at=record.claimed_at,
                        started_at=record.started_at,
                        completed_at=record.completed_at,
                        worker_id=record.worker_id,
                        lease_id=record.lease_id,
                        checkpoint_ref=record.checkpoint_ref,
                        error_code=record.error_code,
                        error_message=record.error_message,
                        revision=record.revision,
                    )
                )
            except IntegrityError as exc:
                raise PersistenceConflictError(
                    "execution record already exists",
                ) from exc

        return record

    async def get(
        self,
        execution_id: str,
    ) -> PersistentExecutionRecord | None:
        """Return one execution record."""
        normalized_id = execution_id.strip()

        if not normalized_id:
            raise ValueError("execution_id must not be empty")

        async with self._read_session() as session:
            result = await session.execute(
                select(PersistentExecutionModel).where(
                    PersistentExecutionModel.execution_id
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
        execution_id: str,
        worker_id: str,
        lease_id: str,
        claimed_at: datetime,
        expected_revision: int,
    ) -> PersistentExecutionRecord | None:
        """Atomically claim one queued execution."""
        normalized_id = execution_id.strip()
        normalized_worker_id = worker_id.strip()
        normalized_lease_id = lease_id.strip()

        if not normalized_id:
            raise ValueError("execution_id must not be empty")
        if not normalized_worker_id:
            raise ValueError("worker_id must not be empty")
        if not normalized_lease_id:
            raise ValueError("lease_id must not be empty")
        if expected_revision < 1:
            raise ValueError(
                "expected_revision must be positive",
            )

        async with self._write_session() as session:
            result = await session.execute(
                update(PersistentExecutionModel)
                .where(
                    PersistentExecutionModel.execution_id
                    == normalized_id,
                    PersistentExecutionModel.state
                    == PersistentExecutionState.QUEUED.value,
                    PersistentExecutionModel.revision
                    == expected_revision,
                )
                .values(
                    state=PersistentExecutionState.CLAIMED.value,
                    claimed_at=claimed_at,
                    worker_id=normalized_worker_id,
                    lease_id=normalized_lease_id,
                    revision=expected_revision + 1,
                )
                .returning(PersistentExecutionModel)
            )

            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_contract(model)

    async def transition(
        self,
        *,
        execution_id: str,
        worker_id: str,
        lease_id: str,
        expected_revision: int,
        target_state: PersistentExecutionState,
        occurred_at: datetime,
        checkpoint_ref: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> PersistentExecutionRecord:
        """Atomically advance an owned execution lifecycle."""
        normalized_id = execution_id.strip()
        normalized_worker_id = worker_id.strip()
        normalized_lease_id = lease_id.strip()

        if not normalized_id:
            raise ValueError("execution_id must not be empty")
        if not normalized_worker_id:
            raise ValueError("worker_id must not be empty")
        if not normalized_lease_id:
            raise ValueError("lease_id must not be empty")
        if expected_revision < 1:
            raise ValueError(
                "expected_revision must be positive",
            )

        values: dict[str, object] = {
            "state": target_state.value,
            "revision": expected_revision + 1,
        }

        if target_state is PersistentExecutionState.EXECUTING:
            values["started_at"] = occurred_at

        if target_state in {
            PersistentExecutionState.COMPLETED,
            PersistentExecutionState.FAILED,
            PersistentExecutionState.CANCELLED,
            PersistentExecutionState.ABANDONED,
        }:
            values["completed_at"] = occurred_at

        if checkpoint_ref is not None:
            values["checkpoint_ref"] = checkpoint_ref

        if error_code is not None:
            values["error_code"] = error_code

        if error_message is not None:
            values["error_message"] = error_message

        async with self._write_session() as session:
            result = await session.execute(
                update(PersistentExecutionModel)
                .where(
                    PersistentExecutionModel.execution_id
                    == normalized_id,
                    PersistentExecutionModel.worker_id
                    == normalized_worker_id,
                    PersistentExecutionModel.lease_id
                    == normalized_lease_id,
                    PersistentExecutionModel.revision
                    == expected_revision,
                )
                .values(**values)
                .returning(PersistentExecutionModel)
            )

            model = result.scalar_one_or_none()

            if model is None:
                raise PersistenceConflictError(
                    "execution transition conflict",
                )

            return self._to_contract(model)

    async def requeue(
        self,
        *,
        execution_id: str,
        expected_revision: int,
        occurred_at: datetime,
    ) -> PersistentExecutionRecord:
        """Return a recoverable execution to QUEUED."""
        normalized_id = execution_id.strip()

        if not normalized_id:
            raise ValueError(
                "execution_id must not be empty"
            )

        if expected_revision < 1:
            raise ValueError(
                "expected_revision must be positive"
            )

        if (
            occurred_at.tzinfo is None
            or occurred_at.utcoffset() is None
        ):
            raise ValueError(
                "occurred_at must be timezone-aware"
            )

        async with self._write_session() as session:
            result = await session.execute(
                update(PersistentExecutionModel)
                .where(
                    PersistentExecutionModel.execution_id
                    == normalized_id,
                    PersistentExecutionModel.state
                    == PersistentExecutionState.CLAIMED.value,
                    PersistentExecutionModel.revision
                    == expected_revision,
                )
                .values(
                    state=PersistentExecutionState.QUEUED.value,
                    worker_id=None,
                    lease_id=None,
                    claimed_at=None,
                    revision=expected_revision + 1,
                )
                .returning(PersistentExecutionModel)
            )

            model = result.scalar_one_or_none()

            if model is None:
                raise PersistenceConflictError(
                    "execution requeue conflict"
                )

            return self._to_contract(model)

    async def find_recoverable(
        self,
        *,
        states: Sequence[PersistentExecutionState],
        now: datetime,
        limit: int,
    ) -> list[PersistentExecutionRecord]:
        """Return bounded execution records requiring recovery."""
        if not states:
            raise ValueError("states must not be empty")

        if limit < 1:
            raise ValueError("limit must be positive")

        state_values = tuple(state.value for state in states)

        async with self._read_session() as session:
            result = await session.execute(
                select(PersistentExecutionModel)
                .where(
                    PersistentExecutionModel.state.in_(state_values),
                    PersistentExecutionModel.created_at <= now,
                )
                .order_by(
                    PersistentExecutionModel.created_at,
                    PersistentExecutionModel.execution_id,
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
        model: PersistentExecutionModel,
    ) -> PersistentExecutionRecord:
        """Convert one ORM row into the domain persistence contract."""
        return PersistentExecutionRecord(
            execution_id=model.execution_id,
            request_id=model.request_id,
            opportunity_id=OpportunityId(model.opportunity_id),
            task_id=TaskId(model.task_id),
            idempotency_key=IdempotencyKey(model.idempotency_key),
            state=PersistentExecutionState(model.state),
            created_at=model.created_at,
            claimed_at=model.claimed_at,
            started_at=model.started_at,
            completed_at=model.completed_at,
            worker_id=model.worker_id,
            lease_id=model.lease_id,
            checkpoint_ref=model.checkpoint_ref,
            error_code=model.error_code,
            error_message=model.error_message,
            revision=model.revision,
        )
