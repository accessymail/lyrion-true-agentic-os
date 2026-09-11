"""Unit and adversarial tests for the Application Runtime Boundary."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from lyrion.application.contracts import (
    ApplicationCorrelationContext,
    ApplicationCorrelationError,
    ApplicationPrincipalContext,
    ApplicationRuntimeError,
    ApplicationSessionContext,
    ApplicationSessionError,
    ApplicationTurnContext,
    ApplicationTurnError,
)
from lyrion.application.dependencies import build_application_runtime
from lyrion.application.errors import public_error_code
from lyrion.application.runtime import ApplicationRuntime
from lyrion.capabilities.contracts import CapabilityOperation
from lyrion.cognition.contracts import (
    CognitiveRequestStatus,
    CognitiveResult,
    ReasonRequest,
)
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
from lyrion.execution.contracts import ExecutionPlan, ResourceLimits
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
from lyrion.voice.streaming.contracts import (
    VoiceInterruptionReason,
    VoiceInterruptionRequest,
    VoiceInterruptionResult,
    VoiceInterruptionStatus,
    VoiceStreamSession,
    VoiceStreamState,
)

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


def make_principal() -> ApplicationPrincipalContext:
    return ApplicationPrincipalContext(
        principal_id="principal-001",
        authentication_method="test",
    )


def make_session(
    principal_id: str = "principal-001",
) -> ApplicationSessionContext:
    return ApplicationSessionContext(
        application_session_id="app-session-001",
        principal_id=principal_id,
        created_at=NOW,
    )


def make_correlation(
    *,
    session_id: str = "app-session-001",
) -> ApplicationCorrelationContext:
    return ApplicationCorrelationContext(
        correlation_id="corr-001",
        application_session_id=session_id,
        voice_session_id="voice-session-001",
        interaction_id="interaction-001",
        turn_id="turn-001",
        request_id="request-001",
    )


def make_turn(
    *,
    session_id: str = "app-session-001",
    correlation_id: str = "corr-001",
) -> ApplicationTurnContext:
    return ApplicationTurnContext(
        application_session_id=session_id,
        turn_id="turn-001",
        correlation_id=correlation_id,
        request_id="request-001",
        sequence=0,
    )


def test_runtime_factory_returns_runtime() -> None:
    assert isinstance(build_application_runtime(), ApplicationRuntime)


def test_session_binds_to_validated_principal() -> None:
    runtime = ApplicationRuntime(clock=lambda: NOW)

    result = runtime.bind_session(
        principal=make_principal(),
        session=make_session(),
    )

    assert result.application_session_id == "app-session-001"
    assert result.principal_id == "principal-001"


def test_cross_principal_session_fails_closed() -> None:
    runtime = ApplicationRuntime(clock=lambda: NOW)

    with pytest.raises(ApplicationSessionError, match="principal"):
        runtime.bind_session(
            principal=make_principal(),
            session=make_session("different-principal"),
        )


def test_future_session_fails_closed() -> None:
    runtime = ApplicationRuntime(clock=lambda: NOW)

    future_session = ApplicationSessionContext(
        application_session_id="app-session-001",
        principal_id="principal-001",
        created_at=NOW + timedelta(seconds=1),
    )

    with pytest.raises(ApplicationSessionError, match="future"):
        runtime.bind_session(
            principal=make_principal(),
            session=future_session,
        )


def test_correlation_can_be_bound_to_expected_session() -> None:
    runtime = ApplicationRuntime(clock=lambda: NOW)

    result = runtime.validate_correlation(
        make_correlation(),
        expected_session_id="app-session-001",
    )

    assert result.correlation_id == "corr-001"


def test_cross_session_correlation_fails_closed() -> None:
    runtime = ApplicationRuntime(clock=lambda: NOW)

    with pytest.raises(
        ApplicationCorrelationError,
        match="correlation session",
    ):
        runtime.validate_correlation(
            make_correlation(session_id="attacker-session"),
            expected_session_id="app-session-001",
        )


def test_turn_must_belong_to_session() -> None:
    runtime = ApplicationRuntime(clock=lambda: NOW)

    with pytest.raises(ApplicationTurnError, match="turn session"):
        runtime.bind_turn(
            session=make_session(),
            correlation=make_correlation(),
            turn=make_turn(session_id="attacker-session"),
        )


def test_turn_must_match_correlation_lineage() -> None:
    runtime = ApplicationRuntime(clock=lambda: NOW)

    with pytest.raises(ApplicationTurnError, match="correlation"):
        runtime.bind_turn(
            session=make_session(),
            correlation=make_correlation(),
            turn=make_turn(correlation_id="forged-correlation"),
        )


def test_correlation_is_not_authorization() -> None:
    runtime = build_application_runtime()
    context = make_correlation()

    result = runtime.validate_correlation(context)

    assert result.correlation_id == "corr-001"
    assert not hasattr(runtime, "authorize")
    assert not hasattr(runtime, "execute")
    assert not hasattr(runtime, "grant_capability")


def test_contracts_reject_blank_identity() -> None:
    with pytest.raises(ValueError, match="principal_id"):
        ApplicationPrincipalContext(
            principal_id=" ",
            authentication_method="test",
        )


def test_contracts_reject_blank_optional_lineage_values() -> None:
    with pytest.raises(ValueError, match="request_id"):
        ApplicationCorrelationContext(
            correlation_id="corr",
            application_session_id="session",
            request_id=" ",
        )


def test_contracts_reject_negative_turn_sequence() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        ApplicationTurnContext(
            application_session_id="session",
            turn_id="turn",
            correlation_id="corr",
            request_id="request",
            sequence=-1,
        )


def test_public_error_codes_are_stable() -> None:
    assert (
        public_error_code(ApplicationSessionError("x"))
        == "INVALID_SESSION"
    )
    assert (
        public_error_code(ApplicationCorrelationError("x"))
        == "INVALID_CORRELATION"
    )
    assert public_error_code(ApplicationTurnError("x")) == "INVALID_TURN"


def test_runtime_never_exposes_privileged_authority() -> None:
    runtime = build_application_runtime()

    forbidden_names = {
        "authorize",
        "grant_capability",
        "admit_execution",
        "execute",
        "secure_execute",
    }

    assert forbidden_names.isdisjoint(dir(runtime))




class FakeVoiceStreamingService:
    def __init__(self) -> None:
        self.interrupt_calls: list[VoiceInterruptionRequest] = []
        self.cancel_calls: list[str] = []
        self.get_calls: list[str] = []
        self.sessions = {
            "voice-session-001": VoiceStreamSession(
                session_id="voice-session-001",
                correlation_id="corr-001",
                state=VoiceStreamState.STREAMING,
                next_input_sequence=0,
                started_at=NOW,
                updated_at=NOW,
            ),
            "attacker-voice-session": VoiceStreamSession(
                session_id="attacker-voice-session",
                correlation_id="attacker-correlation",
                state=VoiceStreamState.STREAMING,
                next_input_sequence=0,
                started_at=NOW,
                updated_at=NOW,
            ),
        }
        self.interrupt_result = VoiceInterruptionResult(
            session_id="voice-session-001",
            request_id="request-001",
            status=VoiceInterruptionStatus.REQUESTED,
            occurred_at=NOW,
        )
        self.cancel_result = VoiceStreamSession(
            session_id="voice-session-001",
            correlation_id="corr-001",
            state=VoiceStreamState.CANCELLED,
            next_input_sequence=0,
            started_at=NOW,
            updated_at=NOW,
        )

    async def get(self, session_id: str) -> VoiceStreamSession:
        self.get_calls.append(session_id)
        return self.sessions[session_id]

    async def interrupt(
        self,
        request: VoiceInterruptionRequest,
    ) -> VoiceInterruptionResult:
        self.interrupt_calls.append(request)
        return self.interrupt_result

    async def cancel(self, session_id: str) -> VoiceStreamSession:
        self.cancel_calls.append(session_id)
        return self.cancel_result


def make_interruption_request(
    *,
    session_id: str = "voice-session-001",
    request_id: str = "request-001",
) -> VoiceInterruptionRequest:
    return VoiceInterruptionRequest(
        session_id=session_id,
        request_id=request_id,
        reason=VoiceInterruptionReason.BARGE_IN,
        requested_at=NOW,
    )


def test_bind_voice_session_creates_verified_lineage() -> None:
    runtime = ApplicationRuntime(clock=lambda: NOW)
    voice_session = VoiceStreamSession(
        session_id="voice-session-001",
        correlation_id="corr-001",
        state=VoiceStreamState.STREAMING,
        next_input_sequence=0,
        started_at=NOW,
        updated_at=NOW,
    )

    bound = runtime.bind_voice_session(
        session=make_session(),
        correlation=ApplicationCorrelationContext(
            correlation_id="corr-001",
            application_session_id="app-session-001",
            interaction_id="interaction-001",
            turn_id="turn-001",
            request_id="request-001",
        ),
        voice_session=voice_session,
    )

    assert bound.application_session_id == "app-session-001"
    assert bound.correlation_id == "corr-001"
    assert bound.voice_session_id == "voice-session-001"


def test_bind_voice_session_rejects_wrong_correlation() -> None:
    runtime = ApplicationRuntime(clock=lambda: NOW)
    voice_session = VoiceStreamSession(
        session_id="voice-session-001",
        correlation_id="attacker-correlation",
        state=VoiceStreamState.STREAMING,
        next_input_sequence=0,
        started_at=NOW,
        updated_at=NOW,
    )

    correlation = ApplicationCorrelationContext(
        correlation_id="corr-001",
        application_session_id="app-session-001",
    )

    with pytest.raises(
        ApplicationCorrelationError,
        match="voice session does not match correlation lineage",
    ):
        runtime.bind_voice_session(
            session=make_session(),
            correlation=correlation,
            voice_session=voice_session,
        )


def test_bind_voice_session_rejects_rebinding() -> None:
    runtime = ApplicationRuntime(clock=lambda: NOW)

    with pytest.raises(
        ApplicationCorrelationError,
        match="already has a voice session bound",
    ):
        runtime.bind_voice_session(
            session=make_session(),
            correlation=make_correlation(),
            voice_session=VoiceStreamSession(
                session_id="voice-session-002",
                correlation_id="corr-001",
                state=VoiceStreamState.STREAMING,
                next_input_sequence=0,
                started_at=NOW,
                updated_at=NOW,
            ),
        )


@pytest.mark.asyncio
async def test_interrupt_delegates_through_existing_voice_service() -> None:
    voice_service = FakeVoiceStreamingService()
    runtime = ApplicationRuntime(
        voice_streaming_service=voice_service,  # type: ignore[arg-type]
        clock=lambda: NOW,
    )

    result = await runtime.interrupt(
        session=make_session(),
        correlation=make_correlation(),
        request=make_interruption_request(),
    )

    assert result == voice_service.interrupt_result
    assert voice_service.interrupt_calls == [
        make_interruption_request(),
    ]


@pytest.mark.asyncio
async def test_interrupt_rejects_cross_session_before_service_call() -> None:
    voice_service = FakeVoiceStreamingService()
    runtime = ApplicationRuntime(
        voice_streaming_service=voice_service,  # type: ignore[arg-type]
        clock=lambda: NOW,
    )

    with pytest.raises(
        ApplicationCorrelationError,
        match="voice interruption session",
    ):
        await runtime.interrupt(
            session=make_session(),
            correlation=make_correlation(),
            request=make_interruption_request(
                session_id="attacker-voice-session",
            ),
        )

    assert voice_service.interrupt_calls == []


@pytest.mark.asyncio
async def test_interrupt_rejects_forged_request_lineage_before_service_call() -> None:
    voice_service = FakeVoiceStreamingService()
    runtime = ApplicationRuntime(
        voice_streaming_service=voice_service,  # type: ignore[arg-type]
        clock=lambda: NOW,
    )

    with pytest.raises(
        ApplicationCorrelationError,
        match="interruption request does not match",
    ):
        await runtime.interrupt(
            session=make_session(),
            correlation=make_correlation(),
            request=make_interruption_request(
                request_id="attacker-request",
            ),
        )

    assert voice_service.interrupt_calls == []


@pytest.mark.asyncio
async def test_interrupt_fails_closed_without_voice_service() -> None:
    runtime = ApplicationRuntime(clock=lambda: NOW)

    with pytest.raises(
        ApplicationRuntimeError,
        match="voice streaming service is not configured",
    ):
        await runtime.interrupt(
            session=make_session(),
            correlation=make_correlation(),
            request=make_interruption_request(),
        )


@pytest.mark.asyncio
async def test_cancel_delegates_through_existing_voice_service() -> None:
    voice_service = FakeVoiceStreamingService()
    runtime = ApplicationRuntime(
        voice_streaming_service=voice_service,  # type: ignore[arg-type]
        clock=lambda: NOW,
    )

    result = await runtime.cancel(
        session=make_session(),
        correlation=make_correlation(),
    )

    assert result == voice_service.cancel_result
    assert voice_service.cancel_calls == ["voice-session-001"]


@pytest.mark.asyncio
async def test_cancel_rejects_cross_session_before_service_call() -> None:
    voice_service = FakeVoiceStreamingService()
    runtime = ApplicationRuntime(
        voice_streaming_service=voice_service,  # type: ignore[arg-type]
        clock=lambda: NOW,
    )

    cross_session_correlation = make_correlation(
        session_id="attacker-session",
    )

    with pytest.raises(
        ApplicationCorrelationError,
        match="correlation session",
    ):
        await runtime.cancel(
            session=make_session(),
            correlation=cross_session_correlation,
        )

    assert voice_service.cancel_calls == []


@pytest.mark.asyncio
async def test_cancel_rejects_cross_voice_session_before_service_call() -> None:
    voice_service = FakeVoiceStreamingService()
    runtime = ApplicationRuntime(
        voice_streaming_service=voice_service,  # type: ignore[arg-type]
        clock=lambda: NOW,
    )

    forged_correlation = ApplicationCorrelationContext(
        correlation_id="corr-001",
        application_session_id="app-session-001",
        voice_session_id="attacker-voice-session",
        interaction_id="interaction-001",
        turn_id="turn-001",
        request_id="request-001",
    )

    with pytest.raises(
        ApplicationCorrelationError,
        match="voice session does not match correlation lineage",
    ):
        await runtime.cancel(
            session=make_session(),
            correlation=forged_correlation,
        )

    assert voice_service.cancel_calls == []


@pytest.mark.asyncio
async def test_cancel_fails_closed_without_voice_service() -> None:
    runtime = ApplicationRuntime(clock=lambda: NOW)

    with pytest.raises(
        ApplicationRuntimeError,
        match="voice streaming service is not configured",
    ):
        await runtime.cancel(
            session=make_session(),
            correlation=make_correlation(),
        )


class FakeCognitiveRuntime:
    def __init__(self) -> None:
        self.requests: list[ReasonRequest] = []

    async def reason(self, request: ReasonRequest) -> CognitiveResult:
        self.requests.append(request)

        return CognitiveResult(
            request_id=request.request_id,
            status=CognitiveRequestStatus.COMPLETED,
            answer="test answer",
            proposed_plan=(),
            uncertainty=0.1,
            confidence=0.9,
            evidence_refs=(),
            provider="test",
            model="test",
            verification_required=False,
            created_at=request.created_at,
        )


def make_reason_request(
    *,
    request_id: str = "request-001",
) -> ReasonRequest:
    return ReasonRequest(
        request_id=request_id,
        objective="test objective",
        created_at=NOW,
    )


@pytest.mark.asyncio
async def test_reason_delegates_to_existing_cognitive_runtime() -> None:
    cognitive = FakeCognitiveRuntime()
    runtime = ApplicationRuntime(
        cognitive_runtime=cognitive,
        clock=lambda: NOW,
    )

    result = await runtime.reason(
        session=make_session(),
        correlation=make_correlation(),
        request=make_reason_request(),
    )

    assert result.answer == "test answer"
    assert cognitive.requests == [make_reason_request()]


@pytest.mark.asyncio
async def test_reason_rejects_forged_request_lineage_before_delegation() -> None:
    cognitive = FakeCognitiveRuntime()
    runtime = ApplicationRuntime(
        cognitive_runtime=cognitive,
        clock=lambda: NOW,
    )

    with pytest.raises(
        ApplicationCorrelationError,
        match="request does not match correlation lineage",
    ):
        await runtime.reason(
            session=make_session(),
            correlation=make_correlation(),
            request=make_reason_request(request_id="forged-request"),
        )

    assert cognitive.requests == []


@pytest.mark.asyncio
async def test_reason_fails_closed_without_cognitive_runtime() -> None:
    runtime = ApplicationRuntime(clock=lambda: NOW)

    with pytest.raises(
        ApplicationRuntimeError,
        match="cognitive runtime is not configured",
    ):
        await runtime.reason(
            session=make_session(),
            correlation=make_correlation(),
            request=make_reason_request(),
        )


def make_rpii_opportunity() -> Opportunity:
    return Opportunity(
        opportunity_id=OpportunityId("opp_app_001"),
        correlation_id=CorrelationId("corr-001"),
        trigger_event_ids=(EventId("evt_app_001"),),
        relevant_state_ids=("state_app_001",),
        goal_context=("application-runtime-test",),
        title="Application runtime RPII test",
        description="Bounded application-runtime RPII test opportunity.",
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


def make_rpii_context(
    *,
    session_id: str = "app-session-001",
    interaction_id: str = "interaction-001",
) -> RPIIContext:
    return RPIIContext(
        interaction_id=interaction_id,
        session_id=session_id,
        decision_context=DecisionContext(
            opportunity=make_rpii_opportunity(),
            state_records=(),
            active_task_ids=(TaskId("task_app_001"),),
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
        ),
        created_at=NOW,
    )


def make_rpii_candidate() -> DecisionCandidate:
    return DecisionCandidate(
        action=DecisionAction.WAIT,
        rationale=DecisionReason.EFFICIENCY,
        explanation="Bounded application runtime test candidate.",
        confidence=0.95,
        estimated_risk=RiskLevel.LOW,
        estimated_cost_units=0.0,
        estimated_runtime_seconds=0.1,
        requires_human_approval=False,
        has_external_side_effect=False,
        requires_network_access=False,
    )


def make_rpii_intent() -> CapabilityIntent:
    return CapabilityIntent(
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope="lyrion/project/src",
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        task_id=TaskId("task_app_001"),
        risk_level=RiskLevel.LOW,
        justification="Application runtime RPII integration test.",
        idempotency_key=IdempotencyKey("idem_app_001"),
    )


def make_rpii_plan() -> ExecutionPlan:
    return ExecutionPlan(
        execution_id="exec-app-001",
        execution_target=ExecutionTarget.REMOTE_SANDBOX,
        command_ref=None,
        input_ref=None,
        output_ref=None,
        resource_limits=ResourceLimits(),
        network_access_allowed=False,
        external_side_effects_allowed=False,
        checkpoint_required=False,
    )


def make_rpii_sandbox() -> SandboxConfig:
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


class FakeRPIIActionLoop:
    """Typed action-loop double behind the real RPIIService."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run_once(
        self,
        context: object,
        candidates: tuple[DecisionCandidate, ...],
        intent: CapabilityIntent | None,
        plan: ExecutionPlan | None,
        sandbox: SandboxConfig | None,
        *,
        decision_id: DecisionId | None = None,
        input_context_ref: str = "action-loop",
        now: datetime | None = None,
    ) -> PIAEActionCycleResult:
        if not isinstance(context, DecisionContext):
            raise TypeError("RPII action-loop context must be DecisionContext")

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

        decision = DecisionResult(
            decision_id=decision_id or DecisionId("decision-app-001"),
            input_context_ref=input_context_ref,
            opportunity_ref=context.opportunity.opportunity_id,
            selected_action=DecisionAction.WAIT,
            alternative_actions=(),
            utility_estimate=0.0,
            interruption_cost=0.0,
            risk_estimate=0.0,
            autonomy_level=context.autonomy_level,
            authorization_result=PolicyResult.NOT_EVALUATED,
            policy_result=PolicyResult.NOT_EVALUATED,
            confidence=1.0,
            reason_codes=(DecisionReason.INSUFFICIENT_CONFIDENCE,),
            authorization_required=False,
            authorization_granted=False,
            candidate_count=len(candidates),
            correlation_id=context.opportunity.correlation_id,
            idempotency_key=None,
            expires_at=context.opportunity.expires_at,
            decided_at=context.now,
        )

        return PIAEActionCycleResult(decision=decision)


