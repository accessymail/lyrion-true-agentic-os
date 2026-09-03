from __future__ import annotations

import pytest
from pydantic import ValidationError

from lyrion.voice.contracts import (
    VoiceIdentityMatch,
    VoiceIdentityRequest,
    VoiceIdentityStatus,
)


def test_known_identity_requires_identity_id() -> None:
    with pytest.raises(ValidationError):
        VoiceIdentityMatch(
            request_id="voice-1",
            status=VoiceIdentityStatus.KNOWN,
            confidence=0.91,
        )


def test_unknown_identity_cannot_have_identity_id() -> None:
    with pytest.raises(ValidationError):
        VoiceIdentityMatch(
            request_id="voice-1",
            status=VoiceIdentityStatus.UNKNOWN,
            identity_id="person-1",
            confidence=0.91,
        )


def test_identity_request_is_immutable() -> None:
    request = VoiceIdentityRequest(
        request_id="voice-1",
        audio_ref="audio://sample-1",
    )
    with pytest.raises(ValidationError):
        request.audio_ref = "audio://changed"


def test_identity_match_is_immutable() -> None:
    result = VoiceIdentityMatch(
        request_id="voice-1",
        status=VoiceIdentityStatus.UNKNOWN,
    )
    with pytest.raises(ValidationError):
        result.confidence = 1.0
