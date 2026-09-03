from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lyrion.voice.contracts import VoiceIdentityProfile, VoiceIdentityProfileStatus


def make_profile() -> VoiceIdentityProfile:
    now = datetime.now(UTC)
    return VoiceIdentityProfile(
        identity_id="person-1",
        status=VoiceIdentityProfileStatus.PENDING,
        representation_refs=("rep-1",),
        enrolled_at=now,
        updated_at=now,
        provenance="test",
    )


def test_profile_revision_defaults_to_one() -> None:
    profile = make_profile()
    assert profile.revision == 1


def test_profile_rejects_non_positive_revision() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        VoiceIdentityProfile(
            identity_id="person-1",
            status=VoiceIdentityProfileStatus.PENDING,
            representation_refs=("rep-1",),
            enrolled_at=now,
            updated_at=now,
            provenance="test",
            revision=0,
        )
