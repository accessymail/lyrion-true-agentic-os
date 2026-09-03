from __future__ import annotations

import pytest

from lyrion.voice.contracts import (
    VoiceIdentityMatch,
    VoiceIdentityRequest,
    VoiceIdentityStatus,
)
from lyrion.voice.identity import VoiceIdentityService


class FakeVoiceIdentityProvider:
    def __init__(self, result: VoiceIdentityMatch) -> None:
        self.result = result
        self.requests: list[VoiceIdentityRequest] = []

    async def identify(self, request: VoiceIdentityRequest) -> VoiceIdentityMatch:
        self.requests.append(request)
        return self.result


def make_request() -> VoiceIdentityRequest:
    return VoiceIdentityRequest(
        request_id="voice-1",
        audio_ref="audio://sample-1",
        session_id="session-1",
    )


def test_voice_identity_match_contract() -> None:
    result = VoiceIdentityMatch(
        request_id="voice-1",
        status=VoiceIdentityStatus.KNOWN,
        identity_id="person-1",
        confidence=0.97,
        evidence_ref="evidence://voice-1",
        provider="test",
    )
    assert result.identity_id == "person-1"
    assert result.confidence == 0.97


def test_unknown_identity_does_not_require_identity_id() -> None:
    result = VoiceIdentityMatch(
        request_id="voice-1",
        status=VoiceIdentityStatus.UNKNOWN,
    )
    assert result.identity_id is None
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_identity_service_delegates_and_preserves_request_id() -> None:
    request = make_request()
    result = VoiceIdentityMatch(
        request_id=request.request_id,
        status=VoiceIdentityStatus.KNOWN,
        identity_id="person-1",
        confidence=0.91,
    )
    provider = FakeVoiceIdentityProvider(result)
    service = VoiceIdentityService(provider)

    actual = await service.identify(request)

    assert actual == result
    assert provider.requests == [request]


@pytest.mark.asyncio
async def test_identity_service_rejects_provider_request_mismatch() -> None:
    request = make_request()
    result = VoiceIdentityMatch(
        request_id="different-request",
        status=VoiceIdentityStatus.KNOWN,
        identity_id="person-1",
        confidence=0.91,
    )
    service = VoiceIdentityService(FakeVoiceIdentityProvider(result))

    with pytest.raises(ValueError, match="mismatched request_id"):
        await service.identify(request)
