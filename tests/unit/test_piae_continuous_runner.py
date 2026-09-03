"""Adversarial tests for the bounded PIAE continuous runner."""

from datetime import UTC, datetime

import pytest

from lyrion.capabilities.contracts import CapabilityOperation
from lyrion.capabilities.gateway import CapabilityGateway
from lyrion.core.types import (
    AutonomyLevel,
    CorrelationId,
    DecisionAction,
    EventId,
    ExecutionTarget,
    IdempotencyKey,
    RiskLevel,
)
from lyrion.events.models import (
    Event,
    EventSensitivity,
    EventTrustLevel,
)
from lyrion.execution.contracts import ExecutionPlan, ExecutionStatus, ResourceLimits
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
from lyrion.piae.continuous_runner import (
    ContinuousRunnerConfig,
    PIAEContinuousRunner,
    ProactiveBatchResult,
)
from lyrion.piae.contracts import (
    DecisionCandidate,
    DecisionConstraints,
    DecisionReason,
)
from lyrion.piae.engine import PIAEDecisionEngine
from lyrion.piae.opportunity_detector import OpportunityDetector
from lyrion.piae.proactive_cycle import PIAEProactiveCycle
from lyrion.security.authorization import AegisAuthorizationService
from lyrion.security.guards import AuthorizationGuard
from lyrion.security.policy import AegisPolicyEvaluator
from lyrion.security.replay import ReplayGuard
from lyrion.security.rules import default_aegis_policy


def make_event(
    event_id: str,
    *,
    payload: dict[str, object] | None = None,
) -> Event:
    """Create an event for runner tests."""
    now = datetime.now(UTC)

    return Event(
        event_id=EventId(event_id),
        event_type="proactive.trigger",
        source="runner-test",
        timestamp=now,
        observed_at=now,
        subject="runner",
        payload=payload or {},
        sensitivity=EventSensitivity.INTERNAL,
        provenance="runner-test",
        trust_level=EventTrustLevel.SYSTEM,
        correlation_id=CorrelationId(
            f"corr:{event_id}",
        ),
        idempotency_key=IdempotencyKey(
            f"idem:{event_id}",
        ),
    )


def make_payload() -> dict[str, object]:
    """Create a valid opportunity payload."""
    return {
        "creates_opportunity": True,
        "opportunity_title": "Runner opportunity",
        "opportunity_description": "Bounded proactive action.",
        "user_relevance": 0.90,
        "expected_benefit": 0.90,
        "interruption_cost": 0.05,
        "risk_score": 0.10,
        "reversibility": 0.95,
        "urgency": 0.50,
        "confidence": 0.95,
        "required_capabilities": (
            "development.prepare",
        ),
        "required_autonomy_level": "L1",
    }


def make_candidate() -> DecisionCandidate:
    """Create a safe executable candidate."""
    return DecisionCandidate(
        action=DecisionAction.EXECUTE,
        rationale=DecisionReason.EFFICIENCY,
        explanation="Bounded runner test action.",
        confidence=0.95,
        estimated_risk=RiskLevel.LOW,
        estimated_cost_units=0.5,
        estimated_runtime_seconds=1.0,
        requires_human_approval=False,
        has_external_side_effect=False,
        requires_network_access=False,
    )


def make_constraints() -> DecisionConstraints:
    """Create safe constraints."""
    return DecisionConstraints(
        max_risk_level=RiskLevel.LOW,
        requires_human_approval=False,
        allow_external_side_effects=False,
        allow_network_access=False,
        max_cost_units=10.0,
        max_runtime_seconds=30.0,
    )


def make_intent(event_id: str) -> CapabilityIntent:
    """Create an intent for one event."""
    return CapabilityIntent(
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope="lyrion/project/src",
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        task_id=f"task:{event_id}",
        risk_level=RiskLevel.LOW,
        justification="Run bounded proactive test action.",
        idempotency_key=IdempotencyKey(
            f"action:{event_id}",
        ),
    )


