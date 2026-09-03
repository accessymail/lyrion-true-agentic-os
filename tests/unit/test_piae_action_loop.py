"""Tests for the deterministic PIAE action loop."""

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
from lyrion.piae.action_loop import (
    PIAEActionCycleResult,
    PIAEActionLoop,
)
from lyrion.piae.contracts import (
    DecisionCandidate,
    DecisionConstraints,
    DecisionContext,
    DecisionReason,
    Opportunity,
    OpportunityStatus,
)
from lyrion.piae.engine import PIAEDecisionEngine
from lyrion.security.authorization import AegisAuthorizationService
from lyrion.security.guards import AuthorizationGuard
from lyrion.security.policy import AegisPolicyEvaluator
from lyrion.security.replay import ReplayGuard
from lyrion.security.rules import default_aegis_policy


def make_opportunity(now: datetime) -> Opportunity:
    """Create a valid proactive opportunity."""
    return Opportunity(
        opportunity_id=OpportunityId("opp_loop_001"),
        correlation_id=CorrelationId("corr_loop_001"),
        trigger_event_ids=(EventId("evt_loop_001"),),
        relevant_state_ids=("state_loop_001",),
        goal_context=("validate_piae_action_loop",),
        title="Execute bounded proactive action",
        description="A safe action is ready.",
        user_relevance=0.95,
        expected_benefit=0.90,
        interruption_cost=0.05,
        risk_score=0.10,
        reversibility=0.95,
        urgency=0.50,
        confidence=0.95,
        required_capabilities=("development.prepare",),
        required_autonomy_level=AutonomyLevel.L1,
        sensitivity=EventSensitivity.INTERNAL,
        trust_level=EventTrustLevel.SYSTEM,
        status=OpportunityStatus.OPEN,
        created_at=now,
        expires_at=now + timedelta(minutes=5),
    )


def make_constraints() -> DecisionConstraints:
    """Create safe low-risk decision constraints."""
    return DecisionConstraints(
        max_risk_level=RiskLevel.LOW,
        requires_human_approval=False,
        allow_external_side_effects=False,
        allow_network_access=False,
        max_cost_units=10.0,
        max_runtime_seconds=30.0,
    )


def make_context(now: datetime) -> DecisionContext:
    """Create a valid decision context."""
    return DecisionContext(
        opportunity=make_opportunity(now),
        state_records=(),
        active_task_ids=(TaskId("task_loop_001"),),
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
        now=now,
    )


def make_candidate(
    *,
    action: DecisionAction = DecisionAction.EXECUTE,
    risk: RiskLevel = RiskLevel.LOW,
) -> DecisionCandidate:
    """Create a bounded decision candidate."""
    return DecisionCandidate(
        action=action,
        rationale=DecisionReason.EFFICIENCY,
        explanation="A bounded proactive action is ready.",
        confidence=0.95,
        estimated_risk=risk,
        estimated_cost_units=0.5,
        estimated_runtime_seconds=1.0,
        requires_human_approval=False,
        has_external_side_effect=False,
        requires_network_access=False,
    )


def make_intent(
    *,
    target_scope: str = "lyrion/project/src",
) -> CapabilityIntent:
    """Create a valid capability intent."""
    return CapabilityIntent(
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope=target_scope,
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        task_id=TaskId("task_loop_001"),
        risk_level=RiskLevel.LOW,
        justification="Execute bounded proactive action.",
        idempotency_key=IdempotencyKey("idem_loop_001"),
    )


def make_plan(execution_id: str) -> ExecutionPlan:
    """Create a valid dry-run execution plan."""
    return ExecutionPlan(
        execution_id=execution_id,
        execution_target=ExecutionTarget.REMOTE_SANDBOX,
        command_ref=None,
        input_ref=None,
        output_ref=None,
        resource_limits=ResourceLimits(),
        network_access_allowed=False,
        external_side_effects_allowed=False,
        checkpoint_required=False,
    )


