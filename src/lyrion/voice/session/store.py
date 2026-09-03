"""Persistence-neutral store contract for Lyrion voice sessions."""

from __future__ import annotations

from typing import Protocol

from lyrion.voice.session.contracts import (
    VoiceSession,
    VoiceTurn,
)


class VoiceSessionStore(Protocol):
    """Domain-level persistence contract for voice session continuity."""

    async def create(
        self,
        session: VoiceSession,
    ) -> VoiceSession:
        """Persist a new logical voice session."""
        ...

    async def get(
        self,
        session_id: str,
    ) -> VoiceSession | None:
        """Return a logical voice session or None when it does not exist."""
        ...

    async def save(
        self,
        session: VoiceSession,
        *,
        expected_revision: int,
    ) -> VoiceSession:
        """Persist a session using optimistic concurrency."""
        ...

    async def append_turn(
        self,
        turn: VoiceTurn,
        *,
        expected_session_revision: int,
    ) -> VoiceSession:
        """Atomically persist a turn and advance session continuity state."""
        ...

    async def get_turn(
        self,
        session_id: str,
        sequence: int,
    ) -> VoiceTurn | None:
        """Return one turn by its session-local sequence."""
        ...
