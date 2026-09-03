"""Voice Identity profile management service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from lyrion.voice.contracts import (
    VoiceIdentityProfile,
    VoiceIdentityProfileStatus,
    VoiceIdentityProfileUpdateRequest,
)
from lyrion.voice.lifecycle import VoiceIdentityProfileTransitionPolicy


class VoiceIdentityProfileConflictError(ValueError):
    """Raised when a voice identity profile already exists or conflicts."""


class VoiceIdentityProfileStore(Protocol):
    """Persistence-neutral boundary for voice identity profiles."""

    async def get(self, identity_id: str) -> VoiceIdentityProfile | None:
        """Return a profile by identity ID, or None when absent."""

    async def create(self, profile: VoiceIdentityProfile) -> VoiceIdentityProfile:
        """Atomically create one profile and reject duplicate identity IDs."""

    async def update(
        self,
        profile: VoiceIdentityProfile,
        *,
        expected_revision: int,
    ) -> VoiceIdentityProfile:
        """Atomically persist one revision-checked profile update."""

    async def transition(
        self,
        identity_id: str,
        *,
        expected_revision: int,
        profile: VoiceIdentityProfile,
    ) -> VoiceIdentityProfile:
        """Atomically persist one optimistic-concurrency transition."""


class VoiceIdentityProfileService:
    """Manage voice identity profiles through a provider-neutral store."""

    def __init__(
        self,
        store: VoiceIdentityProfileStore,
        transition_policy: VoiceIdentityProfileTransitionPolicy,
    ) -> None:
        self._store = store
        self._transition_policy = transition_policy

    @property
    def store(self) -> VoiceIdentityProfileStore:
        """Return the configured profile store."""
        return self._store

    @property
    def transition_policy(self) -> VoiceIdentityProfileTransitionPolicy:
        """Return the configured lifecycle transition policy."""
        return self._transition_policy

    async def get(self, identity_id: str) -> VoiceIdentityProfile | None:
        """Retrieve one profile by identity ID."""
        if not identity_id.strip():
            raise ValueError("identity_id must not be blank")
        return await self._store.get(identity_id)

    async def register(self, profile: VoiceIdentityProfile) -> VoiceIdentityProfile:
        """Atomically register one new profile."""
        return await self._store.create(profile)

    async def update(
        self,
        request: VoiceIdentityProfileUpdateRequest,
    ) -> VoiceIdentityProfile:
        """Apply one revision-checked profile metadata update."""
        current = await self.get(request.identity_id)
        if current is None:
            raise ValueError("voice identity profile not found")
        if current.revision != request.expected_revision:
            raise VoiceIdentityProfileConflictError(
                "voice identity profile revision conflict"
            )

        updated = VoiceIdentityProfile(
            identity_id=current.identity_id,
            status=current.status,
            representation_refs=(
                current.representation_refs
                if request.representation_refs is None
                else request.representation_refs
            ),
            enrolled_at=current.enrolled_at,
            updated_at=datetime.now(UTC),
            provenance=(
                current.provenance
                if request.provenance is None
                else request.provenance
            ),
            revision=current.revision + 1,
        )
        return await self._store.update(
            updated,
            expected_revision=request.expected_revision,
        )

    async def transition(
        self,
        identity_id: str,
        target_status: VoiceIdentityProfileStatus,
    ) -> VoiceIdentityProfile:
        """Apply one explicitly authorized lifecycle transition."""
        current = await self.get(identity_id)
        if current is None:
            raise ValueError("voice identity profile not found")

        self._transition_policy.validate(current.status, target_status)

        now = datetime.now(UTC)
        updated = VoiceIdentityProfile(
            identity_id=current.identity_id,
            status=target_status,
            representation_refs=current.representation_refs,
            enrolled_at=current.enrolled_at,
            updated_at=now,
            provenance=current.provenance,
            revision=current.revision + 1,
        )
        return await self._store.transition(
            identity_id,
            expected_revision=current.revision,
            profile=updated,
        )
