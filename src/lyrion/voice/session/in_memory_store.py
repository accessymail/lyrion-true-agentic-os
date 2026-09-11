"""Deterministic in-memory reference store for voice session continuity."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from lyrion.voice.session.contracts import (
    VoiceSession,
    VoiceSessionError,
    VoiceSessionErrorCode,
    VoiceTurn,
)
from lyrion.voice.session.store import VoiceSessionStore


class VoiceSessionStoreError(RuntimeError):
    """Raised when a voice-session store operation fails safely."""

    def __init__(self, error: VoiceSessionError) -> None:
        self.error = error
        super().__init__(error.message)


@dataclass(slots=True)
class _StoredSession:
    session: VoiceSession
    turns: dict[int, VoiceTurn]


class InMemoryVoiceSessionStore(VoiceSessionStore):
    """Reference implementation of the voice-session store protocol."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._sessions: dict[str, _StoredSession] = {}

    async def create(
        self,
        session: VoiceSession,
    ) -> VoiceSession:
        """Create one logical session and reject duplicate identifiers."""
        async with self._lock:
            if session.session_id in self._sessions:
                raise VoiceSessionStoreError(
                    VoiceSessionError(
                        session_id=session.session_id,
                        code=VoiceSessionErrorCode.SESSION_STATE_CONFLICT,
                        message="voice session already exists",
                        occurred_at=session.created_at,
                    )
                )

            self._sessions[session.session_id] = _StoredSession(
                session=session,
                turns={},
            )
            return session

    async def get(
        self,
        session_id: str,
    ) -> VoiceSession | None:
        """Return a session snapshot or None when absent."""
        normalized_id = self._require_id(session_id)

        async with self._lock:
            stored = self._sessions.get(normalized_id)
            if stored is None:
                return None

            return stored.session

    async def save(
        self,
        session: VoiceSession,
        *,
        expected_revision: int,
    ) -> VoiceSession:
        """Save a session using optimistic concurrency."""
        if expected_revision < 0:
            raise ValueError("expected_revision must be >= 0")

        async with self._lock:
            stored = self._sessions.get(session.session_id)

            if stored is None:
                raise VoiceSessionStoreError(
                    VoiceSessionError(
                        session_id=session.session_id,
                        code=VoiceSessionErrorCode.SESSION_NOT_FOUND,
                        message="voice session does not exist",
                        occurred_at=session.last_activity_at,
                    )
                )

            current = stored.session

            if current.session_revision != expected_revision:
                raise VoiceSessionStoreError(
                    VoiceSessionError(
                        session_id=session.session_id,
                        code=VoiceSessionErrorCode.STALE_SESSION_REVISION,
                        message=(
                            "voice session revision conflict: "
                            f"expected {expected_revision}, "
                            f"current {current.session_revision}"
                        ),
                        occurred_at=session.last_activity_at,
                    )
                )

            if session.session_revision != expected_revision + 1:
                raise VoiceSessionStoreError(
                    VoiceSessionError(
                        session_id=session.session_id,
                        code=VoiceSessionErrorCode.SESSION_STATE_CONFLICT,
                        message=(
                            "saved session revision must advance exactly "
                            "one revision"
                        ),
                        occurred_at=session.last_activity_at,
                    )
                )

            self._sessions[session.session_id] = _StoredSession(
                session=session,
                turns=stored.turns,
            )
            return session

    async def append_turn(
        self,
        turn: VoiceTurn,
        *,
        expected_session_revision: int,
    ) -> VoiceSession:
        """
        Atomically append one turn and advance session continuity state.

        The turn sequence must equal the session's next expected sequence.
        """
        if expected_session_revision < 0:
            raise ValueError("expected_session_revision must be >= 0")

        async with self._lock:
            stored = self._sessions.get(turn.session_id)

            if stored is None:
                raise VoiceSessionStoreError(
                    VoiceSessionError(
                        session_id=turn.session_id,
                        code=VoiceSessionErrorCode.SESSION_NOT_FOUND,
                        message="voice session does not exist",
                        occurred_at=turn.created_at,
                    )
                )

            session = stored.session

            if session.session_revision != expected_session_revision:
                raise VoiceSessionStoreError(
                    VoiceSessionError(
                        session_id=turn.session_id,
                        code=VoiceSessionErrorCode.STALE_SESSION_REVISION,
                        message=(
                            "voice session revision conflict: "
                            f"expected {expected_session_revision}, "
                            f"current {session.session_revision}"
                        ),
                        occurred_at=turn.created_at,
                    )
                )

            if turn.sequence < session.next_turn_sequence:
                raise VoiceSessionStoreError(
                    VoiceSessionError(
                        session_id=turn.session_id,
                        code=VoiceSessionErrorCode.TURN_REPLAY,
                        message=(
                            "voice turn sequence has already been committed: "
                            f"{turn.sequence}"
                        ),
                        occurred_at=turn.created_at,
                    )
                )

            if turn.sequence > session.next_turn_sequence:
                raise VoiceSessionStoreError(
                    VoiceSessionError(
                        session_id=turn.session_id,
                        code=VoiceSessionErrorCode.TURN_OUT_OF_ORDER,
                        message=(
                            "voice turn sequence is out of order: "
                            f"expected {session.next_turn_sequence}, "
                            f"received {turn.sequence}"
                        ),
                        occurred_at=turn.created_at,
                    )
                )

            existing_turn = stored.turns.get(turn.sequence)
            if existing_turn is not None:
                raise VoiceSessionStoreError(
                    VoiceSessionError(
                        session_id=turn.session_id,
                        code=VoiceSessionErrorCode.TURN_REPLAY,
                        message="voice turn already exists",
                        occurred_at=turn.created_at,
                    )
                )

            updated_session = session.model_copy(
                update={
                    "next_turn_sequence": session.next_turn_sequence + 1,
                    "session_revision": session.session_revision + 1,
                    "last_activity_at": turn.created_at,
                }
            )

            stored.turns[turn.sequence] = turn
            stored.session = updated_session

            return updated_session

    async def get_turn(
        self,
        session_id: str,
        sequence: int,
    ) -> VoiceTurn | None:
        """Return one persisted turn by session-local sequence."""
        normalized_id = self._require_id(session_id)

        if sequence < 0:
            raise ValueError("sequence must be >= 0")

        async with self._lock:
            stored = self._sessions.get(normalized_id)

            if stored is None:
                return None

            return stored.turns.get(sequence)

    @staticmethod
    def _require_id(value: str) -> str:
        """Normalize and validate a session identifier."""
        normalized = value.strip()

        if not normalized:
            raise ValueError("session_id must not be empty")

        if len(normalized) > 200:
            raise ValueError("session_id must not exceed 200 characters")

        return normalized
