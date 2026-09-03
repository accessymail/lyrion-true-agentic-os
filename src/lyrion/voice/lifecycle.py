"""Voice Identity profile lifecycle policy."""

from __future__ import annotations

from lyrion.voice.contracts import VoiceIdentityProfileStatus


class VoiceIdentityProfileTransitionPolicy:
    """Explicit policy boundary for profile lifecycle transitions."""

    def __init__(
        self,
        allowed_transitions: dict[
            VoiceIdentityProfileStatus,
            frozenset[VoiceIdentityProfileStatus],
        ],
    ) -> None:
        self._allowed_transitions = allowed_transitions

    def is_allowed(
        self,
        current: VoiceIdentityProfileStatus,
        target: VoiceIdentityProfileStatus,
    ) -> bool:
        """Return whether a lifecycle transition is explicitly allowed."""
        return target in self._allowed_transitions.get(current, frozenset())

    def validate(
        self,
        current: VoiceIdentityProfileStatus,
        target: VoiceIdentityProfileStatus,
    ) -> None:
        """Raise when the requested transition is not explicitly allowed."""
        if not self.is_allowed(current, target):
            raise ValueError(
                f"lifecycle transition {current.value} -> {target.value} is not allowed"
            )
