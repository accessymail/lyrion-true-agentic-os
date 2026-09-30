"""Integration tests for PB-DOC-005 Agent Harness delegation."""

from datetime import UTC, datetime, timedelta

from lyrion.agent_harness import AgentHarness, AgentIdentity
from lyrion.capabilities.contracts import (
    AuthorizationDecision,
    CapabilityOperation,
    CapabilityRequest,
)
from lyrion.capabilities.gateway import CapabilityGateway, ExecutionAdmission
from lyrion.core.types import (
    AutonomyLevel,
    DecisionId,
    ExecutionTarget,
    IdempotencyKey,
    RiskLevel,
    TaskId,
)
from lyrion.events.models import EventSensitivity
from lyrion.execution.contracts import ExecutionPlan, ExecutionStatus, ResourceLimits
from lyrion.execution.executor import SecureExecutor
from lyrion.execution.sandbox import SandboxConfig
from lyrion.security.authorization import AegisAuthorizationService
from lyrion.security.guards import AuthorizationGuard
from lyrion.security.policy import AegisPolicyEvaluator
from lyrion.security.replay import ReplayGuard
from lyrion.security.rules import default_aegis_policy
from lyrion.tasks.models import Task, TaskStatus


def make_request(now: datetime) -> CapabilityRequest:
    return CapabilityRequest(
        request_id="request:agent-harness:integration",
        decision_id=DecisionId("decision:agent-harness:integration"),
        task_id=TaskId("task:agent-harness:integration"),
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope="lyrion/project/src",
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        autonomy_level=AutonomyLevel.L1,
        risk_level=RiskLevel.LOW,
        policy_version="aegis-policy-v1",
        idempotency_key=IdempotencyKey("idem:agent-harness:integration"),
        requested_at=now,
        expires_at=now + timedelta(minutes=5),
        justification="PB-DOC-005 integration validation.",
    )


def make_task(now: datetime) -> Task:
    return Task(
        task_id=TaskId("task:agent-harness:integration"),
        objective="PB-DOC-005 integration validation",
        status=TaskStatus.RUNNING,
        autonomy_level=AutonomyLevel.L2,
        risk_level=RiskLevel.LOW,
        created_at=now,
        updated_at=now,
    )


def make_gateway() -> CapabilityGateway:
    policy = default_aegis_policy()
    return CapabilityGateway(
        AegisAuthorizationService(
            AegisPolicyEvaluator(policy),
            AuthorizationGuard(policy.policy_version),
            ReplayGuard(),
        )
    )


def test_agent_harness_delegates_only_through_secure_executor() -> None:
    now = datetime.now(UTC)
    request = make_request(now)
    task = make_task(now)
    gateway = make_gateway()

    authority = gateway.authorization_service.authorize(
        request,
        now=now,
    )
    assert authority.decision is AuthorizationDecision.ALLOWED
    assert authority.granted is True

    admission = ExecutionAdmission.from_authorization(
        request,
        authority,
        admitted_at=now,
    )
    assert admission.admitted is True

    limits = ResourceLimits()
    plan = ExecutionPlan(
        execution_id=admission.execution_request.execution_id,
        execution_target=ExecutionTarget.LOCAL_CPU,
        resource_limits=limits,
        network_access_allowed=False,
        external_side_effects_allowed=False,
    )
    sandbox = SandboxConfig(
        execution_target=ExecutionTarget.LOCAL_CPU,
        resource_limits=limits,
    )

    executor = SecureExecutor()
    harness = AgentHarness(secure_executor=executor)

    binding = harness.bind(
        identity=AgentIdentity(
            agent_id="agent:integration",
            identity_provenance_ref="registry:agent:integration:v1",
        ),
        task=task,
        authority_context=authority,
        capability_context=request,
        execution_admission=admission,
        provenance_context="test:pb-doc-005:integration",
    )

    result = harness.delegate(
        binding,
        task=task,
        plan=plan,
        sandbox=sandbox,
        now=now,
    )

    assert result.status is ExecutionStatus.COMPLETED
    assert result.execution_id == admission.execution_request.execution_id

    provenance = harness.provenance(
        binding,
        task=task,
        now=now,
    )
    assert provenance.agent_id == "agent:integration"
    assert provenance.task_id == task.task_id
    assert provenance.request_id == request.request_id
    assert provenance.execution_id == admission.execution_request.execution_id

    assert executor.audit_log.verify_chain() is True
    events = executor.audit_log.events_for(result.execution_id)
    event_types = [event.event_type for event in events]
    assert "AGENT_BINDING_VALIDATED" in event_types
    assert "AGENT_EXECUTION_DELEGATED" in event_types