def make_sandbox() -> SandboxConfig:
    """Create a conservative sandbox configuration."""
    return SandboxConfig(
        execution_target=ExecutionTarget.REMOTE_SANDBOX,
        filesystem_mode=FilesystemMode.ISOLATED,
        network_mode=NetworkMode.DISABLED,
        environment_mode=EnvironmentMode.EMPTY,
        isolation_level=IsolationLevel.STRICT,
        writable_paths=(),
        read_only_paths=(),
        allowed_environment_keys=(),
        resource_limits=ResourceLimits(),
        allow_process_creation=False,
        allow_privileged_operations=False,
    )


def make_loop(
    *,
    audit: ExecutionAuditLog | None = None,
    replay: ReplayGuard | None = None,
) -> PIAEActionLoop:
    """Create the complete PIAE action loop."""
    policy = default_aegis_policy()

    gateway = CapabilityGateway(
        AegisAuthorizationService(
            AegisPolicyEvaluator(policy),
            AuthorizationGuard(policy.policy_version),
            replay or ReplayGuard(),
        )
    )

    coordinator = ProactiveExecutionCoordinator(
        piae=PIAEDecisionEngine(),
        gateway=gateway,
        executor=SecureExecutor(
            audit_log=audit,
        ),
    )

    return PIAEActionLoop(coordinator)


def test_execute_cycle_is_end_to_end() -> None:
    """A valid PIAE decision should reach dry-run completion."""
    now = datetime.now(UTC)

    decision_id = DecisionId(
        "decision_loop_execute",
    )

    loop = make_loop()

    request_id = f"capreq:{decision_id}"

    result = loop.run_once(
        make_context(now),
        (make_candidate(),),
        make_intent(),
        make_plan(
            f"execution:{request_id}",
        ),
        make_sandbox(),
        decision_id=decision_id,
        now=now,
    )

    assert isinstance(result, PIAEActionCycleResult)
    assert result.decision.decision_id == decision_id
    assert result.decision.selected_action is DecisionAction.EXECUTE

    assert result.capability_request is not None
    assert result.capability_request.decision_id == decision_id

    assert result.admission is not None
    assert result.admission.admitted is True

    assert result.execution_result is not None
    assert result.execution_result.status is ExecutionStatus.COMPLETED
    assert result.execution_result.request_id == (
        result.capability_request.request_id
    )
    assert result.executed is True


def test_identity_is_preserved_across_full_cycle() -> None:
    """Decision identity must remain stable through execution."""
    now = datetime.now(UTC)

    decision_id = DecisionId(
        "decision_loop_identity",
    )

    loop = make_loop()

    request_id = f"capreq:{decision_id}"

    result = loop.run_once(
        make_context(now),
        (make_candidate(),),
        make_intent(),
        make_plan(
            f"execution:{request_id}",
        ),
        make_sandbox(),
        decision_id=decision_id,
        now=now,
    )

    assert result.capability_request is not None
    assert result.admission is not None
    assert result.execution_result is not None

    assert result.decision.decision_id == decision_id
    assert result.capability_request.decision_id == decision_id
    assert result.admission.request_id == (
        result.capability_request.request_id
    )
    assert result.execution_result.request_id == (
        result.capability_request.request_id
    )


def test_non_execute_decision_stops_before_authorization() -> None:
    """Non-execute decisions must not cross into authorization."""
    now = datetime.now(UTC)

    result = make_loop().run_once(
        make_context(now),
        (
            make_candidate(
                action=DecisionAction.PREPARE,
            ),
        ),
        intent=None,
        plan=None,
        sandbox=None,
        decision_id=DecisionId(
            "decision_prepare",
        ),
        now=now,
    )

    assert result.decision.selected_action is DecisionAction.PREPARE
    assert result.capability_request is None
    assert result.admission is None
    assert result.execution_result is None
    assert result.executed is False


