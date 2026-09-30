"""Adversarial tests for the PB-DOC-005 Agent Isolation Contract."""

import pytest
from pydantic import ValidationError

from lyrion.agent_harness.isolation import AgentIsolationContract


def make_contract() -> AgentIsolationContract:
    return AgentIsolationContract(
        agent_id="agent:test",
        task_id="task:test",
    )


def test_default_isolation_contract_is_fully_enabled() -> None:
    contract = make_contract()

    assert contract.valid is True
    assert contract.authority_isolated is True
    assert contract.capability_isolated is True
    assert contract.execution_isolated is True
    assert contract.sandbox_isolated is True
    assert contract.resource_isolated is True
    assert contract.secret_isolated is True
    assert contract.context_isolated is True
    assert contract.provenance_isolated is True
    assert contract.lifecycle_isolated is True
    assert contract.failure_isolated is True
    assert contract.cross_agent_communication_controlled is True


@pytest.mark.parametrize(
    "field",
    (
        "authority_isolated",
        "capability_isolated",
        "execution_isolated",
        "sandbox_isolated",
        "resource_isolated",
        "secret_isolated",
        "context_isolated",
        "provenance_isolated",
        "lifecycle_isolated",
        "failure_isolated",
        "cross_agent_communication_controlled",
    ),
)
def test_disabled_boundary_is_not_valid(field: str) -> None:
    contract = make_contract().model_copy(update={field: False})

    assert contract.valid is False


def test_contract_is_immutable() -> None:
    contract = make_contract()

    with pytest.raises(ValidationError):
        contract.agent_id = "agent:other"  # type: ignore[misc]


def test_contract_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        AgentIsolationContract(
            agent_id="agent:test",
            task_id="task:test",
            privileged=True,
        )
