"""Tests for the single-cycle proactive intelligence pipeline."""

from datetime import UTC, datetime, timedelta

import pytest

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
    RiskLevel,
    TaskId,
)
from lyrion.events.models import (
    Event,
    EventSensitivity,
    EventTrustLevel,
)
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
from lyrion.piae.action_loop import PIAEActionLoop
from lyrion.piae.contracts import (
    DecisionCandidate,
    DecisionConstraints,
    DecisionReason,
)
from lyrion.piae.engine import PIAEDecisionEngine
from lyrion.piae.opportunity_detector import OpportunityDetector
from lyrion.piae.proactive_cycle import (
    PIAEProactiveCycle,
    ProactiveCycleResult,
)
from lyrion.security.authorization import AegisAuthorizationService
from lyrion.security.guards import AuthorizationGuard
from lyrion.security.policy import AegisPolicyEvaluator
from lyrion.security.replay import ReplayGuard
from lyrion.security.rules import default_aegis_policy


def make_event(
    *,
    now: datetime | None = None,
    payload: dict[str, object] | None = None,
) -> Event:
    """Create a valid proactive event."""
    current_time = now or datetime.now(UTC)

    return Event(
        event_id=EventId("evt_proactive_cycle_001"),
        event_type="proactive.trigger",
        source="unit-test",
        timestamp=current_time,
        observed_at=current_time,
        subject="proactive-subject",
        payload=payload or {},
        sensitivity=EventSensitivity.INTERNAL,
        provenance="unit-test",
        trust_level=EventTrustLevel.SYSTEM,
        correlation_id=CorrelationId(
            "corr_proactive_cycle_001",
        ),
        idempotency_key=IdempotencyKey(
            "idem_proactive_cycle_001",
        ),
    )


def make_payload() -> dict[str, object]:
    """Create a valid opportunity declaration."""
    return {
        "creates_opportunity": True,
        "opportunity_title": "Prepare proactive action",
        "opportunity_description": (
            "A bounded proactive action is available."
        ),
        "user_relevance": 0.90,
        "expected_benefit": 0.85,
        "interruption_cost": 0.10,
        "risk_score": 0.10,
        "reversibility": 0.90,
        "urgency": 0.50,
        "confidence": 0.95,
        "required_capabilities": (
            "development.prepare",
        ),
        "required_autonomy_level": "L1",
        "goal_context": (
            "proactive-maintenance",
        ),
    }


def make_candidate() -> DecisionCandidate:
    """Create a safe executable candidate."""
    return DecisionCandidate(
        action=DecisionAction.EXECUTE,
        rationale=DecisionReason.EFFICIENCY,
        explanation="A bounded proactive action is ready.",
        confidence=0.95,
        estimated_risk=RiskLevel.LOW,
        estimated_cost_units=0.5,
        estimated_runtime_seconds=1.0,
        requires_human_approval=False,
        has_external_side_effect=False,
        requires_network_access=False,
    )


def make_constraints() -> DecisionConstraints:
    """Create safe decision constraints."""
    return DecisionConstraints(
        max_risk_level=RiskLevel.LOW,
        requires_human_approval=False,
        allow_external_side_effects=False,
        allow_network_access=False,
        max_cost_units=10.0,
        max_runtime_seconds=30.0,
    )