def test_missing_intent_fails_closed() -> None:
    """EXECUTE decisions require explicit capability intent."""
    now = datetime.now(UTC)

    with pytest.raises(
        ValueError,
        match="CapabilityIntent is required",
    ):
        make_loop().run_once(
            make_context(now),
            (make_candidate(),),
            intent=None,
            plan=make_plan("execution:missing-intent"),
            sandbox=make_sandbox(),
            decision_id=DecisionId(
                "decision_missing_intent",
            ),
            now=now,
        )


def test_missing_plan_fails_closed() -> None:
    """EXECUTE decisions require an explicit execution plan."""
    now = datetime.now(UTC)

    with pytest.raises(
        ValueError,
        match="ExecutionPlan is required",
    ):
        make_loop().run_once(
            make_context(now),
            (make_candidate(),),
            intent=make_intent(),
            plan=None,
            sandbox=make_sandbox(),
            decision_id=DecisionId(
                "decision_missing_plan",
            ),
            now=now,
        )


def test_missing_sandbox_fails_closed() -> None:
    """EXECUTE decisions require an explicit sandbox."""
    now = datetime.now(UTC)

    with pytest.raises(
        ValueError,
        match="SandboxConfig is required",
    ):
        make_loop().run_once(
            make_context(now),
            (make_candidate(),),
            intent=make_intent(),
            plan=make_plan("execution:missing-sandbox"),
            sandbox=None,
            decision_id=DecisionId(
                "decision_missing_sandbox",
            ),
            now=now,
        )


def test_aegis_denial_propagates_to_execution_result() -> None:
    """Aegis denial must prevent successful execution."""
    now = datetime.now(UTC)

    decision_id = DecisionId(
        "decision_denied_scope",
    )

    loop = make_loop()

    request_id = f"capreq:{decision_id}"

    result = loop.run_once(
        make_context(now),
        (make_candidate(),),
        make_intent(
            target_scope="protected/system",
        ),
        make_plan(
            f"execution:{request_id}",
        ),
        make_sandbox(),
        decision_id=decision_id,
        now=now,
    )

    assert result.admission is not None
    assert result.admission.admitted is False

    assert result.execution_result is not None
    assert result.execution_result.status is ExecutionStatus.DENIED


def test_execution_cycle_is_audited() -> None:
    """A successful cycle must leave execution evidence."""
    now = datetime.now(UTC)

    audit = ExecutionAuditLog()
    loop = make_loop(
        audit=audit,
    )

    decision_id = DecisionId(
        "decision_audit",
    )

    request_id = f"capreq:{decision_id}"

    result = loop.run_once(
        make_context(now),
        (make_candidate(),),
        make_intent(),
        make_plan(
            f"execution:{request_id}",
        ),
        make_sandbox(),
        decision_id=decision_id,
        now=now,
    )

    assert result.execution_result is not None

    events = audit.events_for(
        result.execution_result.execution_id,
    )

    event_types = {
        event.event_type
        for event in events
    }

    assert "EXECUTOR_RECEIVED" in event_types
    assert "EXECUTION_STARTED" in event_types
    assert "EXECUTION_COMPLETED" in event_types
    assert audit.verify_chain() is True


def test_naive_time_is_rejected() -> None:
    """The action loop requires timezone-aware timestamps."""
    with pytest.raises(ValueError):
        make_loop().run_once(
            make_context(datetime.now(UTC)),
            (make_candidate(),),
            make_intent(),
            make_plan("execution:naive"),
            make_sandbox(),
            decision_id=DecisionId(
                "decision_naive",
            ),
            now=datetime.now(),
        )


def test_action_cycle_result_is_immutable() -> None:
    """Action cycle results must remain immutable."""
    now = datetime.now(UTC)

    decision_id = DecisionId(
        "decision_immutable",
    )

    request_id = f"capreq:{decision_id}"

    result = make_loop().run_once(
        make_context(now),
        (make_candidate(),),
        make_intent(),
        make_plan(
            f"execution:{request_id}",
        ),
        make_sandbox(),
        decision_id=decision_id,
        now=now,
    )

    with pytest.raises(ValidationError):
        result.decision = result.decision
