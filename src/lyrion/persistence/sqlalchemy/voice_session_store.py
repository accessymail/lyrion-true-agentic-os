"""SQLAlchemy implementation of durable Lyrion voice-session continuity."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from sqlalchemy import insert, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lyrion.persistence.sqlalchemy.errors import PersistenceConflictError
from lyrion.persistence.sqlalchemy.models import (
    PersistentVoiceSessionModel,
    PersistentVoiceTurnModel,
)
from lyrion.voice.session.contracts import (
    VoiceSession,
    VoiceSessionError,
    VoiceSessionErrorCode,
    VoiceSessionState,
    VoiceTurn,
    VoiceTurnStatus,
)
from lyrion.voice.session.in_memory_store import (
    VoiceSessionStoreError,
)
from lyrion.voice.session.store import VoiceSessionStore


class SQLAlchemyVoiceSessionStore(VoiceSessionStore):
    """Persist logical voice sessions and turns through SQLAlchemy."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        *,
        session: AsyncSession | None = None,
    ) -> None:
        """Initialize the store with exactly one session source."""
        if (session_factory is None) == (session is None):
            raise ValueError("exactly one session source is required")

        self._session_factory = session_factory
        self._session = session

    @classmethod
    def _from_session(
        cls,
        session: AsyncSession,
    ) -> SQLAlchemyVoiceSessionStore:
        """Create a store bound to an existing transaction session."""
        return cls(session=session)

    @asynccontextmanager
    async def _read_session(self) -> AsyncIterator[AsyncSession]:
        """Provide a read session."""
        if self._session is not None:
            yield self._session
            return

        assert self._session_factory is not None

        async with self._session_factory() as session:
            yield session

    @asynccontextmanager
    async def _write_session(self) -> AsyncIterator[AsyncSession]:
        """Provide an ownership-aware write transaction."""
        if self._session is not None:
            yield self._session
            return

        assert self._session_factory is not None

        async with self._session_factory.begin() as session:
            yield session

    async def create(
        self,
        session: VoiceSession,
    ) -> VoiceSession:
        """Atomically create one durable voice session."""
        async with self._write_session() as db_session:
            try:
                await db_session.execute(
                    insert(PersistentVoiceSessionModel).values(
                        session_id=session.session_id,
                        correlation_id=session.correlation_id,
                        state=session.state.value,
                        session_revision=session.session_revision,
                        next_turn_sequence=session.next_turn_sequence,
                        created_at=session.created_at,
                        last_activity_at=session.last_activity_at,
                        expires_at=session.expires_at,
                        resumable_until=session.resumable_until,
                        continuity_version=session.continuity_version,
                    )
                )
            except IntegrityError as exc:
                raise PersistenceConflictError(
                    "voice session already exists"
                ) from exc

        return session

    async def get(
        self,
        session_id: str,
    ) -> VoiceSession | None:
        """Return one durable voice session by ID."""
        normalized_id = session_id.strip()

        if not normalized_id:
            raise ValueError("session_id must not be empty")

        async with self._read_session() as db_session:
            result = await db_session.execute(
                select(PersistentVoiceSessionModel).where(
                    PersistentVoiceSessionModel.session_id
                    == normalized_id
                )
            )
            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_session(model)

    async def save(
        self,
        session: VoiceSession,
        *,
        expected_revision: int,
    ) -> VoiceSession:
        """Persist one revision-checked session update atomically."""
        if expected_revision < 0:
            raise ValueError("expected_revision must be >= 0")

        if session.session_revision != expected_revision + 1:
            raise ValueError(
                "session revision must advance by exactly one"
            )

        async with self._write_session() as db_session:
            result = await db_session.execute(
                update(PersistentVoiceSessionModel)
                .where(
                    PersistentVoiceSessionModel.session_id
                    == session.session_id,
                    PersistentVoiceSessionModel.session_revision
                    == expected_revision,
                )
                .values(
                    correlation_id=session.correlation_id,
                    state=session.state.value,
                    session_revision=session.session_revision,
                    next_turn_sequence=session.next_turn_sequence,
                    created_at=session.created_at,
                    last_activity_at=session.last_activity_at,
                    expires_at=session.expires_at,
                    resumable_until=session.resumable_until,
                    continuity_version=session.continuity_version,
                )
            )

            cursor_result = cast(CursorResult[Any], result)

            if cursor_result.rowcount != 1:
                raise PersistenceConflictError(
                    "voice session revision conflict"
                )

        return session

    async def append_turn(
        self,
        turn: VoiceTurn,
        *,
        expected_session_revision: int,
    ) -> VoiceSession:
        """
        Atomically append a turn and advance session continuity.

        The guarded session update acquires the PostgreSQL row lock before
        the turn insert. Concurrent writers therefore cannot both advance
        the same session revision/sequence.
        """
        if expected_session_revision < 0:
            raise ValueError(
                "expected_session_revision must be >= 0"
            )

        async with self._write_session() as db_session:
            session_update = await db_session.execute(
                update(PersistentVoiceSessionModel)
                .where(
                    PersistentVoiceSessionModel.session_id
                    == turn.session_id,
                    PersistentVoiceSessionModel.session_revision
                    == expected_session_revision,
                    PersistentVoiceSessionModel.next_turn_sequence
                    == turn.sequence,
                )
                .values(
                    session_revision=expected_session_revision + 1,
                    next_turn_sequence=turn.sequence + 1,
                    last_activity_at=turn.created_at,
                )
            )

            cursor_result = cast(
                CursorResult[Any],
                session_update,
            )

            if cursor_result.rowcount != 1:
                raise PersistenceConflictError(
                    "voice session revision or turn sequence conflict"
                )

            try:
                await db_session.execute(
                    insert(PersistentVoiceTurnModel).values(
                        turn_id=turn.turn_id,
                        session_id=turn.session_id,
                        sequence=turn.sequence,
                        request_id=turn.request_id,
                        created_at=turn.created_at,
                        input_reference=turn.input_reference,
                        output_reference=turn.output_reference,
                        status=turn.status.value,
                        provenance=turn.provenance,
                    )
                )
            except IntegrityError as exc:
                raise PersistenceConflictError(
                    "voice turn already exists or violates continuity "
                    "constraints"
                ) from exc

            result = await db_session.execute(
                select(PersistentVoiceSessionModel).where(
                    PersistentVoiceSessionModel.session_id
                    == turn.session_id
                )
            )

            model = result.scalar_one_or_none()

            if model is None:
                raise VoiceSessionStoreError(
                    VoiceSessionError(
                        session_id=turn.session_id,
                        code=VoiceSessionErrorCode.SESSION_NOT_FOUND,
                        message="voice session disappeared during turn append",
                        retryable=False,
                        occurred_at=turn.created_at,
                    )
                )

            return self._to_session(model)

    async def get_turn(
        self,
        session_id: str,
        sequence: int,
    ) -> VoiceTurn | None:
        """Return one durable turn by session-local sequence."""
        normalized_id = session_id.strip()

        if not normalized_id:
            raise ValueError("session_id must not be empty")

        if sequence < 0:
            raise ValueError("sequence must be >= 0")

        async with self._read_session() as db_session:
            result = await db_session.execute(
                select(PersistentVoiceTurnModel).where(
                    PersistentVoiceTurnModel.session_id
                    == normalized_id,
                    PersistentVoiceTurnModel.sequence
                    == sequence,
                )
            )

            model = result.scalar_one_or_none()

            if model is None:
                return None

            return self._to_turn(model)

    @staticmethod
    def _to_session(
        model: PersistentVoiceSessionModel,
    ) -> VoiceSession:
        """Map a persisted ORM row to the immutable domain contract."""
        return VoiceSession(
            session_id=model.session_id,
            correlation_id=model.correlation_id,
            state=VoiceSessionState(model.state),
            session_revision=model.session_revision,
            next_turn_sequence=model.next_turn_sequence,
            created_at=model.created_at,
            last_activity_at=model.last_activity_at,
            expires_at=model.expires_at,
            resumable_until=model.resumable_until,
            continuity_version=model.continuity_version,
        )

    @staticmethod
    def _to_turn(
        model: PersistentVoiceTurnModel,
    ) -> VoiceTurn:
        """Map a persisted ORM row to the immutable domain contract."""
        return VoiceTurn(
            session_id=model.session_id,
            turn_id=model.turn_id,
            sequence=model.sequence,
            request_id=model.request_id,
            created_at=model.created_at,
            input_reference=model.input_reference,
            output_reference=model.output_reference,
            status=VoiceTurnStatus(model.status),
            provenance=model.provenance,
        )
