"""Unit tests for the 19.4.3 Voice Cloning boundary."""

from datetime import UTC, datetime

import pytest

from lyrion.voice.cloning import (
    VoiceCloneOutputFormat,
    VoiceCloneRequest,
    VoiceCloneResult,
    VoiceCloneService,
)


class FakeVoiceCloneProvider:
    """Deterministic provider used only for unit testing."""

    def __init__(self) -> None:
        self.requests: list[VoiceCloneRequest] = []

    async def clone(self, request: VoiceCloneRequest) -> VoiceCloneResult:
        self.requests.append(request)

        return VoiceCloneResult(
            clone_id="clone-1",
            identity_id=request.identity_id,
            representation_ref="voice-clone://clone-1",
            provider="test-provider",
            provider_model="test-model",
            output_format=request.output_format,
            created_at=datetime.now(UTC),
            provenance=request.provenance,
        )


@pytest.fixture
def voice_clone_request() -> VoiceCloneRequest:
    return VoiceCloneRequest(
        identity_id="person-1",
        source_representation_ref="voice-source://representation-1",
        consent_evidence_ref="consent://evidence-1",
        locale="en-IN",
        output_format=VoiceCloneOutputFormat.WAV,
        max_duration_seconds=30,
        provenance="user-authorized voice cloning request",
    )


@pytest.mark.asyncio
async def test_create_clone_delegates_through_provider_boundary(
    voice_clone_request: VoiceCloneRequest,
) -> None:
    provider = FakeVoiceCloneProvider()
    service = VoiceCloneService(provider)

    result = await service.create_clone(voice_clone_request)

    assert result.clone_id == "clone-1"
    assert result.identity_id == "person-1"
    assert result.provider == "test-provider"
    assert provider.requests == [voice_clone_request]


def test_request_is_immutable() -> None:
    voice_clone_request = VoiceCloneRequest(
        identity_id="person-1",
        source_representation_ref="voice-source://1",
        consent_evidence_ref="consent://1",
        provenance="authorized test request",
    )

    with pytest.raises(AttributeError):
        voice_clone_request.identity_id = "person-2"  # type: ignore[misc]


def test_request_rejects_blank_consent_reference() -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        VoiceCloneRequest(
            identity_id="person-1",
            source_representation_ref="voice-source://1",
            consent_evidence_ref="   ",
            provenance="authorized test request",
        )


def test_request_rejects_blank_source_reference() -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        VoiceCloneRequest(
            identity_id="person-1",
            source_representation_ref="   ",
            consent_evidence_ref="consent://1",
            provenance="authorized test request",
        )


def test_duration_is_bounded() -> None:
    with pytest.raises(ValueError):
        VoiceCloneRequest(
            identity_id="person-1",
            source_representation_ref="voice-source://1",
            consent_evidence_ref="consent://1",
            max_duration_seconds=301,
            provenance="authorized test request",
        )


def test_result_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        VoiceCloneResult(
            clone_id="clone-1",
            identity_id="person-1",
            representation_ref="voice-clone://1",
            provider="test-provider",
            output_format=VoiceCloneOutputFormat.WAV,
            created_at=datetime.now(),
            provenance="test provenance",
        )


@pytest.mark.asyncio
async def test_provider_identity_mismatch_is_rejected(
    voice_clone_request: VoiceCloneRequest,
) -> None:
    class MismatchingProvider:
        async def clone(self, request: VoiceCloneRequest) -> VoiceCloneResult:
            return VoiceCloneResult(
                clone_id="clone-1",
                identity_id="different-person",
                representation_ref="voice-clone://1",
                provider="test-provider",
                output_format=voice_clone_request.output_format,
                created_at=datetime.now(UTC),
                provenance=voice_clone_request.provenance,
            )

    service = VoiceCloneService(MismatchingProvider())

    with pytest.raises(ValueError, match="unexpected identity"):
        await service.create_clone(voice_clone_request)
