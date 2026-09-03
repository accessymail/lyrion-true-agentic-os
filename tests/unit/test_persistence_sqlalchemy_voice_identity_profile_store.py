"""Behavioral tests for the SQLAlchemy Voice Identity profile store."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import ClauseElement

from lyrion.persistence.sqlalchemy.errors import PersistenceConflictError
from lyrion.persistence.sqlalchemy.voice_identity_profile_store import (
    SQLAlchemyVoiceIdentityProfileStore,
)
from lyrion.voice.contracts import VoiceIdentityProfile, VoiceIdentityProfileStatus

BASE_TIME = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)


class FakeScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class FakeCursorResult:
    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


class FakeSession:
    def __init__(
        self,
        *,
        get_value: object = None,
        update_rowcount: int = 1,
    ) -> None:
        self.get_value = get_value
        self.update_rowcount = update_rowcount
        self.executed: list[ClauseElement] = []

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        return None

    async def execute(self, statement: ClauseElement) -> object:
        self.executed.append(statement)
        if statement.is_update:
            return cast(CursorResult[Any], FakeCursorResult(self.update_rowcount))
        return FakeScalarResult(self.get_value)


class FakeSessionFactory:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    def __call__(self) -> FakeSession:
        return self.session

    @asynccontextmanager
    async def begin(self) -> AsyncIterator[FakeSession]:
        yield self.session


class IntegrityErrorSession(FakeSession):
    async def execute(self, statement: ClauseElement) -> object:
        self.executed.append(statement)
        raise IntegrityError("duplicate", {}, Exception("duplicate"))


def make_profile(revision: int = 1) -> VoiceIdentityProfile:
    return VoiceIdentityProfile(
        identity_id="person-1",
        status=VoiceIdentityProfileStatus.ACTIVE,
        representation_refs=("rep-1",),
        enrolled_at=BASE_TIME,
        updated_at=BASE_TIME,
        provenance="test",
        revision=revision,
    )


@pytest.mark.asyncio
async def test_get_missing_returns_none() -> None:
    store = SQLAlchemyVoiceIdentityProfileStore(
        cast(Any, FakeSessionFactory(FakeSession()))
    )
    assert await store.get("person-1") is None


@pytest.mark.asyncio
async def test_get_existing_converts_persisted_profile() -> None:
    row = type(
        "VoiceIdentityRow",
        (), {
            "identity_id": "person-1",
            "status": "ACTIVE",
            "representation_refs": ["rep-1"],
            "enrolled_at": BASE_TIME,
            "updated_at": BASE_TIME,
            "provenance": "test",
            "revision": 3,
        },
    )()
    store = SQLAlchemyVoiceIdentityProfileStore(
        cast(Any, FakeSessionFactory(FakeSession(get_value=row)))
    )
    result = await store.get("person-1")
    assert result is not None
    assert result.revision == 3
    assert result.status is VoiceIdentityProfileStatus.ACTIVE


@pytest.mark.asyncio
async def test_create_returns_original_profile() -> None:
    profile = make_profile()
    store = SQLAlchemyVoiceIdentityProfileStore(
        cast(Any, FakeSessionFactory(FakeSession()))
    )
    assert await store.create(profile) is profile


@pytest.mark.asyncio
async def test_create_duplicate_raises_conflict() -> None:
    store = SQLAlchemyVoiceIdentityProfileStore(
        cast(Any, FakeSessionFactory(IntegrityErrorSession()))
    )
    with pytest.raises(PersistenceConflictError, match="already exists"):
        await store.create(make_profile())


@pytest.mark.asyncio
async def test_transition_advances_revision() -> None:
    store = SQLAlchemyVoiceIdentityProfileStore(
        cast(Any, FakeSessionFactory(FakeSession(update_rowcount=1)))
    )
    profile = make_profile(revision=2)
    result = await store.transition(
        "person-1",
        expected_revision=1,
        profile=profile,
    )
    assert result.revision == 2


@pytest.mark.asyncio
async def test_transition_stale_revision_raises_conflict() -> None:
    store = SQLAlchemyVoiceIdentityProfileStore(
        cast(Any, FakeSessionFactory(FakeSession(update_rowcount=0)))
    )
    with pytest.raises(PersistenceConflictError, match="revision conflict"):
        await store.transition(
            "person-1",
            expected_revision=1,
            profile=make_profile(revision=2),
        )


@pytest.mark.asyncio
async def test_update_advances_revision() -> None:
    store = SQLAlchemyVoiceIdentityProfileStore(
        cast(Any, FakeSessionFactory(FakeSession(update_rowcount=1)))
    )
    profile = make_profile(revision=2)

    result = await store.update(
        profile,
        expected_revision=1,
    )

    assert result is profile
    assert result.revision == 2


@pytest.mark.asyncio
async def test_update_stale_revision_raises_conflict() -> None:
    store = SQLAlchemyVoiceIdentityProfileStore(
        cast(Any, FakeSessionFactory(FakeSession(update_rowcount=0)))
    )

    with pytest.raises(PersistenceConflictError, match="revision conflict"):
        await store.update(
            make_profile(revision=2),
            expected_revision=1,
        )


@pytest.mark.asyncio
async def test_update_rejects_non_positive_expected_revision() -> None:
    store = SQLAlchemyVoiceIdentityProfileStore(
        cast(Any, FakeSessionFactory(FakeSession()))
    )

    with pytest.raises(ValueError, match="expected_revision must be positive"):
        await store.update(
            make_profile(revision=2),
            expected_revision=0,
        )


@pytest.mark.asyncio
async def test_update_rejects_non_sequential_profile_revision() -> None:
    store = SQLAlchemyVoiceIdentityProfileStore(
        cast(Any, FakeSessionFactory(FakeSession()))
    )

    with pytest.raises(
        ValueError,
        match="profile revision must advance by exactly one",
    ):
        await store.update(
            make_profile(revision=3),
            expected_revision=1,
        )
