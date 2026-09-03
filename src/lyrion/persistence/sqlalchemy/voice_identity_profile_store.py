"""SQLAlchemy implementation of the durable Voice Identity profile store."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from sqlalchemy import insert, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lyrion.persistence.sqlalchemy.errors import PersistenceConflictError
from lyrion.persistence.sqlalchemy.models import VoiceIdentityProfileModel
from lyrion.voice.contracts import VoiceIdentityProfile, VoiceIdentityProfileStatus


class SQLAlchemyVoiceIdentityProfileStore:
    """Persist Voice Identity profiles through SQLAlchemy."""

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
    ) -> SQLAlchemyVoiceIdentityProfileStore:
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

    async def get(self, identity_id: str) -> VoiceIdentityProfile | None:
        """Return one durable profile by identity ID."""
        normalized_id = identity_id.strip()
        if not normalized_id:
            raise ValueError("identity_id must not be empty")
        async with self._read_session() as session:
            result = await session.execute(
                select(VoiceIdentityProfileModel).where(
                    VoiceIdentityProfileModel.identity_id == normalized_id
                )
            )
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return VoiceIdentityProfile(
                identity_id=model.identity_id,
                status=VoiceIdentityProfileStatus(model.status),
                representation_refs=tuple(model.representation_refs),
                enrolled_at=model.enrolled_at,
                updated_at=model.updated_at,
                provenance=model.provenance,
                revision=model.revision,
            )

    async def create(self, profile: VoiceIdentityProfile) -> VoiceIdentityProfile:
        """Atomically create one durable profile."""
        async with self._write_session() as session:
            try:
                await session.execute(
                    insert(VoiceIdentityProfileModel).values(
                        identity_id=profile.identity_id,
                        status=profile.status.value,
                        representation_refs=list(profile.representation_refs),
                        enrolled_at=profile.enrolled_at,
                        updated_at=profile.updated_at,
                        provenance=profile.provenance,
                        revision=profile.revision,
                    )
                )
            except IntegrityError as exc:
                raise PersistenceConflictError(
                    "voice identity profile already exists"
                ) from exc
        return profile

    async def update(
        self,
        profile: VoiceIdentityProfile,
        *,
        expected_revision: int,
    ) -> VoiceIdentityProfile:
        """Atomically persist one revision-checked profile update."""
        normalized_id = profile.identity_id.strip()
        if not normalized_id:
            raise ValueError("profile.identity_id must not be empty")
        if expected_revision < 1:
            raise ValueError("expected_revision must be positive")
        if profile.revision != expected_revision + 1:
            raise ValueError("profile revision must advance by exactly one")
        async with self._write_session() as session:
            result = await session.execute(
                update(VoiceIdentityProfileModel)
                .where(
                    VoiceIdentityProfileModel.identity_id == normalized_id,
                    VoiceIdentityProfileModel.revision == expected_revision,
                )
                .values(
                    status=profile.status.value,
                    representation_refs=list(profile.representation_refs),
                    enrolled_at=profile.enrolled_at,
                    updated_at=profile.updated_at,
                    provenance=profile.provenance,
                    revision=profile.revision,
                )
            )
            cursor_result = cast(CursorResult[Any], result)
            if cursor_result.rowcount != 1:
                raise PersistenceConflictError(
                    "voice identity profile revision conflict"
                )
        return profile

    async def transition(
        self,
        identity_id: str,
        *, 
        expected_revision: int,
        profile: VoiceIdentityProfile,
    ) -> VoiceIdentityProfile:
        """Atomically persist one optimistic-concurrency transition."""
        normalized_id = identity_id.strip()
        if not normalized_id:
            raise ValueError("identity_id must not be empty")
        if profile.identity_id != normalized_id:
            raise ValueError("profile.identity_id must match identity_id")
        if expected_revision < 1:
            raise ValueError("expected_revision must be positive")
        if profile.revision != expected_revision + 1:
            raise ValueError("profile revision must advance by exactly one")
        async with self._write_session() as session:
            result = await session.execute(
                update(VoiceIdentityProfileModel)
                .where(
                    VoiceIdentityProfileModel.identity_id == normalized_id,
                    VoiceIdentityProfileModel.revision == expected_revision,
                )
                .values(
                    status=profile.status.value,
                    representation_refs=list(profile.representation_refs),
                    enrolled_at=profile.enrolled_at,
                    updated_at=profile.updated_at,
                    provenance=profile.provenance,
                    revision=profile.revision,
                )
            )
            cursor_result = cast(CursorResult[Any], result)
            if cursor_result.rowcount != 1:
                raise PersistenceConflictError("voice identity profile revision conflict")
        return profile
