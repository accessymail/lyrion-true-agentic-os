"""Unit tests for PB-DOC-005 Agent Harness contracts."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lyrion.agent_harness.contracts import (
    AgentBinding,
    AgentBindingState,
    AgentIdentity,
    AgentIsolationContract,
    BindingValidationResult,
)
from lyrion.capabilities.contracts import (
    AuthorizationDecision,
    AuthorizationResult,
    CapabilityOperation,
    CapabilityRequest,
)
from lyrion.capabilities.gateway import ExecutionAdmission
from lyrion.core.types import (
    AutonomyLevel,
    DecisionId,
    IdempotencyKey,
    RiskLevel,
    TaskId,
)
from lyrion.events.models import EventSensitivity
from lyrion.tasks.models import Task, TaskStatus


def make_task() -> Task:
    now = datetime.now(UTC)
    return Task(
        task_id=TaskId("task:agent-harness:001"),
        objective="Agent Harness contract test",
        status=TaskStatus.RUNNING,
        autonomy_level=AutonomyLevel.L2,
        risk_level=RiskLevel.LOW,
        created_at=now,
        updated_at=now,
    )


def make_capability(now: datetime) -> CapabilityRequest:
    return CapabilityRequest(
        request_id="request:agent-harness:001",
        decision_id=DecisionId("decision:agent-harness:001"),
        task_id=TaskId("task:agent-harness:001"),
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope="lyrion/project/src",
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        autonomy_level=AutonomyLevel.L2,
        risk_level=RiskLevel.LOW,
        policy_version="aegis-policy-v1",
        idempotency_key=IdempotencyKey("idem:agent-harness:001"),
        requested_at=now,
        expires_at=now.replace(microsecond=0) if False else now,
        justification="Agent Harness contract test.",
    )


def test_agent_identity_is_immutable_and_attributable() -> None:
    identity = AgentIdentity(
        agent_id="agent:researcher",
        identity_provenance_ref="registry:agent:researcher:v1",
    )

    assert identity.agent_id == "agent:researcher"
    with pytest.raises(ValidationError):
        identity.agent_id = "agent:other"


def test_binding_state_machine_is_fail_closed() -> None:
    # Construct only enough nested contracts to test the state machine.
    now = datetime.now(UTC)
    task_id = TaskId("task:state")
    capability = CapabilityRequest(
        request_id="request:state",
        decision_id=DecisionId("decision:state"),
        task_id=task_id,
        principal_id="principal:state",
        capability_id="capability:state",
        target_scope="scope:state",
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        autonomy_level=AutonomyLevel.L1,
        risk_level=RiskLevel.LOW,
        policy_version="policy:v1",
        idempotency_key=IdempotencyKey("idem:state"),
        requested_at=now,
        expires_at=now,
        justification="state test",
    )
    authority = AuthorizationResult(
        request_id=capability.request_id,
        decision=AuthorizationDecision.ALLOWED,
        granted=True,
        principal_id=capability.principal_id,
        capability_id=capability.capability_id,
        target_scope=capability.target_scope,
        policy_version=capability.policy_version,
        reason="allowed",
        evaluated_at=now,
        expires_at=now,
    )
    admission = ExecutionAdmission.from_authorization(
        capability,
        authority,
        admitted_at=now,
    )
    binding = AgentBinding(
        identity=AgentIdentity(
            agent_id="agent:state",
            identity_provenance_ref="registry:state",
        ),
        task_id=task_id,
        authority_context=authority,
        capability_context=capability,
        execution_admission=admission,
        isolation_contract=AgentIsolationContract(
            agent_id="agent:state",
            task_id=str(task_id),
        ),
        provenance_context="test:state",
    )

    validated = binding.transition(AgentBindingState.VALIDATED)
    delegated = validated.transition(AgentBindingState.DELEGATED)

    assert validated.lifecycle_state is AgentBindingState.VALIDATED
    assert delegated.lifecycle_state is AgentBindingState.DELEGATED

    with pytest.raises(ValueError):
        binding.transition(AgentBindingState.COMPLETED)


def test_invalid_validation_result_requires_reason() -> None:
    with pytest.raises(ValueError):
        BindingValidationResult(valid=False)

    with pytest.raises(ValueError):
        BindingValidationResult(valid=True, failure_reason="invalid")
