"""Behavioral tests for the SQLAlchemy voice-session store."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import ClauseElement

from lyrion.persistence.sqlalchemy.errors import PersistenceConflictError
from lyrion.persistence.sqlalchemy.voice_session_store import (
    SQLAlchemyVoiceSessionStore,
)
from lyrion.voice.session.contracts import (
    VoiceSession,
    VoiceSessionState,
    VoiceTurn,
    VoiceTurnStatus,
)

BASE_TIME = datetime(2026, 9, 3, 10, 0, tzinfo=UTC)


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
        sequence_update_rowcount: int = 1,
        second_get_value: object = None,
    ) -> None:
        self.get_value = get_value
        self.update_rowcount = update_rowcount
        self.sequence_update_rowcount = sequence_update_rowcount
        self.second_get_value = second_get_value
        self.executed: list[ClauseElement] = []
        self._execute_count = 0

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
        self._execute_count += 1

        if statement.is_update:
            return cast(
                CursorResult[Any],
                FakeCursorResult(
                    
                        self.update_rowcount
                        if self._execute_count == 1
                        else self.sequence_update_rowcount
                    
                ),
            )

        if statement.is_insert:
            return object()

        if self._execute_count > 1 and self.second_get_value is not None:
            return FakeScalarResult(self.second_get_value)

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

        if statement.is_insert:
            raise IntegrityError(
                "duplicate",
                {},
                Exception("duplicate"),
            )

        return await super().execute(statement)


def make_session(
    *,
    state: VoiceSessionState = VoiceSessionState.ACTIVE,
    revision: int = 0,
    next_turn_sequence: int = 0,
) -> VoiceSession:
    return VoiceSession(
        session_id="session-1",
        correlation_id="correlation-1",
        state=state,
        session_revision=revision,
        next_turn_sequence=next_turn_sequence,
        created_at=BASE_TIME,
        last_activity_at=BASE_TIME,
        expires_at=BASE_TIME + timedelta(minutes=30),
        resumable_until=BASE_TIME + timedelta(minutes=10),
    )


def make_turn(sequence: int = 0) -> VoiceTurn:
    return VoiceTurn(
        session_id="session-1",
        turn_id=f"turn-{sequence}",
        sequence=sequence,
        request_id=f"request-{sequence}",
        created_at=BASE_TIME + timedelta(seconds=sequence),
        status=VoiceTurnStatus.COMPLETED,
        provenance="test",
    )


def make_session_row(
    *,
    state: str = "ACTIVE",
    revision: int = 0,
    next_turn_sequence: int = 0,
) -> object:
    return type(
        "VoiceSessionRow",
        (),
        {
            "session_id": "session-1",
            "correlation_id": "correlation-1",
            "state": state,
            "session_revision": revision,
            "next_turn_sequence": next_turn_sequence,
            "created_at": BASE_TIME,
            "last_activity_at": BASE_TIME,
            "expires_at": BASE_TIME + timedelta(minutes=30),
            "resumable_until": BASE_TIME + timedelta(minutes=10),
            "continuity_version": 1,
        },
    )()


def make_turn_row(
    *,
    sequence: int = 0,
) -> object:
    return type(
        "VoiceTurnRow",
        (),
        {
            "turn_id": f"turn-{sequence}",
            "session_id": "session-1",
            "sequence": sequence,
            "request_id": f"request-{sequence}",
            "created_at": BASE_TIME + timedelta(seconds=sequence),
            "input_reference": None,
            "output_reference": None,
            "status": "COMPLETED",
            "provenance": "test",
        },
    )()


@pytest.mark.asyncio
async def test_get_missing_returns_none() -> None:
    store = SQLAlchemyVoiceSessionStore(
        cast(Any, FakeSessionFactory(FakeSession()))
    )

    assert await store.get("session-1") is None


@pytest.mark.asyncio
async def test_get_existing_converts_persisted_session() -> None:
    row = make_session_row(
        state="SUSPENDED",
        revision=3,
        next_turn_sequence=7,
    )

    store = SQLAlchemyVoiceSessionStore(
        cast(
            Any,
            FakeSessionFactory(
                FakeSession(get_value=row),
            ),
        )
    )

    result = await store.get("session-1")

    assert result is not None
    assert result.session_id == "session-1"
    assert result.state is VoiceSessionState.SUSPENDED
    assert result.session_revision == 3
    assert result.next_turn_sequence == 7


@pytest.mark.asyncio
async def test_create_returns_original_session() -> None:
    session = make_session()
    store = SQLAlchemyVoiceSessionStore(
        cast(Any, FakeSessionFactory(FakeSession()))
    )

    assert await store.create(session) is session


@pytest.mark.asyncio
async def test_create_duplicate_raises_conflict() -> None:
    store = SQLAlchemyVoiceSessionStore(
        cast(Any, FakeSessionFactory(IntegrityErrorSession()))
    )

    with pytest.raises(
        PersistenceConflictError,
        match="already exists",
    ):
        await store.create(make_session())


@pytest.mark.asyncio
async def test_save_advances_revision() -> None:
    store = SQLAlchemyVoiceSessionStore(
        cast(
            Any,
            FakeSessionFactory(
                FakeSession(update_rowcount=1),
            ),
        )
    )

    updated = make_session(revision=1)

    result = await store.save(
        updated,
        expected_revision=0,
    )

    assert result is updated
    assert result.session_revision == 1


@pytest.mark.asyncio
async def test_save_stale_revision_raises_conflict() -> None:
    store = SQLAlchemyVoiceSessionStore(
        cast(
            Any,
            FakeSessionFactory(
                FakeSession(update_rowcount=0),
            ),
        )
    )

    with pytest.raises(
        PersistenceConflictError,
        match="revision conflict",
    ):
        await store.save(
            make_session(revision=1),
            expected_revision=0,
        )


@pytest.mark.asyncio
async def test_save_rejects_non_sequential_revision() -> None:
    store = SQLAlchemyVoiceSessionStore(
        cast(Any, FakeSessionFactory(FakeSession()))
    )

    with pytest.raises(
        ValueError,
        match="advance by exactly one",
    ):
        await store.save(
            make_session(revision=2),
            expected_revision=0,
        )


@pytest.mark.asyncio
async def test_save_rejects_negative_expected_revision() -> None:
    store = SQLAlchemyVoiceSessionStore(
        cast(Any, FakeSessionFactory(FakeSession()))
    )

    with pytest.raises(
        ValueError,
        match="expected_revision must be >= 0",
    ):
        await store.save(
            make_session(revision=0),
            expected_revision=-1,
        )


@pytest.mark.asyncio
async def test_append_turn_advances_session_and_returns_updated_state() -> None:
    updated_row = make_session_row(
        state="ACTIVE",
        revision=1,
        next_turn_sequence=1,
    )

    store = SQLAlchemyVoiceSessionStore(
        cast(
            Any,
            FakeSessionFactory(
                FakeSession(
                    update_rowcount=1,
                    second_get_value=updated_row,
                ),
            ),
        )
    )

    result = await store.append_turn(
        make_turn(0),
        expected_session_revision=0,
    )

    assert result.session_revision == 1
    assert result.next_turn_sequence == 1


@pytest.mark.asyncio
async def test_append_turn_conflict_raises_persistence_conflict() -> None:
    store = SQLAlchemyVoiceSessionStore(
        cast(
            Any,
            FakeSessionFactory(
                FakeSession(
                    update_rowcount=0,
                ),
            ),
        )
    )

    with pytest.raises(
        PersistenceConflictError,
        match="revision or turn sequence conflict",
    ):
        await store.append_turn(
            make_turn(0),
            expected_session_revision=0,
        )


@pytest.mark.asyncio
async def test_append_turn_duplicate_insert_raises_conflict() -> None:
    class UpdateThenIntegrityErrorSession(FakeSession):
        async def execute(
            self,
            statement: ClauseElement,
        ) -> object:
            self.executed.append(statement)

            if statement.is_update:
                return cast(
                    CursorResult[Any],
                    FakeCursorResult(1),
                )

            if statement.is_insert:
                raise IntegrityError(
                    "duplicate",
                    {},
                    Exception("duplicate"),
                )

            return FakeScalarResult(
                make_session_row(
                    revision=1,
                    next_turn_sequence=1,
                )
            )

    store = SQLAlchemyVoiceSessionStore(
        cast(
            Any,
            FakeSessionFactory(
                UpdateThenIntegrityErrorSession(),
            ),
        )
    )

    with pytest.raises(
        PersistenceConflictError,
        match="voice turn already exists",
    ):
        await store.append_turn(
            make_turn(0),
            expected_session_revision=0,
        )


@pytest.mark.asyncio
async def test_append_turn_requires_non_negative_revision() -> None:
    store = SQLAlchemyVoiceSessionStore(
        cast(Any, FakeSessionFactory(FakeSession()))
    )

    with pytest.raises(
        ValueError,
        match="expected_session_revision must be >= 0",
    ):
        await store.append_turn(
            make_turn(0),
            expected_session_revision=-1,
        )


@pytest.mark.asyncio
async def test_get_turn_missing_returns_none() -> None:
    store = SQLAlchemyVoiceSessionStore(
        cast(Any, FakeSessionFactory(FakeSession()))
    )

    assert await store.get_turn("session-1", 0) is None


@pytest.mark.asyncio
async def test_get_turn_converts_persisted_turn() -> None:
    row = make_turn_row(sequence=3)

    store = SQLAlchemyVoiceSessionStore(
        cast(
            Any,
            FakeSessionFactory(
                FakeSession(get_value=row),
            ),
        )
    )

    result = await store.get_turn("session-1", 3)

    assert result is not None
    assert result.turn_id == "turn-3"
    assert result.sequence == 3
    assert result.status is VoiceTurnStatus.COMPLETED


@pytest.mark.asyncio
async def test_get_rejects_blank_session_id() -> None:
    store = SQLAlchemyVoiceSessionStore(
        cast(Any, FakeSessionFactory(FakeSession()))
    )

    with pytest.raises(
        ValueError,
        match="session_id must not be empty",
    ):
        await store.get("   ")


@pytest.mark.asyncio
async def test_get_turn_rejects_blank_session_id() -> None:
    store = SQLAlchemyVoiceSessionStore(
        cast(Any, FakeSessionFactory(FakeSession()))
    )

    with pytest.raises(
        ValueError,
        match="session_id must not be empty",
    ):
        await store.get_turn("   ", 0)


@pytest.mark.asyncio
async def test_get_turn_rejects_negative_sequence() -> None:
    store = SQLAlchemyVoiceSessionStore(
        cast(Any, FakeSessionFactory(FakeSession()))
    )

    with pytest.raises(
        ValueError,
        match="sequence must be >= 0",
    ):
        await store.get_turn("session-1", -1)


def test_store_requires_exactly_one_session_source() -> None:
    with pytest.raises(
        ValueError,
        match="exactly one session source is required",
    ):
        SQLAlchemyVoiceSessionStore()


def test_store_rejects_two_session_sources() -> None:
    session = cast(Any, FakeSession())

    with pytest.raises(
        ValueError,
        match="exactly one session source is required",
    ):
        SQLAlchemyVoiceSessionStore(
            cast(Any, FakeSessionFactory(session)),
            session=session,
        )
