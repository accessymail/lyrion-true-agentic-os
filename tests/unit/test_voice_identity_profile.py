from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lyrion.voice.contracts import (
    VoiceIdentityProfile,
    VoiceIdentityProfileStatus,
)


def test_active_profile_requires_representation() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        VoiceIdentityProfile(
            identity_id="person-1",
            status=VoiceIdentityProfileStatus.ACTIVE,
            enrolled_at=now,
            updated_at=now,
            provenance="test",
        )


def test_profile_rejects_duplicate_representations() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        VoiceIdentityProfile(
            identity_id="person-1",
            status=VoiceIdentityProfileStatus.PENDING,
            representation_refs=("rep-1", "rep-1"),
            enrolled_at=now,
            updated_at=now,
            provenance="test",
        )


def test_profile_rejects_backwards_timestamp() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        VoiceIdentityProfile(
            identity_id="person-1",
            status=VoiceIdentityProfileStatus.PENDING,
            enrolled_at=now,
            updated_at=now - timedelta(seconds=1),
            provenance="test",
        )


def test_profile_is_immutable() -> None:
    now = datetime.now(UTC)
    profile = VoiceIdentityProfile(
        identity_id="person-1",
        status=VoiceIdentityProfileStatus.ACTIVE,
        representation_refs=("rep-1",),
        enrolled_at=now,
        updated_at=now,
        provenance="test",
    )
    with pytest.raises(ValidationError):
        profile.status = VoiceIdentityProfileStatus.DISABLED
