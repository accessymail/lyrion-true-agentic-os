import asyncio
from datetime import UTC, datetime

import pytest

from lyrion.voice.contracts import (
    VoiceIdentityProfile,
    VoiceIdentityProfileStatus,
    VoiceIdentityProfileUpdateRequest,
)
from lyrion.voice.lifecycle import VoiceIdentityProfileTransitionPolicy
from lyrion.voice.profile import (
    VoiceIdentityProfileConflictError,
    VoiceIdentityProfileService,
)


class InMemoryProfileStore:
    def __init__(self) -> None:
        self._profiles: dict[str, VoiceIdentityProfile] = {}
        self._lock = asyncio.Lock()

    async def get(self, identity_id: str) -> VoiceIdentityProfile | None:
        return self._profiles.get(identity_id)

    async def create(self, profile: VoiceIdentityProfile) -> VoiceIdentityProfile:
        async with self._lock:
            if profile.identity_id in self._profiles:
                raise VoiceIdentityProfileConflictError("voice identity profile already exists")
            self._profiles[profile.identity_id] = profile
            return profile

    async def update(
        self,
        profile: VoiceIdentityProfile,
        *,
        expected_revision: int,
    ) -> VoiceIdentityProfile:
        async with self._lock:
            current = self._profiles.get(profile.identity_id)
            if current is None:
                raise ValueError("voice identity profile not found")
            if current.revision != expected_revision:
                raise VoiceIdentityProfileConflictError(
                    "voice identity profile revision conflict"
                )
            if profile.revision != expected_revision + 1:
                raise ValueError(
                    "profile revision must advance by exactly one"
                )
            self._profiles[profile.identity_id] = profile
            return profile
    async def transition(
        self,
        identity_id: str,
        *,
        expected_revision: int,
        profile: VoiceIdentityProfile,
    ) -> VoiceIdentityProfile:
        current = self._profiles.get(identity_id)
        if current is None:
            raise ValueError("voice identity profile not found")
        if current.revision != expected_revision:
            raise VoiceIdentityProfileConflictError("voice identity profile revision conflict")
        if profile.revision != expected_revision + 1:
            raise ValueError("profile revision must advance by exactly one")
        self._profiles[identity_id] = profile
        return profile


def make_policy(
    *allowed: tuple[VoiceIdentityProfileStatus, VoiceIdentityProfileStatus],
) -> VoiceIdentityProfileTransitionPolicy:
    transitions: dict[
        VoiceIdentityProfileStatus,
        frozenset[VoiceIdentityProfileStatus],
    ] = {}
    for current, target in allowed:
        transitions[current] = transitions.get(current, frozenset()) | frozenset({target})
    return VoiceIdentityProfileTransitionPolicy(transitions)


def make_profile(identity_id: str = "person-1") -> VoiceIdentityProfile:
    now = datetime.now(UTC)
    return VoiceIdentityProfile(
        identity_id=identity_id,
        status=VoiceIdentityProfileStatus.PENDING,
        representation_refs=("rep-1",),
        enrolled_at=now,
        updated_at=now,
        provenance="test",
    )


def make_service(
    store: InMemoryProfileStore,
    *allowed: tuple[VoiceIdentityProfileStatus, VoiceIdentityProfileStatus],
) -> VoiceIdentityProfileService:
    return VoiceIdentityProfileService(store, make_policy(*allowed))


@pytest.mark.asyncio
async def test_register_and_get_profile() -> None:
    store = InMemoryProfileStore()
    service = make_service(store)
    profile = make_profile()

    result = await service.register(profile)

    assert result is profile
    assert await service.get("person-1") is profile


@pytest.mark.asyncio
async def test_register_rejects_duplicate_identity() -> None:
    store = InMemoryProfileStore()
    service = make_service(store)
    profile = make_profile()

    await service.register(profile)
    with pytest.raises(VoiceIdentityProfileConflictError, match="already exists"):
        await service.register(profile)


