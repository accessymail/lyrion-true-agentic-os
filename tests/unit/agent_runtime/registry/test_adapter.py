from uuid import uuid4

import pytest

from lyrion.agent_runtime.contracts.agent import AgentIdentity
from lyrion.agent_runtime.registry.adapter import AgentIdentityAdapter


def make_identity() -> AgentIdentity:
    return AgentIdentity(
        agent_id=uuid4(),
        agent_type="research-agent",
        instance_name="research-001",
        version="1.0.0",
    )


def test_runtime_identity_translates_to_harness_identity() -> None:
    identity = make_identity()

    result = AgentIdentityAdapter().to_harness_identity(
        identity,
        identity_provenance_ref="registry://research-agent/1",
    )

    assert result.agent_id == str(identity.agent_id)
    assert result.identity_provenance_ref == "registry://research-agent/1"


def test_identity_translation_is_deterministic() -> None:
    identity = make_identity()
    adapter = AgentIdentityAdapter()

    first = adapter.to_harness_identity(
        identity,
        identity_provenance_ref="registry://research-agent/1",
    )
    second = adapter.to_harness_identity(
        identity,
        identity_provenance_ref="registry://research-agent/1",
    )

    assert first == second


@pytest.mark.parametrize(
    "provenance_ref",
    ["", "   ", "\t"],
)
def test_blank_provenance_reference_is_rejected(
    provenance_ref: str,
) -> None:
    with pytest.raises(ValueError):
        AgentIdentityAdapter().to_harness_identity(
            make_identity(),
            identity_provenance_ref=provenance_ref,
        )


def test_adapter_does_not_expose_security_authority() -> None:
    adapter = AgentIdentityAdapter()

    assert not hasattr(adapter, "authorize")
    assert not hasattr(adapter, "grant_capability")
    assert not hasattr(adapter, "create_admission")
    assert not hasattr(adapter, "execute")
    assert not hasattr(adapter, "secure_executor")


def test_runtime_metadata_is_not_promoted_to_harness_authority() -> None:
    identity = make_identity()

    result = AgentIdentityAdapter().to_harness_identity(
        identity,
        identity_provenance_ref="registry://research-agent/1",
    )

    assert result.agent_id == str(identity.agent_id)
    assert not hasattr(result, "authorization")
    assert not hasattr(result, "capability_grant")
    assert not hasattr(result, "delegated_authority")
    assert not hasattr(result, "execution_admission")
