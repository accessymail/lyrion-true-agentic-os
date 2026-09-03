from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lyrion.voice.contracts import (
    VoiceEvidenceQuality,
    VoiceIdentityEvidence,
    VoiceIdentityProfile,
    VoiceIdentityProfileStatus,
)


def make_profile() -> VoiceIdentityProfile:
    now = datetime.now(UTC)
    return VoiceIdentityProfile(
        identity_id="person-1",
        status=VoiceIdentityProfileStatus.ACTIVE,
        representation_refs=("rep-1",),
        enrolled_at=now,
        updated_at=now,
        provenance="test",
    )


def test_profile_rejects_blank_identity_id() -> None:
    with pytest.raises(ValidationError):
        VoiceIdentityProfile(
            identity_id="   ",
            status=VoiceIdentityProfileStatus.PENDING,
            enrolled_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            provenance="test",
        )


def test_profile_rejects_blank_representation_reference() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        VoiceIdentityProfile(
            identity_id="person-1",
            status=VoiceIdentityProfileStatus.ACTIVE,
            representation_refs=("   ",),
            enrolled_at=now,
            updated_at=now,
            provenance="test",
        )


def test_profile_rejects_blank_provenance() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        VoiceIdentityProfile(
            identity_id="person-1",
            status=VoiceIdentityProfileStatus.PENDING,
            enrolled_at=now,
            updated_at=now,
            provenance="   ",
        )


def test_evidence_rejects_blank_reference() -> None:
    with pytest.raises(ValidationError):
        VoiceIdentityEvidence(
            evidence_ref="   ",
            quality=VoiceEvidenceQuality.HIGH,
            duration_seconds=1.0,
            signal_confidence=0.9,
        )


def test_valid_profile_still_constructs() -> None:
    profile = make_profile()
    assert profile.identity_id == "person-1"
