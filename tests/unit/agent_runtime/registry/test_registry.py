from uuid import uuid4

import pytest

from lyrion.agent_runtime.contracts.agent import (
    AgentIdentity,
    AgentRegistration,
    AgentTrustState,
)
from lyrion.agent_runtime.registry import AgentRegistry, AgentRegistryError


def make_registration(
    *,
    revision: int = 1,
    trust_state: AgentTrustState = AgentTrustState.UNKNOWN,
) -> AgentRegistration:
    return AgentRegistration(
        identity=AgentIdentity(
            agent_type="research-agent",
            instance_name="research-001",
            version="1.0.0",
        ),
        trust_state=trust_state,
        declared_capabilities=("research.read",),
        registration_revision=revision,
    )


def test_register_and_lookup() -> None:
    registry = AgentRegistry()
    registration = make_registration()

    result = registry.register(registration)

    assert result == registration
    assert registry.get(registration.identity.agent_id) == registration
    assert registry.contains(registration.identity.agent_id)


def test_duplicate_identical_registration_is_idempotent() -> None:
    registry = AgentRegistry()
    registration = make_registration()

    registry.register(registration)

    assert registry.register(registration) == registration


def test_conflicting_duplicate_registration_is_rejected() -> None:
    registry = AgentRegistry()
    registration = make_registration()

    registry.register(registration)

    conflicting = registration.model_copy(
        update={"trust_state": AgentTrustState.EVALUATING}
    )

    with pytest.raises(AgentRegistryError):
        registry.register(conflicting)


def test_revision_must_increase_for_replacement() -> None:
    registry = AgentRegistry()
    registration = make_registration()
    registry.register(registration)

    stale = make_registration()
    stale = stale.model_copy(
        update={"identity": registration.identity}
    )

    with pytest.raises(AgentRegistryError):
        registry.replace(stale)


def test_replacement_with_higher_revision_is_allowed() -> None:
    registry = AgentRegistry()
    registration = make_registration()
    registry.register(registration)

    updated = registration.model_copy(
        update={
            "registration_revision": 2,
            "trust_state": AgentTrustState.EVALUATING,
        }
    )

    result = registry.replace(updated)

    assert result.registration_revision == 2
    assert result.trust_state is AgentTrustState.EVALUATING


def test_unregistered_lookup_fails_closed() -> None:
    registry = AgentRegistry()

    with pytest.raises(AgentRegistryError):
        registry.get(uuid4())


def test_unregister_removes_registration() -> None:
    registry = AgentRegistry()
    registration = make_registration()

    registry.register(registration)

    removed = registry.unregister(registration.identity.agent_id)

    assert removed == registration
    assert not registry.contains(registration.identity.agent_id)


def test_trust_state_is_metadata_only() -> None:
    registry = AgentRegistry()
    registration = make_registration()

    registry.register(registration)

    updated = registry.set_trust_state(
        registration.identity.agent_id,
        AgentTrustState.TRUSTED,
    )

    assert updated.trust_state is AgentTrustState.TRUSTED
    assert updated.registration_revision == 2


def test_snapshot_is_deterministic_and_immutable() -> None:
    registry = AgentRegistry()

    first = make_registration()
    second = make_registration()

    registry.register(first)
    registry.register(second)

    snapshot = registry.snapshot()

    assert len(snapshot) == 2
    assert tuple(
        sorted(
            str(item.registration.identity.agent_id)
            for item in snapshot
        )
    ) == tuple(
        str(item.registration.identity.agent_id)
        for item in snapshot
    )


def test_registration_does_not_expose_security_authority() -> None:
    registration = make_registration()

    assert not hasattr(registration, "authorization")
    assert not hasattr(registration, "execution_admission")
    assert not hasattr(registration, "delegated_authority")
    assert not hasattr(registration, "capability_grant")
