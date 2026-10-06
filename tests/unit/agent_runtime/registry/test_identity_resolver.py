from uuid import UUID, uuid4

import pytest

from lyrion.agent_harness.contracts import AgentIdentity as HarnessAgentIdentity
from lyrion.agent_runtime.contracts.agent import (
    AgentIdentity,
    AgentRegistration,
)
from lyrion.agent_runtime.registry import AgentRegistry
from lyrion.agent_runtime.registry.identity_resolver import (
    AgentHarnessIdentityResolver,
    AgentIdentityResolutionError,
)


def make_registration() -> AgentRegistration:
    return AgentRegistration(
        identity=AgentIdentity(
            agent_type="research-agent",
            instance_name="research-001",
            version="1.0.0",
        ),
        declared_capabilities=("research.read",),
    )


def test_registered_runtime_identity_resolves_to_harness_identity() -> None:
    registry = AgentRegistry()
    registration = make_registration()
    registry.register(registration)

    resolver = AgentHarnessIdentityResolver(registry=registry)

    result = resolver.resolve(
        registration.identity.agent_id,
        identity_provenance_ref="registry://research-agent/1",
    )

    assert isinstance(result, HarnessAgentIdentity)
    assert result.agent_id == str(registration.identity.agent_id)
    assert result.identity_provenance_ref == "registry://research-agent/1"


def test_resolution_is_deterministic() -> None:
    registry = AgentRegistry()
    registration = make_registration()
    registry.register(registration)

    resolver = AgentHarnessIdentityResolver(registry=registry)

    first = resolver.resolve(
        registration.identity.agent_id,
        identity_provenance_ref="registry://research-agent/1",
    )
    second = resolver.resolve(
        registration.identity.agent_id,
        identity_provenance_ref="registry://research-agent/1",
    )

    assert first == second


def test_unregistered_agent_fails_closed() -> None:
    registry = AgentRegistry()
    resolver = AgentHarnessIdentityResolver(registry=registry)

    with pytest.raises(AgentIdentityResolutionError):
        resolver.resolve(
            uuid4(),
            identity_provenance_ref="registry://unknown/1",
        )


@pytest.mark.parametrize(
    "provenance_ref",
    [
        "",
        " ",
        "\t",
        "\n",
    ],
)
def test_blank_identity_provenance_fails_closed(
    provenance_ref: str,
) -> None:
    registry = AgentRegistry()
    registration = make_registration()
    registry.register(registration)

    resolver = AgentHarnessIdentityResolver(registry=registry)

    with pytest.raises(AgentIdentityResolutionError):
        resolver.resolve(
            registration.identity.agent_id,
            identity_provenance_ref=provenance_ref,
        )


def test_identity_resolution_does_not_promote_registration_capabilities() -> None:
    registry = AgentRegistry()
    registration = make_registration()
    registry.register(registration)

    resolver = AgentHarnessIdentityResolver(registry=registry)

    result = resolver.resolve(
        registration.identity.agent_id,
        identity_provenance_ref="registry://research-agent/1",
    )

    assert not hasattr(result, "authorization")
    assert not hasattr(result, "capability_grant")
    assert not hasattr(result, "delegated_authority")
    assert not hasattr(result, "execution_admission")


def test_identity_resolution_exposes_no_execution_api() -> None:
    registry = AgentRegistry()
    registration = make_registration()
    registry.register(registration)

    resolver = AgentHarnessIdentityResolver(registry=registry)

    assert not hasattr(resolver, "authorize")
    assert not hasattr(resolver, "grant_capability")
    assert not hasattr(resolver, "create_admission")
    assert not hasattr(resolver, "execute")
    assert not hasattr(resolver, "secure_executor")
    assert not hasattr(resolver, "lhicf")
    assert not hasattr(resolver, "host")


def test_resolved_harness_identity_contains_only_identity_attribution() -> None:
    registry = AgentRegistry()
    registration = make_registration()
    registry.register(registration)

    resolver = AgentHarnessIdentityResolver(registry=registry)

    result = resolver.resolve(
        registration.identity.agent_id,
        identity_provenance_ref="registry://research-agent/1",
    )

    assert set(type(result).model_fields) == {
        "agent_id",
        "identity_provenance_ref",
    }


def test_uuid_identity_is_preserved_exactly() -> None:
    registry = AgentRegistry()
    registration = make_registration()
    registry.register(registration)

    resolver = AgentHarnessIdentityResolver(registry=registry)

    result = resolver.resolve(
        UUID(str(registration.identity.agent_id)),
        identity_provenance_ref="registry://research-agent/1",
    )

    assert result.agent_id == str(registration.identity.agent_id)
