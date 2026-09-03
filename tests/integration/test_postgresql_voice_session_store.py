"""Real PostgreSQL integration tests for voice-session continuity."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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

BASE_TIME = datetime(2026, 9, 3, 12, 0, tzinfo=UTC)


def make_session() -> VoiceSession:
    return VoiceSession(
        session_id="integration-session-1",
        correlation_id="integration-correlation-1",
        state=VoiceSessionState.ACTIVE,
        session_revision=0,
        next_turn_sequence=0,
        created_at=BASE_TIME,
        last_activity_at=BASE_TIME,
        expires_at=BASE_TIME + timedelta(minutes=30),
        resumable_until=BASE_TIME + timedelta(minutes=10),
    )


def make_turn(
    *,
    session_id: str = "integration-session-1",
    sequence: int = 0,
) -> VoiceTurn:
    return VoiceTurn(
        session_id=session_id,
        turn_id=f"integration-turn-{sequence}",
        sequence=sequence,
        request_id=f"integration-request-{sequence}",
        created_at=BASE_TIME + timedelta(seconds=sequence),
        status=VoiceTurnStatus.COMPLETED,
        provenance="postgres-integration-test",
    )


@pytest.mark.asyncio
async def test_postgresql_voice_session_round_trip(
    database_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    store = SQLAlchemyVoiceSessionStore(database_session_factory)
    session = make_session()

    created = await store.create(session)
    loaded = await store.get(session.session_id)

    assert created == session
    assert loaded == session


@pytest.mark.asyncio
async def test_postgresql_voice_session_revision_update(
    database_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    store = SQLAlchemyVoiceSessionStore(database_session_factory)
    session = make_session()

    await store.create(session)

    updated = session.model_copy(
        update={
            "state": VoiceSessionState.SUSPENDED,
            "session_revision": 1,
            "last_activity_at": BASE_TIME + timedelta(seconds=1),
        }
    )

    saved = await store.save(
        updated,
        expected_revision=0,
    )

    loaded = await store.get(session.session_id)

    assert saved == updated
    assert loaded == updated


@pytest.mark.asyncio
async def test_postgresql_voice_turn_append_is_atomic(
    database_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    store = SQLAlchemyVoiceSessionStore(database_session_factory)
    session = make_session()

    await store.create(session)

    updated = await store.append_turn(
        make_turn(sequence=0),
        expected_session_revision=0,
    )

    loaded_session = await store.get(session.session_id)
    loaded_turn = await store.get_turn(
        session.session_id,
        0,
    )

    assert updated.session_revision == 1
    assert updated.next_turn_sequence == 1
    assert loaded_session == updated
    assert loaded_turn == make_turn(sequence=0)


@pytest.mark.asyncio
async def test_postgresql_concurrent_turn_append_has_one_winner(
    database_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    creator = SQLAlchemyVoiceSessionStore(database_session_factory)
    session = make_session()

    await creator.create(session)

    barrier = asyncio.Barrier(2)

    async def append_from_independent_transaction(
        turn_id: str,
    ) -> str:
        async with database_session_factory.begin() as db_session:
            store = SQLAlchemyVoiceSessionStore._from_session(
                db_session,
            )

            await barrier.wait()

            turn = make_turn(sequence=0).model_copy(
                update={"turn_id": turn_id},
            )

            try:
                await store.append_turn(
                    turn,
                    expected_session_revision=0,
                )
            except PersistenceConflictError:
                return "conflict"

            return "success"

    results = await asyncio.gather(
        append_from_independent_transaction("concurrent-turn-a"),
        append_from_independent_transaction("concurrent-turn-b"),
    )

    assert sorted(results) == ["conflict", "success"]

    loaded_session = await creator.get(session.session_id)
    assert loaded_session is not None
    assert loaded_session.session_revision == 1
    assert loaded_session.next_turn_sequence == 1

    loaded_turn = await creator.get_turn(
        session.session_id,
        0,
    )

    assert loaded_turn is not None
    assert loaded_turn.sequence == 0


@pytest.mark.asyncio
async def test_postgresql_duplicate_session_is_rejected(
    database_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    store = SQLAlchemyVoiceSessionStore(database_session_factory)
    session = make_session()

    await store.create(session)

    with pytest.raises(
        PersistenceConflictError,
        match="already exists",
    ):
        await store.create(session)


@pytest.mark.asyncio
async def test_postgresql_stale_session_revision_is_rejected(
    database_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    store = SQLAlchemyVoiceSessionStore(database_session_factory)
    session = make_session()

    await store.create(session)

    updated = session.model_copy(
        update={
            "session_revision": 1,
            "last_activity_at": BASE_TIME + timedelta(seconds=1),
        }
    )

    await store.save(
        updated,
        expected_revision=0,
    )

    stale = session.model_copy(
        update={
            "session_revision": 1,
            "last_activity_at": BASE_TIME + timedelta(seconds=2),
        }
    )

    with pytest.raises(
        PersistenceConflictError,
        match="revision conflict",
    ):
        await store.save(
            stale,
            expected_revision=0,
        )


@pytest.mark.asyncio
async def test_postgresql_out_of_order_turn_is_rejected(
    database_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    store = SQLAlchemyVoiceSessionStore(database_session_factory)
    session = make_session()

    await store.create(session)

    with pytest.raises(
        PersistenceConflictError,
        match="revision or turn sequence conflict",
    ):
        await store.append_turn(
            make_turn(sequence=2),
            expected_session_revision=0,
        )

    loaded_session = await store.get(session.session_id)

    assert loaded_session == session
    assert await store.get_turn(session.session_id, 2) is None


@pytest.mark.asyncio
async def test_postgresql_turn_survives_independent_session(
    database_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    writer = SQLAlchemyVoiceSessionStore(database_session_factory)
    reader = SQLAlchemyVoiceSessionStore(database_session_factory)
    session = make_session()

    await writer.create(session)
    await writer.append_turn(
        make_turn(sequence=0),
        expected_session_revision=0,
    )

    loaded = await reader.get_turn(
        session.session_id,
        0,
    )

    assert loaded is not None
    assert loaded.turn_id == "integration-turn-0"
