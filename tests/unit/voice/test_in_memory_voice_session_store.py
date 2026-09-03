"""Unit tests for the 19.4.6 in-memory voice session store."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lyrion.voice.session.contracts import (
    VoiceSession,
    VoiceSessionErrorCode,
    VoiceSessionState,
    VoiceTurn,
    VoiceTurnStatus,
)
from lyrion.voice.session.in_memory_store import (
    InMemoryVoiceSessionStore,
    VoiceSessionStoreError,
)

BASE_TIME = datetime(2026, 9, 3, 10, 0, tzinfo=UTC)


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


@pytest.mark.asyncio
async def test_create_and_get_session() -> None:
    store = InMemoryVoiceSessionStore()
    session = make_session()

    created = await store.create(session)
    loaded = await store.get("session-1")

    assert created == session
    assert loaded == session


@pytest.mark.asyncio
async def test_missing_session_returns_none() -> None:
    store = InMemoryVoiceSessionStore()

    assert await store.get("missing") is None
    assert await store.get_turn("missing", 0) is None


@pytest.mark.asyncio
async def test_duplicate_session_is_rejected() -> None:
    store = InMemoryVoiceSessionStore()
    session = make_session()

    await store.create(session)

    with pytest.raises(VoiceSessionStoreError) as exc_info:
        await store.create(session)

    assert (
        exc_info.value.error.code
        is VoiceSessionErrorCode.SESSION_STATE_CONFLICT
    )


@pytest.mark.asyncio
async def test_save_advances_revision_exactly_once() -> None:
    store = InMemoryVoiceSessionStore()
    session = make_session()
    await store.create(session)

    updated = session.model_copy(
        update={
            "session_revision": 1,
            "last_activity_at": BASE_TIME + timedelta(seconds=1),
        }
    )

    saved = await store.save(
        updated,
        expected_revision=0,
    )

    assert saved.session_revision == 1
    assert await store.get("session-1") == saved


@pytest.mark.asyncio
async def test_save_rejects_stale_revision() -> None:
    store = InMemoryVoiceSessionStore()
    await store.create(make_session())

    updated = make_session(revision=1)

    with pytest.raises(VoiceSessionStoreError) as exc_info:
        await store.save(
            updated,
            expected_revision=7,
        )

    assert (
        exc_info.value.error.code
        is VoiceSessionErrorCode.STALE_SESSION_REVISION
    )


@pytest.mark.asyncio
async def test_save_rejects_non_incrementing_revision() -> None:
    store = InMemoryVoiceSessionStore()
    session = make_session()
    await store.create(session)

    with pytest.raises(VoiceSessionStoreError) as exc_info:
        await store.save(
            session,
            expected_revision=0,
        )

    assert (
        exc_info.value.error.code
        is VoiceSessionErrorCode.SESSION_STATE_CONFLICT
    )


@pytest.mark.asyncio
async def test_save_missing_session_fails() -> None:
    store = InMemoryVoiceSessionStore()

    with pytest.raises(VoiceSessionStoreError) as exc_info:
        await store.save(
            make_session(revision=1),
            expected_revision=0,
        )

    assert (
        exc_info.value.error.code
        is VoiceSessionErrorCode.SESSION_NOT_FOUND
    )


@pytest.mark.asyncio
async def test_append_first_turn_advances_session() -> None:
    store = InMemoryVoiceSessionStore()
    await store.create(make_session())

    updated = await store.append_turn(
        make_turn(0),
        expected_session_revision=0,
    )

    assert updated.session_revision == 1
    assert updated.next_turn_sequence == 1
    assert updated.last_activity_at == BASE_TIME


@pytest.mark.asyncio
async def test_append_turn_is_retrievable() -> None:
    store = InMemoryVoiceSessionStore()
    await store.create(make_session())

    turn = make_turn(0)

    await store.append_turn(
        turn,
        expected_session_revision=0,
    )

    assert await store.get_turn("session-1", 0) == turn


@pytest.mark.asyncio
async def test_append_turn_requires_expected_sequence() -> None:
    store = InMemoryVoiceSessionStore()
    await store.create(make_session())

    with pytest.raises(VoiceSessionStoreError) as exc_info:
        await store.append_turn(
            make_turn(2),
            expected_session_revision=0,
        )

    assert (
        exc_info.value.error.code
        is VoiceSessionErrorCode.TURN_OUT_OF_ORDER
    )


@pytest.mark.asyncio
async def test_append_turn_rejects_replay() -> None:
    store = InMemoryVoiceSessionStore()
    await store.create(make_session())

    await store.append_turn(
        make_turn(0),
        expected_session_revision=0,
    )

    with pytest.raises(VoiceSessionStoreError) as exc_info:
        await store.append_turn(
            make_turn(0),
            expected_session_revision=1,
        )

    assert exc_info.value.error.code is VoiceSessionErrorCode.TURN_REPLAY


@pytest.mark.asyncio
async def test_append_turn_rejects_stale_session_revision() -> None:
    store = InMemoryVoiceSessionStore()
    await store.create(make_session())

    with pytest.raises(VoiceSessionStoreError) as exc_info:
        await store.append_turn(
            make_turn(0),
            expected_session_revision=9,
        )

    assert (
        exc_info.value.error.code
        is VoiceSessionErrorCode.STALE_SESSION_REVISION
    )


@pytest.mark.asyncio
async def test_append_turn_missing_session_fails() -> None:
    store = InMemoryVoiceSessionStore()

    with pytest.raises(VoiceSessionStoreError) as exc_info:
        await store.append_turn(
            make_turn(0),
            expected_session_revision=0,
        )

    assert (
        exc_info.value.error.code
        is VoiceSessionErrorCode.SESSION_NOT_FOUND
    )


@pytest.mark.asyncio
async def test_append_turn_advances_multiple_sequences() -> None:
    store = InMemoryVoiceSessionStore()
    await store.create(make_session())

    first = await store.append_turn(
        make_turn(0),
        expected_session_revision=0,
    )
    second = await store.append_turn(
        make_turn(1),
        expected_session_revision=1,
    )

    assert first.next_turn_sequence == 1
    assert first.session_revision == 1
    assert second.next_turn_sequence == 2
    assert second.session_revision == 2


@pytest.mark.asyncio
async def test_session_snapshots_are_not_mutable() -> None:
    store = InMemoryVoiceSessionStore()
    session = make_session()
    await store.create(session)

    loaded = await store.get("session-1")
    assert loaded is not None

    with pytest.raises(ValidationError):
        loaded.session_revision = 99  # type: ignore[misc]
