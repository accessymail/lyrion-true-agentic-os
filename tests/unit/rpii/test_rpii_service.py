"""Adversarial and integration tests for the RPII orchestration service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from pydantic import ValidationError

from lyrion.capabilities.contracts import (
    AuthorizationDecision,
    CapabilityOperation,
    CapabilityRequest,
)
from lyrion.capabilities.gateway import ExecutionAdmission
from lyrion.core.types import (
    AutonomyLevel,
    CorrelationId,
    DecisionAction,
    DecisionId,
    ExecutionTarget,
    IdempotencyKey,
    OpportunityId,
    RiskLevel,
    TaskId,
)
from lyrion.events.models import EventSensitivity, EventTrustLevel
from lyrion.execution.contracts import (
    ExecutionPlan,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ResourceLimits,
)
from lyrion.execution.sandbox import (
    EnvironmentMode,
    FilesystemMode,
    IsolationLevel,
    NetworkMode,
    SandboxConfig,
)
from lyrion.integration.proactive_execution import CapabilityIntent
from lyrion.piae.action_loop import PIAEActionCycleResult
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
from lyrion.rpii.contracts import RPIIContext
from lyrion.rpii.service import RPIIService

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


def make_opportunity() -> Opportunity:
    return Opportunity(
        opportunity_id=OpportunityId("opp_rpii_001"),
        correlation_id=CorrelationId("corr_rpii_001"),
        trigger_event_ids=("evt_rpii_001",),
        relevant_state_ids=("state_rpii_001",),
        goal_context=("rpii-service-test",),
        title="RPII service test opportunity",
        description="Bounded RPII test opportunity.",
        user_relevance=0.9,
        expected_benefit=0.9,
        interruption_cost=0.1,
        risk_score=0.1,
        reversibility=0.9,
        urgency=0.5,
        confidence=0.95,
        required_capabilities=("development.prepare",),
        required_autonomy_level=AutonomyLevel.L1,
        sensitivity=EventSensitivity.INTERNAL,
        trust_level=EventTrustLevel.SYSTEM,
        status=OpportunityStatus.OPEN,
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
    )


def make_context() -> RPIIContext:
    decision_context = DecisionContext(
        opportunity=make_opportunity(),
        state_records=(),
        active_task_ids=(TaskId("task_rpii_001"),),
        autonomy_level=AutonomyLevel.L1,
        constraints=DecisionConstraints(
            max_risk_level=RiskLevel.LOW,
            requires_human_approval=False,
            allow_external_side_effects=False,
            allow_network_access=False,
            max_cost_units=10.0,
            max_runtime_seconds=30.0,
        ),
        now=NOW,
    )

    return RPIIContext(
        interaction_id="interaction-rpii-001",
        session_id="session-rpii-001",
        decision_context=decision_context,
        created_at=NOW,
    )


def make_decision(
    *,
    input_context_ref: str,
    opportunity_ref: OpportunityId | None = None,
    decision_id: str = "decision-rpii-001",
    action: DecisionAction = DecisionAction.WAIT,
    authorization_required: bool = False,
) -> DecisionResult:
    context = make_context()

    return DecisionResult(
        decision_id=DecisionId(decision_id),
        input_context_ref=input_context_ref,
        opportunity_ref=opportunity_ref
        or context.decision_context.opportunity.opportunity_id,
        selected_action=action,
        alternative_actions=(),
        utility_estimate=0.0,
        interruption_cost=0.0,
        risk_estimate=0.0,
        autonomy_level=AutonomyLevel.L1,
        authorization_result=PolicyResult.NOT_EVALUATED,
        policy_result=PolicyResult.NOT_EVALUATED,
        confidence=1.0,
        reason_codes=(DecisionReason.INSUFFICIENT_CONFIDENCE,),
        authorization_required=authorization_required,
        authorization_granted=False,
        candidate_count=0,
        correlation_id=None,
        idempotency_key=None,
        expires_at=None,
        decided_at=NOW,
    )


def make_intent() -> CapabilityIntent:
    return CapabilityIntent(
        principal_id="lyrion-rpii-test",
        capability_id="development.prepare",
        target_scope="lyrion/project/src",
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        task_id=TaskId("task_rpii_001"),
        risk_level=RiskLevel.LOW,
        justification="RPII service test.",
        idempotency_key=IdempotencyKey("idem-rpii-001"),
    )


def make_plan(
    execution_id: str = "execution:capreq:decision-rpii-001",
) -> ExecutionPlan:
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


def make_request(
    *,
    decision_id: DecisionId,
    request_id: str = "capreq:decision-rpii-001",
) -> CapabilityRequest:
    return CapabilityRequest(
        request_id=request_id,
        decision_id=decision_id,
        task_id=TaskId("task_rpii_001"),
        principal_id="lyrion-rpii-test",
        capability_id="development.prepare",
        target_scope="lyrion/project/src",
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        autonomy_level=AutonomyLevel.L1,
        risk_level=RiskLevel.LOW,
        policy_version="aegis-policy-v1",
        correlation_id=None,
        idempotency_key=IdempotencyKey("idem-rpii-001"),
        requested_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        justification="RPII service test.",
        authorization_decision=AuthorizationDecision.NOT_EVALUATED,
        authorization_granted=False,
    )


def make_admission(
    request: CapabilityRequest,
    *,
    execution_id: str | None = None,
) -> ExecutionAdmission:
    execution_request = ExecutionRequest(
        execution_id=execution_id or f"execution:{request.request_id}",
        request_id=request.request_id,
        task_id=request.task_id,
        capability_id=request.capability_id,
        target_scope=request.target_scope,
        operation=request.operation.value,
        authorization_reference=f"authorization:{request.request_id}",
        policy_version=request.policy_version,
        principal_id=request.principal_id,
        autonomy_level=request.autonomy_level,
        risk_level=request.risk_level,
        resource_limits=ResourceLimits(),
        network_access_allowed=False,
        external_side_effects_allowed=False,
        checkpoint_ref=None,
        idempotency_key=request.idempotency_key,
        correlation_id=request.correlation_id,
        requested_at=request.requested_at,
        expires_at=request.expires_at,
    )

    return ExecutionAdmission(
        request_id=request.request_id,
        capability_id=request.capability_id,
        target_scope=request.target_scope,
        admitted=True,
        authorization_decision=AuthorizationDecision.ALLOWED,
        authorization_reason="test authorization",
        policy_version=request.policy_version,
        admitted_at=NOW,
        execution_request=execution_request,
    )


def make_execution_result(
    admission: ExecutionAdmission,
    *,
    execution_id: str | None = None,
    request_id: str | None = None,
    status: ExecutionStatus = ExecutionStatus.COMPLETED,
) -> ExecutionResult:
    resolved_execution_id = (
        execution_id or admission.execution_request.execution_id
    )
    resolved_request_id = request_id or admission.request_id

    return ExecutionResult(
        execution_id=resolved_execution_id,
        request_id=resolved_request_id,
        status=status,
        started_at=NOW,
        completed_at=NOW,
        exit_code=0 if status is ExecutionStatus.COMPLETED else None,
        output_ref=None,
        error_code=None,
        error_message=None,
        checkpoint_ref=None,
    )


class FakeActionLoop:
    """Controlled action-loop double for RPII boundary tests."""

    def __init__(self, cycle: PIAEActionCycleResult) -> None:
        self.cycle = cycle
        self.calls: list[dict[str, object]] = []

    def run_once(
        self,
        context: object,
        candidates: tuple[DecisionCandidate, ...],
        intent: CapabilityIntent | None,
        plan: ExecutionPlan | None,
        sandbox: SandboxConfig | None,
        *,
        decision_id: object | None = None,
        input_context_ref: str = "action-loop",
        now: datetime | None = None,
    ) -> PIAEActionCycleResult:
        self.calls.append(
            {
                "context": context,
                "candidates": candidates,
                "intent": intent,
                "plan": plan,
                "sandbox": sandbox,
                "decision_id": decision_id,
                "input_context_ref": input_context_ref,
                "now": now,
            }
        )
        return self.cycle


def make_runner(
    *,
    decision: DecisionResult | None = None,
    request: CapabilityRequest | None = None,
    admission: ExecutionAdmission | None = None,
    execution_result: ExecutionResult | None = None,
) -> FakeActionLoop:
    resolved_decision = decision or make_decision(
        input_context_ref="rpii:session-rpii-001:interaction-rpii-001",
    )

    return FakeActionLoop(
        PIAEActionCycleResult(
            decision=resolved_decision,
            capability_request=request,
            admission=admission,
            execution_result=execution_result,
        )
    )


def test_non_execute_cycle_completes_at_decision_boundary() -> None:
    runner = make_runner()
    service = RPIIService(runner)

    result = service.run_once(
        make_context(),
        (),
        intent=None,
        plan=None,
        sandbox=None,
        now=NOW,
    )

    assert result.interaction_id == "interaction-rpii-001"
    assert result.session_id == "session-rpii-001"
    assert result.status.value == "COMPLETED"
    assert result.stage.value == "DECISION"
    assert result.capability_request is None
    assert result.admission is None
    assert result.execution_result is None


def test_service_derives_context_reference_internally() -> None:
    runner = make_runner()
    service = RPIIService(runner)

    service.run_once(
        make_context(),
        (),
        intent=None,
        plan=None,
        sandbox=None,
        now=NOW,
    )

    assert runner.calls[0]["input_context_ref"] == (
        "rpii:session-rpii-001:interaction-rpii-001"
    )


def test_execute_chain_preserves_all_identity_bindings() -> None:
    context = make_context()

    decision = make_decision(
        input_context_ref="rpii:session-rpii-001:interaction-rpii-001",
        action=DecisionAction.EXECUTE,
        authorization_required=True,
    )
    request = make_request(decision_id=decision.decision_id)
    admission = make_admission(request)
    execution_result = make_execution_result(admission)

    runner = make_runner(
        decision=decision,
        request=request,
        admission=admission,
        execution_result=execution_result,
    )

    service = RPIIService(runner)
    result = service.run_once(
        context,
        (),
        intent=make_intent(),
        plan=make_plan(),
        sandbox=make_sandbox(),
        now=NOW,
    )

    assert result.status.value == "COMPLETED"
    assert result.stage.value == "EVALUATION"
    assert result.decision.decision_id == request.decision_id
    assert request.decision_id == decision.decision_id
    assert admission.request_id == request.request_id
    assert admission.execution_request.request_id == request.request_id
    assert execution_result.request_id == request.request_id
    assert execution_result.execution_id == admission.execution_request.execution_id


def test_mismatched_decision_input_context_fails_closed() -> None:
    decision = make_decision(
        input_context_ref="rpii:foreign-session:foreign-interaction",
    )
    runner = make_runner(decision=decision)

    with pytest.raises(ValueError, match="input context"):
        RPIIService(runner).run_once(
            make_context(),
            (),
            intent=None,
            plan=None,
            sandbox=None,
            now=NOW,
        )


def test_mismatched_decision_opportunity_fails_closed() -> None:
    decision = make_decision(
        input_context_ref="rpii:session-rpii-001:interaction-rpii-001",
        opportunity_ref=OpportunityId("foreign-opportunity"),
    )
    runner = make_runner(decision=decision)

    with pytest.raises(ValueError, match="opportunity"):
        RPIIService(runner).run_once(
            make_context(),
            (),
            intent=None,
            plan=None,
            sandbox=None,
            now=NOW,
        )


def test_mismatched_request_decision_fails_closed() -> None:
    decision = make_decision(
        input_context_ref="rpii:session-rpii-001:interaction-rpii-001",
        action=DecisionAction.EXECUTE,
        authorization_required=True,
    )
    request = make_request(
        decision_id=DecisionId("foreign-decision"),
    )
    runner = make_runner(
        decision=decision,
        request=request,
    )

    with pytest.raises(ValueError, match="different decision"):
        RPIIService(runner).run_once(
            make_context(),
            (),
            intent=make_intent(),
            plan=make_plan(),
            sandbox=make_sandbox(),
            now=NOW,
        )


def test_mismatched_admission_request_fails_closed() -> None:
    decision = make_decision(
        input_context_ref="rpii:session-rpii-001:interaction-rpii-001",
        action=DecisionAction.EXECUTE,
        authorization_required=True,
    )
    request = make_request(decision_id=decision.decision_id)
    admission = make_admission(
        request,
    )
    tampered = admission.model_copy(
        update={"request_id": "foreign-request"},
    )

    runner = make_runner(
        decision=decision,
        request=request,
        admission=tampered,
    )

    with pytest.raises(ValueError, match="different request"):
        RPIIService(runner).run_once(
            make_context(),
            (),
            intent=make_intent(),
            plan=make_plan(),
            sandbox=make_sandbox(),
            now=NOW,
        )


def test_mismatched_execution_request_fails_closed() -> None:
    decision = make_decision(
        input_context_ref="rpii:session-rpii-001:interaction-rpii-001",
        action=DecisionAction.EXECUTE,
        authorization_required=True,
    )
    request = make_request(decision_id=decision.decision_id)
    admission = make_admission(request)

    foreign_execution_request = admission.execution_request.model_copy(
        update={"request_id": "foreign-request"},
    )
    tampered_admission = admission.model_copy(
        update={"execution_request": foreign_execution_request},
    )

    runner = make_runner(
        decision=decision,
        request=request,
        admission=tampered_admission,
    )

    with pytest.raises(ValueError, match="execution request"):
        RPIIService(runner).run_once(
            make_context(),
            (),
            intent=make_intent(),
            plan=make_plan(),
            sandbox=make_sandbox(),
            now=NOW,
        )


def test_mismatched_execution_result_request_fails_closed() -> None:
    decision = make_decision(
        input_context_ref="rpii:session-rpii-001:interaction-rpii-001",
        action=DecisionAction.EXECUTE,
        authorization_required=True,
    )
    request = make_request(decision_id=decision.decision_id)
    admission = make_admission(request)
    execution_result = make_execution_result(
        admission,
        request_id="foreign-request",
    )

    runner = make_runner(
        decision=decision,
        request=request,
        admission=admission,
        execution_result=execution_result,
    )

    with pytest.raises(ValueError, match="different capability request"):
        RPIIService(runner).run_once(
            make_context(),
            (),
            intent=make_intent(),
            plan=make_plan(),
            sandbox=make_sandbox(),
            now=NOW,
        )


def test_mismatched_execution_result_execution_id_fails_closed() -> None:
    decision = make_decision(
        input_context_ref="rpii:session-rpii-001:interaction-rpii-001",
        action=DecisionAction.EXECUTE,
        authorization_required=True,
    )
    request = make_request(decision_id=decision.decision_id)
    admission = make_admission(request)
    execution_result = make_execution_result(
        admission,
        execution_id="foreign-execution",
    )

    runner = make_runner(
        decision=decision,
        request=request,
        admission=admission,
        execution_result=execution_result,
    )

    with pytest.raises(ValueError, match="different execution"):
        RPIIService(runner).run_once(
            make_context(),
            (),
            intent=make_intent(),
            plan=make_plan(),
            sandbox=make_sandbox(),
            now=NOW,
        )


def test_mismatched_plan_execution_id_fails_closed() -> None:
    decision = make_decision(
        input_context_ref="rpii:session-rpii-001:interaction-rpii-001",
        action=DecisionAction.EXECUTE,
        authorization_required=True,
    )
    request = make_request(decision_id=decision.decision_id)
    admission = make_admission(request)
    execution_result = make_execution_result(admission)

    runner = make_runner(
        decision=decision,
        request=request,
        admission=admission,
        execution_result=execution_result,
    )

    with pytest.raises(ValueError, match="execution_id"):
        RPIIService(runner).run_once(
            make_context(),
            (),
            intent=make_intent(),
            plan=make_plan("execution:foreign"),
            sandbox=make_sandbox(),
            now=NOW,
        )


def test_denied_admission_never_becomes_successful_execution() -> None:
    decision = make_decision(
        input_context_ref="rpii:session-rpii-001:interaction-rpii-001",
        action=DecisionAction.EXECUTE,
        authorization_required=True,
    )
    request = make_request(decision_id=decision.decision_id)
    admission = make_admission(request).model_copy(
        update={
            "admitted": False,
            "authorization_decision": AuthorizationDecision.DENIED,
        }
    )

    runner = make_runner(
        decision=decision,
        request=request,
        admission=admission,
    )

    result = RPIIService(runner).run_once(
        make_context(),
        (),
        intent=make_intent(),
        plan=make_plan(),
        sandbox=make_sandbox(),
        now=NOW,
    )

    assert result.status.value == "DENIED"
    assert result.stage.value == "AUTHORIZATION"
    assert result.admission is not None
    assert result.admission.admitted is False
    assert result.execution_result is None


def test_service_rejects_time_before_context_creation() -> None:
    runner = make_runner()

    with pytest.raises(ValueError, match="context.created_at"):
        RPIIService(runner).run_once(
            make_context(),
            (),
            intent=None,
            plan=None,
            sandbox=None,
            now=NOW - timedelta(seconds=1),
        )


def test_service_rejects_naive_now() -> None:
    runner = make_runner()

    with pytest.raises(ValueError, match="timezone-aware"):
        RPIIService(runner).run_once(
            make_context(),
            (),
            intent=None,
            plan=None,
            sandbox=None,
            now=datetime(2026, 9, 4, 12, 0),
        )


@pytest.mark.parametrize(
    "authority_field",
    (
        "execution_authorized",
        "capability_granted",
        "execution_authority",
        "authorization_token",
    ),
)
def test_context_authority_injection_is_rejected(
    authority_field: str,
) -> None:
    values = {
        "interaction_id": "interaction-rpii-001",
        "session_id": "session-rpii-001",
        "decision_context": make_context().decision_context,
        "created_at": NOW,
        authority_field: True,
    }

    with pytest.raises(ValidationError):
        RPIIContext.model_validate(values)


def test_service_is_not_an_authorization_authority() -> None:
    runner = make_runner()
    service = RPIIService(runner)

    assert not hasattr(service, "authorize")
    assert not hasattr(service, "grant_capability")
    assert not hasattr(service, "execute")


def test_public_action_runner_is_only_used_for_orchestration() -> None:
    decision = make_decision(
        input_context_ref="rpii:session-rpii-001:interaction-rpii-001",
    )
    runner = make_runner(decision=decision)
    service = RPIIService(cast(object, runner))

    result = service.run_once(
        make_context(),
        (),
        intent=None,
        plan=None,
        sandbox=None,
        now=NOW,
    )

    assert result.decision.decision_id == decision.decision_id