def make_plan(event: Event) -> ExecutionPlan:
    """Create a plan with the correct event-derived identity."""
    return ExecutionPlan(
        execution_id=f"execution:capreq:batch:{event.event_id}",
        execution_target=ExecutionTarget.REMOTE_SANDBOX,
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


def make_runner(
    *,
    audit: ExecutionAuditLog | None = None,
    config: ContinuousRunnerConfig | None = None,
) -> PIAEContinuousRunner:
    """Create a complete continuous runner."""
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

    cycle = PIAEProactiveCycle(
        OpportunityDetector(),
        __import__(
            "lyrion.piae.action_loop",
            fromlist=["PIAEActionLoop"],
        ).PIAEActionLoop(coordinator),
    )

    return PIAEContinuousRunner(
        cycle,
        config=config,
    )


def test_run_once_processes_one_event() -> None:
    """run_once should execute one bounded proactive cycle."""
    event = make_event(
        "evt_runner_once",
        payload=make_payload(),
    )

    result = make_runner().run_once(
        event,
        candidates=(make_candidate(),),
        intent=make_intent(
            str(event.event_id),
        ),
        plan=make_plan(event),
        sandbox=make_sandbox(),
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
    )

    assert result.opportunity_detected is True
    assert result.execution_result is not None
    assert result.execution_result.status is ExecutionStatus.COMPLETED


def test_run_batch_processes_events_in_order() -> None:
    """Batch processing should preserve input ordering."""
    events = (
        make_event("evt_batch_1", payload=make_payload()),
        make_event("evt_batch_2", payload=make_payload()),
        make_event("evt_batch_3", payload=make_payload()),
    )

    runner = make_runner()

    result = runner.run_batch(
        events,
        candidates=(make_candidate(),),
        intent=make_intent("shared"),
        plan_factory=make_plan,
        sandbox=make_sandbox(),
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
    )

    assert result.processed_count == 3
    assert result.failure_count == 0
    assert result.failed_indices == ()
    assert len(result.results) == 3

    assert [
        cycle.event.event_id
        for cycle in result.results
    ] == [
        EventId("evt_batch_1"),
        EventId("evt_batch_2"),
        EventId("evt_batch_3"),
    ]


def test_batch_is_bounded() -> None:
    """A batch exceeding the configured bound must be rejected."""
    runner = make_runner(
        config=ContinuousRunnerConfig(
            max_events_per_batch=2,
        ),
    )

    events = (
        make_event("evt_bound_1"),
        make_event("evt_bound_2"),
        make_event("evt_bound_3"),
    )

    with pytest.raises(
        ValueError,
        match="max_events_per_batch",
    ):
        runner.run_batch(
            events,
            candidates=(),
            intent=None,
            plan_factory=make_plan,
            sandbox=None,
        )


def test_zero_batch_limit_is_rejected() -> None:
    """The runner must reject an unusable zero-event limit."""
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        ContinuousRunnerConfig(
            max_events_per_batch=0,
        )


def test_negative_batch_limit_is_rejected() -> None:
    """The runner must reject negative batch limits."""
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        ContinuousRunnerConfig(
            max_events_per_batch=-1,
        )


def test_empty_batch_is_valid() -> None:
    """An empty batch should return an empty result."""
    result = make_runner().run_batch(
        (),
        candidates=(),
        intent=None,
        plan_factory=make_plan,
        sandbox=None,
    )

    assert isinstance(
        result,
        ProactiveBatchResult,
    )
    assert result.results == ()
    assert result.failed_indices == ()
    assert result.processed_count == 0
    assert result.failure_count == 0


def test_non_opportunity_events_are_processed_without_action() -> None:
    """Ordinary events should produce no action result."""
    events = (
        make_event(
            "evt_ordinary_1",
            payload={},
        ),
        make_event(
            "evt_ordinary_2",
            payload={
                "message": "nothing proactive here",
            },
        ),
    )

    result = make_runner().run_batch(
        events,
        candidates=(),
        intent=None,
        plan_factory=make_plan,
        sandbox=None,
    )

    assert result.processed_count == 2
    assert all(
        cycle.opportunity_detected is False
        for cycle in result.results
    )


def test_failure_is_isolated_to_one_event() -> None:
    """A failure in one event must not abort later events."""
    events = (
        make_event(
            "evt_failure_1",
            payload=make_payload(),
        ),
        make_event(
            "evt_failure_2",
            payload=make_payload(),
        ),
    )

    call_count = 0

    def plan_factory(event: Event) -> ExecutionPlan:
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            raise RuntimeError(
                "synthetic plan creation failure",
            )

        return make_plan(event)

    result = make_runner().run_batch(
        events,
        candidates=(make_candidate(),),
        intent=make_intent("shared"),
        plan_factory=plan_factory,
        sandbox=make_sandbox(),
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
    )

    assert result.failure_count == 1
    assert result.failed_indices == (0,)
    assert result.processed_count == 1
    assert result.results[0].event.event_id == (
        EventId("evt_failure_2")
    )


def test_batch_results_are_immutable() -> None:
    """Batch results should not be mutable."""
    result = make_runner().run_batch(
        (),
        candidates=(),
        intent=None,
        plan_factory=make_plan,
        sandbox=None,
    )

    with pytest.raises(
        AttributeError,
    ):
        result.results += ()


def test_naive_time_is_rejected() -> None:
    """The runner must preserve timezone safety."""
    event = make_event(
        "evt_naive",
        payload=make_payload(),
    )

    with pytest.raises(ValueError):
        make_runner().run_once(
            event,
            candidates=(make_candidate(),),
            intent=make_intent(
                "naive",
            ),
            plan=make_plan(event),
            sandbox=make_sandbox(),
            autonomy_level=AutonomyLevel.L1,
            constraints=make_constraints(),
            now=datetime.now(),
        )


def test_audit_survives_batch_processing() -> None:
    """Batch execution should preserve execution evidence."""
    audit = ExecutionAuditLog()

    events = (
        make_event(
            "evt_audit_1",
            payload=make_payload(),
        ),
        make_event(
            "evt_audit_2",
            payload=make_payload(),
        ),
    )

    result = make_runner(
        audit=audit,
    ).run_batch(
        events,
        candidates=(make_candidate(),),
        intent=make_intent("audit"),
        plan_factory=make_plan,
        sandbox=make_sandbox(),
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
    )

    assert result.processed_count == 2
    assert result.failure_count == 0
    assert audit.verify_chain() is True


def test_runner_does_not_create_background_loop() -> None:
    """The bounded runner exposes explicit invocation only."""
    runner = make_runner()

    assert hasattr(
        runner,
        "run_once",
    )
    assert hasattr(
        runner,
        "run_batch",
    )
    assert not hasattr(
        runner,
        "start",
    )
    assert not hasattr(
        runner,
        "run_forever",
    )
