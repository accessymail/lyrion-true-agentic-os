"""Explicit fail-closed lifecycle policy for Lyrion voice sessions."""

from __future__ import annotations

from lyrion.voice.session.contracts import VoiceSessionState


class VoiceSessionLifecycle:
    """Validate explicit, fail-closed logical voice-session transitions."""

    _TRANSITIONS: dict[
        VoiceSessionState,
        frozenset[VoiceSessionState],
    ] = {
        VoiceSessionState.CREATED: frozenset(
            {
                VoiceSessionState.ACTIVE,
                VoiceSessionState.CLOSED,
                VoiceSessionState.EXPIRED,
            }
        ),
        VoiceSessionState.ACTIVE: frozenset(
            {
                VoiceSessionState.SUSPENDED,
                VoiceSessionState.EXPIRED,
                VoiceSessionState.CLOSED,
            }
        ),
        VoiceSessionState.SUSPENDED: frozenset(
            {
                VoiceSessionState.RESUMABLE,
                VoiceSessionState.EXPIRED,
                VoiceSessionState.CLOSED,
            }
        ),
        VoiceSessionState.RESUMABLE: frozenset(
            {
                VoiceSessionState.ACTIVE,
                VoiceSessionState.EXPIRED,
                VoiceSessionState.CLOSED,
            }
        ),
        VoiceSessionState.EXPIRED: frozenset(),
        VoiceSessionState.CLOSED: frozenset(),
    }

    @classmethod
    def is_allowed(
        cls,
        current: VoiceSessionState,
        target: VoiceSessionState,
    ) -> bool:
        """Return whether a lifecycle transition is explicitly permitted."""
        return target in cls._TRANSITIONS.get(
            current,
            frozenset(),
        )

    @classmethod
    def validate(
        cls,
        current: VoiceSessionState,
        target: VoiceSessionState,
    ) -> None:
        """Reject any lifecycle transition not explicitly declared."""
        if not cls.is_allowed(current, target):
            raise ValueError(
                "invalid voice session transition: "
                f"{current} -> {target}"
            )