@pytest.mark.asyncio
async def test_concurrent_registration_has_single_winner() -> None:
    store = InMemoryProfileStore()
    service = make_service(store)
    profiles = [make_profile() for _ in range(8)]

    results = await asyncio.gather(
        *(service.register(profile) for profile in profiles),
        return_exceptions=True,
    )

    successes = [result for result in results if isinstance(result, VoiceIdentityProfile)]
    conflicts = [
        result for result in results if isinstance(result, VoiceIdentityProfileConflictError)
    ]

    assert len(successes) == 1
    assert len(conflicts) == 7
    assert await service.get("person-1") is successes[0]

@pytest.mark.asyncio
async def test_get_rejects_blank_identity_id() -> None:
    service = make_service(InMemoryProfileStore())

    with pytest.raises(ValueError, match="must not be blank"):
        await service.get("   ")


@pytest.mark.asyncio
async def test_register_passes_profile_to_store_unchanged() -> None:
    store = InMemoryProfileStore()
    service = make_service(store)
    profile = make_profile("person-42")

    result = await service.register(profile)

    assert result is profile
    assert store._profiles["person-42"] is profile


@pytest.mark.asyncio
async def test_transition_creates_new_immutable_profile() -> None:
    store = InMemoryProfileStore()
    service = make_service(
        store,
        (VoiceIdentityProfileStatus.PENDING, VoiceIdentityProfileStatus.ACTIVE),
    )
    original = make_profile()
    await service.register(original)

    updated = await service.transition("person-1", VoiceIdentityProfileStatus.ACTIVE)

    assert updated.status is VoiceIdentityProfileStatus.ACTIVE
    assert updated.identity_id == original.identity_id
    assert updated.representation_refs == original.representation_refs
    assert updated.enrolled_at == original.enrolled_at
    assert updated.updated_at >= original.updated_at
    assert updated is not original
    assert updated.revision == original.revision + 1
    assert await service.get("person-1") is updated


@pytest.mark.asyncio
async def test_transition_rejects_policy_violation() -> None:
    store = InMemoryProfileStore()
    service = make_service(store)
    original = make_profile()
    await service.register(original)

    with pytest.raises(ValueError, match="not allowed"):
        await service.transition("person-1", VoiceIdentityProfileStatus.ACTIVE)

    assert await service.get("person-1") is original


@pytest.mark.asyncio
async def test_transition_rejects_missing_profile() -> None:
    service = make_service(InMemoryProfileStore())

    with pytest.raises(ValueError, match="not found"):
        await service.transition("missing", VoiceIdentityProfileStatus.ACTIVE)


@pytest.mark.asyncio
async def test_transition_preserves_representation_and_provenance() -> None:
    store = InMemoryProfileStore()
    service = make_service(
        store,
        (VoiceIdentityProfileStatus.PENDING, VoiceIdentityProfileStatus.DISABLED),
    )
    original = make_profile()
    await service.register(original)

    updated = await service.transition("person-1", VoiceIdentityProfileStatus.DISABLED)

    assert updated.representation_refs == original.representation_refs
    assert updated.provenance == original.provenance


class ConflictingProfileStore(InMemoryProfileStore):
    async def transition(
        self,
        identity_id: str,
        *,
        expected_revision: int,
        profile: VoiceIdentityProfile,
    ) -> VoiceIdentityProfile:
        raise VoiceIdentityProfileConflictError("voice identity profile revision conflict")


@pytest.mark.asyncio
async def test_transition_propagates_revision_conflict() -> None:
    store = ConflictingProfileStore()
    service = make_service(
        store,
        (VoiceIdentityProfileStatus.PENDING, VoiceIdentityProfileStatus.ACTIVE),
    )
    original = make_profile()
    await service.register(original)

    with pytest.raises(VoiceIdentityProfileConflictError, match="revision conflict"):
        await service.transition("person-1", VoiceIdentityProfileStatus.ACTIVE)

    assert await service.get("person-1") is original


