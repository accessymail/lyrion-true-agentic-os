"""End-to-end tests for PIAE proactive execution integration."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lyrion.capabilities.contracts import CapabilityOperation
from lyrion.capabilities.gateway import CapabilityGateway
from lyrion.core.types import (
    AutonomyLevel,
    CorrelationId,
    DecisionAction,
    DecisionId,
    EventId,
    ExecutionTarget,
    IdempotencyKey,
    OpportunityId,
    RiskLevel,
    TaskId,
)
from lyrion.events.models import EventSensitivity, EventTrustLevel
from lyrion.execution.contracts import (
    ExecutionPlan,
    ExecutionStatus,
    ResourceLimits,
)
from lyrion.execution.executor import SecureExecutor
from lyrion.execution.sandbox import (
    EnvironmentMode,
    FilesystemMode,
    IsolationLevel,
    NetworkMode,
    SandboxConfig,
)
from lyrion.integration.proactive_execution import (
    CapabilityIntent,
    ProactiveExecutionCoordinator,
)
from lyrion.observability.execution_audit import ExecutionAuditLog
from lyrion.piae.contracts import (
    DecisionCandidate,
    DecisionConstraints,
    DecisionContext,
    DecisionReason,
    DecisionResult,
    Opportunity,
    OpportunityStatus,
    PolicyResult,
)
from lyrion.piae.engine import PIAEDecisionEngine
from lyrion.security.authorization import AegisAuthorizationService
from lyrion.security.guards import AuthorizationGuard
from lyrion.security.policy import AegisPolicyEvaluator
from lyrion.security.replay import ReplayGuard
from lyrion.security.rules import default_aegis_policy


def make_opportunity(
    *,
    now: datetime | None = None,
    **overrides: object,
) -> Opportunity:
    """Create a valid proactive opportunity."""
    current_time = now or datetime.now(UTC)

    values: dict[str, object] = {
        "opportunity_id": OpportunityId(
            "opp_integration_001",
        ),
        "correlation_id": CorrelationId(
            "corr_integration_001",
        ),
        "trigger_event_ids": (
            EventId("evt_integration_001"),
        ),
        "relevant_state_ids": (
            "state_integration_001",
        ),
        "goal_context": (
            "validate_proactive_execution",
        ),
        "title": "Execute approved proactive action",
        "description": (
            "A bounded proactive action is ready "
            "for controlled execution."
        ),
        "user_relevance": 0.95,
        "expected_benefit": 0.90,
        "interruption_cost": 0.05,
        "risk_score": 0.10,
        "reversibility": 0.95,
        "urgency": 0.50,
        "confidence": 0.95,
        "required_capabilities": (
            "development.prepare",
        ),
        "required_autonomy_level": AutonomyLevel.L1,
        "sensitivity": EventSensitivity.INTERNAL,
        "trust_level": EventTrustLevel.SYSTEM,
        "status": OpportunityStatus.OPEN,
        "created_at": current_time,
        "expires_at": current_time + timedelta(minutes=5),
    }

    values.update(overrides)

    return Opportunity(**values)


def make_constraints(
    **overrides: object,
) -> DecisionConstraints:
    """Create permissive-enough low-risk decision constraints."""
    values: dict[str, object] = {
        "max_risk_level": RiskLevel.LOW,
        "requires_human_approval": False,
        "allow_external_side_effects": False,
        "allow_network_access": False,
        "max_cost_units": 10.0,
        "max_runtime_seconds": 30.0,
    }

    values.update(overrides)

    return DecisionConstraints(**values)


def make_context(
    *,
    now: datetime | None = None,
    **overrides: object,
) -> DecisionContext:
    """Create a valid proactive decision context."""
    current_time = now or datetime.now(UTC)

    values: dict[str, object] = {
        "opportunity": make_opportunity(
            now=current_time,
        ),
        "state_records": (),
        "active_task_ids": (
            TaskId("task_integration_001"),
        ),
        "autonomy_level": AutonomyLevel.L1,
        "constraints": make_constraints(),
        "now": current_time,
    }

    values.update(overrides)

    return DecisionContext(**values)


def make_candidate(
    **overrides: object,
) -> DecisionCandidate:
    """Create a bounded executable decision candidate."""
    values: dict[str, object] = {
        "action": DecisionAction.EXECUTE,
        "rationale": DecisionReason.EFFICIENCY,
        "explanation": (
            "A low-risk bounded action is ready "
            "for controlled execution."
        ),
        "confidence": 0.95,
        "estimated_risk": RiskLevel.LOW,
        "estimated_cost_units": 0.5,
        "estimated_runtime_seconds": 1.0,
        "requires_human_approval": False,
        "has_external_side_effect": False,
        "requires_network_access": False,
    }

    values.update(overrides)

    return DecisionCandidate(**values)


def make_gateway(
    *,
    replay: ReplayGuard | None = None,
) -> CapabilityGateway:
    """Create the production-shaped Gateway test boundary."""
    policy = default_aegis_policy()

    return CapabilityGateway(
        AegisAuthorizationService(
            AegisPolicyEvaluator(policy),
            AuthorizationGuard(policy.policy_version),
            replay or ReplayGuard(),
        )
    )


def make_intent(
    **overrides: object,
) -> CapabilityIntent:
    """Create a bounded capability intent."""
    values: dict[str, object] = {
        "principal_id": "lyrion-piae",
        "capability_id": "development.prepare",
        "target_scope": "lyrion/project/src",
        "operation": CapabilityOperation.READ,
        "data_classification": EventSensitivity.INTERNAL,
        "task_id": TaskId("task_integration_001"),
        "risk_level": RiskLevel.LOW,
        "justification": (
            "Execute the approved proactive development action."
        ),
        "idempotency_key": IdempotencyKey(
            "idem_integration_001",
        ),
    }

    values.update(overrides)

    return CapabilityIntent(**values)


def make_plan(
    execution_id: str,
    **overrides: object,
) -> ExecutionPlan:
    """Create a valid dry-run execution plan."""
    values: dict[str, object] = {
        "execution_id": execution_id,
        "execution_target": ExecutionTarget.REMOTE_SANDBOX,
        "command_ref": None,
        "input_ref": None,
        "output_ref": None,
        "resource_limits": ResourceLimits(),
        "network_access_allowed": False,
        "external_side_effects_allowed": False,
        "checkpoint_required": False,
    }

    values.update(overrides)

    return ExecutionPlan(**values)


def make_sandbox(
    **overrides: object,
) -> SandboxConfig:
    """Create a valid conservative sandbox."""
    values: dict[str, object] = {
        "execution_target": ExecutionTarget.REMOTE_SANDBOX,
        "filesystem_mode": FilesystemMode.ISOLATED,
        "network_mode": NetworkMode.DISABLED,
        "environment_mode": EnvironmentMode.EMPTY,
        "isolation_level": IsolationLevel.STRICT,
        "writable_paths": (),
        "read_only_paths": (),
        "allowed_environment_keys": (),
        "resource_limits": ResourceLimits(),
        "allow_process_creation": False,
        "allow_privileged_operations": False,
    }

    values.update(overrides)

    return SandboxConfig(**values)


def make_coordinator(
    *,
    audit: ExecutionAuditLog | None = None,
    replay: ReplayGuard | None = None,
) -> ProactiveExecutionCoordinator:
    """Create the complete proactive execution coordinator."""
    return ProactiveExecutionCoordinator(
        piae=PIAEDecisionEngine(),
        gateway=make_gateway(
            replay=replay,
        ),
        executor=SecureExecutor(
            audit_log=audit,
        ),
    )


def make_execute_decision(
    *,
    now: datetime | None = None,
    **candidate_overrides: object,
) -> DecisionResult:
    """Create an actual PIAE EXECUTE decision."""
    current_time = now or datetime.now(UTC)

    context = make_context(
        now=current_time,
    )

    candidate = make_candidate(
        **candidate_overrides,
    )

    return PIAEDecisionEngine().decide(
        context,
        (candidate,),
        decision_id=DecisionId(
            "decision_integration_001",
        ),
        input_context_ref="integration-test",
    )


def test_piae_selects_execute_for_bounded_candidate() -> None:
    """PIAE should select a safe bounded EXECUTE candidate."""
    decision = make_execute_decision()

    assert decision.selected_action is DecisionAction.EXECUTE
    assert decision.authorization_required is True
    assert decision.authorization_granted is False


def test_decision_creates_capability_request() -> None:
    """An EXECUTE decision should become a capability request."""
    now = datetime.now(UTC)

    decision = make_execute_decision(
        now=now,
    )

    coordinator = make_coordinator()

    intent = make_intent()

    request = coordinator.create_capability_request(
        decision,
        intent,
        now=now,
    )

    assert request.decision_id == decision.decision_id
    assert request.principal_id == intent.principal_id
    assert request.capability_id == intent.capability_id
    assert request.target_scope == intent.target_scope
    assert request.operation is CapabilityOperation.READ
    assert request.autonomy_level is decision.autonomy_level
    assert request.risk_level is intent.risk_level
    assert request.correlation_id == decision.correlation_id
    assert request.idempotency_key == intent.idempotency_key


def test_capability_request_is_admitted_by_aegis() -> None:
    """A safe capability request should pass the Gateway."""
    now = datetime.now(UTC)

    decision = make_execute_decision(
        now=now,
    )

    coordinator = make_coordinator()

    request = coordinator.create_capability_request(
        decision,
        make_intent(),
        now=now,
    )

    admission = coordinator.admit(
        request,
        now=now,
    )

    assert admission.admitted is True
    assert (
        admission.execution_request.request_id
        == request.request_id
    )
    assert (
        admission.execution_request.capability_id
        == request.capability_id
    )


def test_complete_piae_to_executor_path_completes() -> None:
    """The complete proactive decision-to-execution path should complete."""
    now = datetime.now(UTC)

    decision = make_execute_decision(
        now=now,
    )

    coordinator = make_coordinator()

    intent = make_intent()

    request = coordinator.create_capability_request(
        decision,
        intent,
        now=now,
    )

    plan = make_plan(
        execution_id=f"execution:{request.request_id}",
    )

    sandbox = make_sandbox()

    result = coordinator.execute_decision(
        decision,
        intent,
        plan,
        sandbox,
        now=now,
    )

    assert result.status is ExecutionStatus.COMPLETED
    assert result.exit_code == 0
    assert result.execution_id == plan.execution_id
    assert result.request_id == request.request_id


def test_complete_path_emits_audit_evidence() -> None:
    """The integrated path must leave execution audit evidence."""
    now = datetime.now(UTC)

    decision = make_execute_decision(
        now=now,
    )

    audit = ExecutionAuditLog()

    coordinator = make_coordinator(
        audit=audit,
    )

    intent = make_intent()

    request = coordinator.create_capability_request(
        decision,
        intent,
        now=now,
    )

    plan = make_plan(
        execution_id=f"execution:{request.request_id}",
    )

    result = coordinator.execute_decision(
        decision,
        intent,
        plan,
        make_sandbox(),
        now=now,
    )

    assert result.status is ExecutionStatus.COMPLETED

    events = audit.events_for(
        result.execution_id,
    )

    event_types = [
        event.event_type
        for event in events
    ]

    assert "EXECUTOR_RECEIVED" in event_types
    assert "EXECUTION_STARTED" in event_types
    assert "EXECUTION_COMPLETED" in event_types
    assert audit.verify_chain() is True


def test_denied_capability_request_fails_closed() -> None:
    """A capability denied by Aegis must not become execution."""
    now = datetime.now(UTC)

    decision = make_execute_decision(
        now=now,
    )

    coordinator = make_coordinator()

    intent = make_intent(
        target_scope="protected/system",
    )

    request = coordinator.create_capability_request(
        decision,
        intent,
        now=now,
    )

    admission = coordinator.admit(
        request,
        now=now,
    )

    assert admission.admitted is False
    assert admission.authorization_decision.value == "DENIED"

    plan = make_plan(
        execution_id=f"execution:{request.request_id}",
    )

    result = coordinator.execute(
        admission,
        plan,
        make_sandbox(),
        now=now,
    )

    assert result.status is ExecutionStatus.DENIED


def test_expired_decision_cannot_create_capability_request() -> None:
    """An expired PIAE decision must not cross into authorization."""
    now = datetime.now(UTC)

    decision = make_execute_decision(
        now=now - timedelta(minutes=10),
    )

    coordinator = make_coordinator()

    with pytest.raises(ValueError, match="expired"):
        coordinator.create_capability_request(
            decision,
            make_intent(),
            now=now,
        )


def test_non_execute_decision_cannot_create_capability_request() -> None:
    """Non-execution decisions must not create capability requests."""
    now = datetime.now(UTC)

    context = make_context(
        now=now,
    )

    candidate = make_candidate(
        action=DecisionAction.PREPARE,
    )

    decision = PIAEDecisionEngine().decide(
        context,
        (candidate,),
        decision_id=DecisionId(
            "decision_prepare_001",
        ),
    )

    assert decision.selected_action is DecisionAction.PREPARE

    with pytest.raises(
        ValueError,
        match="only EXECUTE decisions",
    ):
        make_coordinator().create_capability_request(
            decision,
            make_intent(),
            now=now,
        )


def test_denied_piae_decision_cannot_create_capability_request() -> None:
    """A denied PIAE decision must not cross into capability authorization."""
    now = datetime.now(UTC)

    context = make_context(
        now=now,
        constraints=make_constraints(
            max_risk_level=RiskLevel.LOW,
        ),
    )

    candidate = make_candidate(
        estimated_risk=RiskLevel.CRITICAL,
    )

    decision = PIAEDecisionEngine().decide(
        context,
        (candidate,),
        decision_id=DecisionId(
            "decision_denied_001",
        ),
    )

    assert decision.selected_action is DecisionAction.DENY
    assert decision.authorization_result is PolicyResult.DENIED

    with pytest.raises(
        ValueError,
        match="only EXECUTE decisions",
    ):
        make_coordinator().create_capability_request(
            decision,
            make_intent(),
            now=now,
        )


def test_network_request_is_rejected_by_aegis() -> None:
    """A network requirement must not bypass the authorization boundary."""
    now = datetime.now(UTC)

    decision = make_execute_decision(
        now=now,
    )

    coordinator = make_coordinator()

    intent = make_intent()

    request = coordinator.create_capability_request(
        decision,
        intent,
        now=now,
    )

    request_data = request.model_dump()

    request_data["target_scope"] = "external/network"

    network_request = type(request)(**request_data)

    admission = coordinator.admit(
        network_request,
        now=now,
    )

    assert admission.admitted is False


def test_executor_uses_gateway_execution_request() -> None:
    """The executor must consume the request carried by the admission."""
    now = datetime.now(UTC)

    decision = make_execute_decision(
        now=now,
    )

    coordinator = make_coordinator()

    intent = make_intent(
        principal_id="lyrion-piae",
        target_scope="lyrion/project/src",
    )

    request = coordinator.create_capability_request(
        decision,
        intent,
        now=now,
    )

    admission = coordinator.admit(
        request,
        now=now,
    )

    assert admission.admitted is True

    execution_request = admission.execution_request

    assert execution_request.principal_id == (
        "lyrion-piae"
    )
    assert execution_request.capability_id == (
        "development.prepare"
    )
    assert execution_request.target_scope == (
        "lyrion/project/src"
    )


def test_capability_intent_is_immutable() -> None:
    """Capability intents must be immutable."""
    intent = make_intent()

    with pytest.raises(ValidationError):
        intent.target_scope = "changed"


def test_naive_time_is_rejected() -> None:
    """Integration timestamps must be timezone-aware."""
    decision = make_execute_decision()
    coordinator = make_coordinator()

    with pytest.raises(ValueError):
        coordinator.create_capability_request(
            decision,
            make_intent(),
            now=datetime.now(),
        )


def test_execution_plan_identity_must_match_request() -> None:
    """The execution plan must retain the request execution identity."""
    now = datetime.now(UTC)

    decision = make_execute_decision(
        now=now,
    )

    coordinator = make_coordinator()

    request = coordinator.create_capability_request(
        decision,
        make_intent(),
        now=now,
    )

    admission = coordinator.admit(
        request,
        now=now,
    )

    bad_plan = make_plan(
        execution_id="wrong-execution-id",
    )

    result = coordinator.execute(
        admission,
        bad_plan,
        make_sandbox(),
        now=now,
    )

    assert result.status is ExecutionStatus.DENIED
    assert "EXECUTION_ID_MISMATCH" in (
        result.error_message or ""
    )


def test_checkpoint_required_execution_creates_checkpoint() -> None:
    """End-to-end execution may generate and seal a checkpoint."""
    now = datetime.now(UTC)

    decision = make_execute_decision(
        now=now,
    )

    checkpoint_manager = __import__(
        "lyrion.execution.checkpoint",
        fromlist=["CheckpointManager"],
    ).CheckpointManager()

    coordinator = ProactiveExecutionCoordinator(
        piae=PIAEDecisionEngine(),
        gateway=make_gateway(),
        executor=SecureExecutor(
            checkpoint_manager=checkpoint_manager,
        ),
    )

    intent = make_intent()

    request = coordinator.create_capability_request(
        decision,
        intent,
        now=now,
    )

    plan = make_plan(
        execution_id=f"execution:{request.request_id}",
        checkpoint_required=True,
    )

    result = coordinator.execute_decision(
        decision,
        intent,
        plan,
        make_sandbox(),
        now=now,
    )

    assert result.status is ExecutionStatus.COMPLETED
    assert result.checkpoint_ref is not None

    checkpoint = checkpoint_manager.get(
        result.checkpoint_ref,
    )

    assert checkpoint is not None
    assert checkpoint.status.value == "SEALED"
