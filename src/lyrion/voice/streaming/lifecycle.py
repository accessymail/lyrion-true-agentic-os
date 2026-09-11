"""Explicit lifecycle policy for streaming voice interactions."""

from __future__ import annotations

from lyrion.voice.streaming.contracts import VoiceStreamState


class VoiceStreamLifecycle:
    """Fail-closed streaming lifecycle transition policy."""

    _TRANSITIONS: dict[
        VoiceStreamState,
        frozenset[VoiceStreamState],
    ] = {
        VoiceStreamState.IDLE: frozenset({VoiceStreamState.STARTING}),
        VoiceStreamState.STARTING: frozenset(
            {
                VoiceStreamState.STREAMING,
                VoiceStreamState.CANCEL_REQUESTED,
                VoiceStreamState.FAILED,
            }
        ),
        VoiceStreamState.STREAMING: frozenset(
            {
                VoiceStreamState.TURN_ACTIVE,
                VoiceStreamState.OUTPUT_STREAMING,
                VoiceStreamState.CANCEL_REQUESTED,
                VoiceStreamState.FAILED,
            }
        ),
        VoiceStreamState.TURN_ACTIVE: frozenset(
            {
                VoiceStreamState.STREAMING,
                VoiceStreamState.PROCESSING,
                VoiceStreamState.OUTPUT_STREAMING,
                VoiceStreamState.CANCEL_REQUESTED,
                VoiceStreamState.FAILED,
            }
        ),
        VoiceStreamState.PROCESSING: frozenset(
            {
                VoiceStreamState.STREAMING,
                VoiceStreamState.OUTPUT_STREAMING,
                VoiceStreamState.CANCEL_REQUESTED,
                VoiceStreamState.FAILED,
            }
        ),
        VoiceStreamState.OUTPUT_STREAMING: frozenset(
            {
                VoiceStreamState.STREAMING,
                VoiceStreamState.CANCEL_REQUESTED,
                VoiceStreamState.FAILED,
            }
        ),
        VoiceStreamState.CANCEL_REQUESTED: frozenset(
            {
                VoiceStreamState.CANCELLED,
                VoiceStreamState.FAILED,
            }
        ),
        VoiceStreamState.FAILED: frozenset(),
        VoiceStreamState.CANCELLED: frozenset(),
    }

    @classmethod
    def validate(
        cls,
        current: VoiceStreamState,
        target: VoiceStreamState,
    ) -> None:
        """Reject any transition not explicitly permitted."""
        if target not in cls._TRANSITIONS.get(current, frozenset()):
            raise ValueError(f"invalid voice stream transition: {current} -> {target}")

    @classmethod
    def is_allowed(
        cls,
        current: VoiceStreamState,
        target: VoiceStreamState,
    ) -> bool:
        """Return whether a transition is permitted."""
        return target in cls._TRANSITIONS.get(current, frozenset())