def make_intent() -> CapabilityIntent:
    """Create a valid capability intent."""
    return CapabilityIntent(
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope="lyrion/project/src",
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        task_id=TaskId("task_proactive_cycle_001"),
        risk_level=RiskLevel.LOW,
        justification="Perform bounded proactive maintenance.",
        idempotency_key=IdempotencyKey(
            "idem_action_cycle_001",
        ),
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
    """Create a conservative sandbox."""
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


def make_cycle(
    *,
    audit: ExecutionAuditLog | None = None,
) -> PIAEProactiveCycle:
    """Create the complete proactive cycle."""
    policy = default_aegis_policy()

    gateway = CapabilityGateway(
        AegisAuthorizationService(
            AegisPolicyEvaluator(policy),
            AuthorizationGuard(policy.policy_version),
            ReplayGuard(),
        )
    )

    coordinator = ProactiveExecutionCoordinator(
        piae=PIAEDecisionEngine(),
        gateway=gateway,
        executor=SecureExecutor(
            audit_log=audit,
        ),
    )

    return PIAEProactiveCycle(
        OpportunityDetector(),
        PIAEActionLoop(coordinator),
    )


def test_event_to_opportunity_to_action() -> None:
    """A qualifying event should complete one proactive action cycle."""
    now = datetime.now(UTC)
    decision_id = DecisionId(
        "decision_proactive_cycle",
    )

    request_id = f"capreq:{decision_id}"

    cycle = make_cycle()

    result = cycle.process_event(
        make_event(
            now=now,
            payload=make_payload(),
        ),
        candidates=(make_candidate(),),
        intent=make_intent(),
        plan=make_plan(
            f"execution:{request_id}",
        ),
        sandbox=make_sandbox(),
        active_task_ids=(
            TaskId("task_proactive_cycle_001"),
        ),
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
        decision_id=decision_id,
        now=now,
    )

    assert isinstance(
        result,
        ProactiveCycleResult,
    )
    assert result.opportunity_detected is True
    assert result.detected_opportunity is not None
    assert result.action_cycle is not None
    assert result.action_cycle.decision.decision_id == decision_id
    assert result.action_cycle.admission is not None
    assert result.action_cycle.admission.admitted is True
    assert result.execution_result is not None
    assert result.execution_result.status is ExecutionStatus.COMPLETED


def test_non_opportunity_event_stops_before_piae() -> None:
    """An ordinary event must not enter PIAE."""
    cycle = make_cycle()

    result = cycle.process_event(
        make_event(
            payload={
                "message": "ordinary observation",
            },
        ),
        candidates=(),
        intent=None,
        plan=None,
        sandbox=None,
    )

    assert result.opportunity_detected is False
    assert result.detected_opportunity is None
    assert result.action_cycle is None
    assert result.execution_result is None


def test_detected_opportunity_preserves_event_identity() -> None:
    """The triggering event must remain attached to the opportunity."""
    cycle = make_cycle()

    result = cycle.process_event(
        make_event(
            payload=make_payload(),
        ),
        candidates=(make_candidate(),),
        intent=make_intent(),
        plan=make_plan(
            "execution:capreq:decision_identity",
        ),
        sandbox=make_sandbox(),
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
        decision_id=DecisionId(
            "decision_identity",
        ),
    )

    assert result.detected_opportunity is not None
    assert result.detected_opportunity.trigger_event_ids == (
        EventId("evt_proactive_cycle_001"),
    )


def test_missing_constraints_fail_closed() -> None:
    """An opportunity must not proceed without decision constraints."""
    cycle = make_cycle()

    with pytest.raises(
        ValueError,
        match="constraints are required",
    ):
        cycle.process_event(
            make_event(
                payload=make_payload(),
            ),
            candidates=(make_candidate(),),
            intent=make_intent(),
            plan=make_plan(
                "execution:missing-constraints",
            ),
            sandbox=make_sandbox(),
            autonomy_level=AutonomyLevel.L1,
            constraints=None,
        )


def test_missing_autonomy_fails_closed() -> None:
    """An opportunity must not proceed without autonomy context."""
    cycle = make_cycle()

    with pytest.raises(
        ValueError,
        match="autonomy_level is required",
    ):
        cycle.process_event(
            make_event(
                payload=make_payload(),
            ),
            candidates=(make_candidate(),),
            intent=make_intent(),
            plan=make_plan(
                "execution:missing-autonomy",
            ),
            sandbox=make_sandbox(),
            autonomy_level=None,
            constraints=make_constraints(),
        )


def test_expired_event_opportunity_waits() -> None:
    """An expired opportunity must not execute."""
    now = datetime.now(UTC)

    payload = make_payload()
    payload["opportunity_expires_at"] = now + timedelta(seconds=1)

    cycle = make_cycle()

    result = cycle.process_event(
        make_event(
            now=now,
            payload=payload,
        ),
        candidates=(make_candidate(),),
        intent=None,
        plan=None,
        sandbox=None,
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
        now=now + timedelta(seconds=2),
    )

    assert result.opportunity_detected is True
    assert result.action_cycle is not None
    assert result.action_cycle.decision.selected_action is (
        DecisionAction.WAIT
    )
    assert result.execution_result is None


def test_execution_failure_does_not_break_detection() -> None:
    """A detected opportunity remains represented when execution is denied."""
    cycle = make_cycle()

    result = cycle.process_event(
        make_event(
            payload=make_payload(),
        ),
        candidates=(make_candidate(),),
        intent=CapabilityIntent(
            principal_id="lyrion-piae",
            capability_id="development.prepare",
            target_scope="protected/system",
            operation=CapabilityOperation.READ,
            data_classification=EventSensitivity.INTERNAL,
            task_id=TaskId("task_proactive_cycle_001"),
            risk_level=RiskLevel.LOW,
            justification="Test denied scope.",
            idempotency_key=IdempotencyKey(
                "idem_denied_scope",
            ),
        ),
        plan=make_plan(
            "execution:capreq:denied",
        ),
        sandbox=make_sandbox(),
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
        decision_id=DecisionId(
            "decision_denied_scope",
        ),
    )

    assert result.opportunity_detected is True
    assert result.action_cycle is not None
    assert result.action_cycle.admission is not None
    assert result.action_cycle.admission.admitted is False
    assert result.execution_result is not None
    assert result.execution_result.status is ExecutionStatus.DENIED


def test_audit_survives_full_proactive_cycle() -> None:
    """The complete event-to-action path must retain audit evidence."""
    audit = ExecutionAuditLog()
    cycle = make_cycle(
        audit=audit,
    )

    decision_id = DecisionId(
        "decision_audit_cycle",
    )

    request_id = f"capreq:{decision_id}"

    result = cycle.process_event(
        make_event(
            payload=make_payload(),
        ),
        candidates=(make_candidate(),),
        intent=make_intent(),
        plan=make_plan(
            f"execution:{request_id}",
        ),
        sandbox=make_sandbox(),
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
        decision_id=decision_id,
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