@pytest.mark.asyncio
async def test_update_changes_representation_refs() -> None:
    store = InMemoryProfileStore()
    service = make_service(store)
    original = make_profile()
    await service.register(original)

    updated = await service.update(
        VoiceIdentityProfileUpdateRequest(
            identity_id="person-1",
            expected_revision=1,
            representation_refs=("rep-2", "rep-3"),
        )
    )

    assert updated.representation_refs == ("rep-2", "rep-3")
    assert updated.provenance == original.provenance
    assert updated.status is original.status
    assert updated.revision == 2
    assert updated is not original


@pytest.mark.asyncio
async def test_update_changes_provenance_only() -> None:
    store = InMemoryProfileStore()
    service = make_service(store)
    original = make_profile()
    await service.register(original)

    updated = await service.update(
        VoiceIdentityProfileUpdateRequest(
            identity_id="person-1",
            expected_revision=1,
            provenance="updated-provenance",
        )
    )

    assert updated.provenance == "updated-provenance"
    assert updated.representation_refs == original.representation_refs
    assert updated.revision == 2


@pytest.mark.asyncio
async def test_update_rejects_stale_revision() -> None:
    store = InMemoryProfileStore()
    service = make_service(store)
    original = make_profile()
    await service.register(original)

    updated = await service.update(
        VoiceIdentityProfileUpdateRequest(
            identity_id="person-1",
            expected_revision=1,
            provenance="first-update",
        )
    )
    assert updated.revision == 2

    with pytest.raises(VoiceIdentityProfileConflictError, match="revision conflict"):
        await service.update(
            VoiceIdentityProfileUpdateRequest(
                identity_id="person-1",
                expected_revision=1,
                provenance="stale-update",
            )
        )

    assert (await service.get("person-1")).revision == 2


@pytest.mark.asyncio
async def test_update_missing_fields_preserves_existing_values() -> None:
    store = InMemoryProfileStore()
    service = make_service(store)
    original = make_profile()
    await service.register(original)

    updated = await service.update(
        VoiceIdentityProfileUpdateRequest(
            identity_id="person-1",
            expected_revision=1,
        )
    )

    assert updated.representation_refs == original.representation_refs
    assert updated.provenance == original.provenance
    assert updated.revision == 2
    assert updated.updated_at >= original.updated_at


@pytest.mark.asyncio
async def test_active_profile_cannot_remove_all_representations() -> None:
    store = InMemoryProfileStore()
    service = make_service(store)
    original = make_profile()
    await service.register(original)
    active = VoiceIdentityProfile(
        identity_id=original.identity_id,
        status=VoiceIdentityProfileStatus.ACTIVE,
        representation_refs=original.representation_refs,
        enrolled_at=original.enrolled_at,
        updated_at=original.updated_at,
        provenance=original.provenance,
        revision=2,
    )
    store._profiles["person-1"] = active

    with pytest.raises(ValueError, match="ACTIVE profiles require"):
        await service.update(
            VoiceIdentityProfileUpdateRequest(
                identity_id="person-1",
                expected_revision=2,
                representation_refs=(),
            )
        )


@pytest.mark.asyncio
async def test_update_is_single_winner_under_concurrent_writers() -> None:
    store = InMemoryProfileStore()
    service = make_service(store)
    await service.register(make_profile())

    requests = [
        VoiceIdentityProfileUpdateRequest(
            identity_id="person-1",
            expected_revision=1,
            provenance=f"writer-{index}",
        )
        for index in range(8)
    ]

    results = await asyncio.gather(
        *(service.update(request) for request in requests),
        return_exceptions=True,
    )

    successes = [
        result for result in results if isinstance(result, VoiceIdentityProfile)
    ]
    conflicts = [
        result
        for result in results
        if isinstance(result, VoiceIdentityProfileConflictError)
    ]

    assert len(successes) == 1
    assert len(conflicts) == 7
    assert (await service.get("person-1")).revision == 2