def make_rpii_service() -> tuple[RPIIService, FakeRPIIActionLoop]:
    action_loop = FakeRPIIActionLoop()
    return RPIIService(action_loop), action_loop


def test_rpii_delegates_through_existing_service() -> None:
    rpii, action_loop = make_rpii_service()
    runtime = ApplicationRuntime(
        rpii_service=rpii,
        clock=lambda: NOW,
    )

    context = make_rpii_context()

    result = runtime.run_rpii(
        session=make_session(),
        correlation=make_correlation(),
        context=context,
        candidates=(make_rpii_candidate(),),
        intent=None,
        plan=None,
        sandbox=None,
        now=NOW,
    )

    assert result.session_id == "app-session-001"
    assert result.interaction_id == "interaction-001"
    assert result.decision.selected_action is DecisionAction.WAIT
    assert len(action_loop.calls) == 1
    assert action_loop.calls[0]["context"] is context.decision_context


def test_rpii_rejects_cross_session_before_service_call() -> None:
    rpii, action_loop = make_rpii_service()
    runtime = ApplicationRuntime(
        rpii_service=rpii,
        clock=lambda: NOW,
    )

    with pytest.raises(
        ApplicationSessionError,
        match="RPII context session",
    ):
        runtime.run_rpii(
            session=make_session(),
            correlation=make_correlation(),
            context=make_rpii_context(session_id="attacker-session"),
            candidates=(make_rpii_candidate(),),
            intent=None,
            plan=None,
            sandbox=None,
            now=NOW,
        )

    assert action_loop.calls == []


def test_rpii_rejects_cross_interaction_before_service_call() -> None:
    rpii, action_loop = make_rpii_service()
    runtime = ApplicationRuntime(
        rpii_service=rpii,
        clock=lambda: NOW,
    )

    with pytest.raises(
        ApplicationCorrelationError,
        match="RPII interaction",
    ):
        runtime.run_rpii(
            session=make_session(),
            correlation=make_correlation(),
            context=make_rpii_context(interaction_id="forged-interaction"),
            candidates=(make_rpii_candidate(),),
            intent=None,
            plan=None,
            sandbox=None,
            now=NOW,
        )

    assert action_loop.calls == []


def test_rpii_fails_closed_when_service_is_missing() -> None:
    runtime = ApplicationRuntime(clock=lambda: NOW)

    with pytest.raises(
        ApplicationRuntimeError,
        match="RPII service is not configured",
    ):
        runtime.run_rpii(
            session=make_session(),
            correlation=make_correlation(),
            context=make_rpii_context(),
            candidates=(make_rpii_candidate(),),
            intent=None,
            plan=None,
            sandbox=None,
            now=NOW,
        )
