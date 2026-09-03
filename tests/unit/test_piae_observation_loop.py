"""Adversarial tests for the bounded PIAE observation loop."""

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
from lyrion.piae.continuous_runner import PIAEContinuousRunner
from lyrion.piae.contracts import (
    DecisionCandidate,
    DecisionConstraints,
    DecisionReason,
)
from lyrion.piae.engine import PIAEDecisionEngine
from lyrion.piae.observation_loop import (
    ObservationLoopConfig,
    PIAEObservationLoop,
)
from lyrion.piae.opportunity_detector import OpportunityDetector
from lyrion.piae.proactive_cycle import PIAEProactiveCycle
from lyrion.security.authorization import AegisAuthorizationService
from lyrion.security.guards import AuthorizationGuard
from lyrion.security.policy import AegisPolicyEvaluator
from lyrion.security.replay import ReplayGuard
from lyrion.security.rules import default_aegis_policy


class FakeEventSource:
    """Deterministic in-memory event source for tests."""

    def __init__(
        self,
        events: tuple[Event, ...],
    ) -> None:
        self._events = events
        self.poll_calls: list[int] = []

    def poll(self, limit: int) -> tuple[Event, ...]:
        """Return up to ``limit`` events."""
        self.poll_calls.append(limit)

        return self._events[:limit]


class OverflowEventSource:
    """Event source intentionally violating the source contract."""

    def __init__(
        self,
        events: tuple[Event, ...],
    ) -> None:
        self._events = events

    def poll(self, limit: int) -> tuple[Event, ...]:
        """Return more events than requested."""
        return self._events


def make_event(
    event_id: str,
    *,
    proactive: bool = True,
) -> Event:
    """Create a deterministic event."""
    now = datetime.now(UTC)

    payload: dict[str, object] = {}

    if proactive:
        payload = {
            "creates_opportunity": True,
            "opportunity_title": "Observation-loop opportunity",
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

    return Event(
        event_id=EventId(event_id),
        event_type="observation.test",
        source="observation-loop-test",
        timestamp=now,
        observed_at=now,
        payload=payload,
        sensitivity=EventSensitivity.INTERNAL,
        provenance="observation-loop-test",
        trust_level=EventTrustLevel.SYSTEM,
        correlation_id=CorrelationId(
            f"corr:{event_id}",
        ),
        idempotency_key=IdempotencyKey(
            f"idem:{event_id}",
        ),
    )


def make_candidate() -> DecisionCandidate:
    """Create a safe executable candidate."""
    return DecisionCandidate(
        action=DecisionAction.EXECUTE,
        rationale=DecisionReason.EFFICIENCY,
        explanation="Bounded proactive action.",
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
    """Create a safe capability intent."""
    return CapabilityIntent(
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope="lyrion/project/src",
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        task_id="task:observation-loop",
        risk_level=RiskLevel.LOW,
        justification="Observation-loop test action.",
        idempotency_key=IdempotencyKey(
            "intent:observation-loop",
        ),
    )


def make_plan(event: Event) -> ExecutionPlan:
    """Create a plan matching the deterministic runner identity."""
    return ExecutionPlan(
        execution_id=(
            f"execution:capreq:batch:{event.event_id}"
        ),
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


def make_loop(
    *,
    audit: ExecutionAuditLog | None = None,
) -> PIAEObservationLoop:
    """Create a complete observation loop."""
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
        PIAEActionLoop(coordinator),
    )

    runner = PIAEContinuousRunner(
        cycle,
    )

    return PIAEObservationLoop(
        FakeEventSource(()),
        runner,
    )


def test_poll_once_processes_source_events() -> None:
    """One observation poll should process the available events."""
    events = (
        make_event("evt_observe_1"),
        make_event("evt_observe_2"),
    )

    policy = default_aegis_policy()

    gateway = CapabilityGateway(
        AegisAuthorizationService(
            AegisPolicyEvaluator(policy),
            AuthorizationGuard(policy.policy_version),
            ReplayGuard(),
        )
    )

    cycle = PIAEProactiveCycle(
        OpportunityDetector(),
        PIAEActionLoop(
            ProactiveExecutionCoordinator(
                piae=PIAEDecisionEngine(),
                gateway=gateway,
                executor=SecureExecutor(),
            )
        ),
    )

    runner = PIAEContinuousRunner(cycle)

    source = FakeEventSource(events)

    loop = PIAEObservationLoop(
        source,
        runner,
    )

    result = loop.poll_once(
        candidates=(make_candidate(),),
        intent=make_intent(),
        plan_factory=make_plan,
        sandbox=make_sandbox(),
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
    )

    assert result.events_seen == 2
    assert result.processed_count == 2
    assert result.failed_count == 0
    assert source.poll_calls == [16]


def test_poll_respects_configured_limit() -> None:
    """The configured polling bound must reach the event source."""
    source = FakeEventSource(
        (
            make_event("evt_limit_1"),
            make_event("evt_limit_2"),
        )
    )

    loop = PIAEObservationLoop(
        source,
        make_loop().runner,
        ObservationLoopConfig(
            max_events_per_poll=1,
        ),
    )

    result = loop.poll_once(
        candidates=(),
        intent=None,
        plan_factory=make_plan,
        sandbox=None,
    )

    assert result.events_seen == 1
    assert source.poll_calls == [1]


def test_poll_rejects_source_that_exceeds_bound() -> None:
    """A source violating the bound must fail closed."""
    events = (
        make_event("evt_overflow_1"),
        make_event("evt_overflow_2"),
    )

    source = OverflowEventSource(events)

    loop = PIAEObservationLoop(
        source,
        make_loop().runner,
        ObservationLoopConfig(
            max_events_per_poll=1,
        ),
    )

    with pytest.raises(
        ValueError,
        match="exceeded max_events_per_poll",
    ):
        loop.poll_once(
            candidates=(),
            intent=None,
            plan_factory=make_plan,
            sandbox=None,
        )


def test_zero_poll_limit_is_rejected() -> None:
    """Zero polling capacity is invalid."""
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        ObservationLoopConfig(
            max_events_per_poll=0,
        )


def test_negative_poll_limit_is_rejected() -> None:
    """Negative polling capacity is invalid."""
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        ObservationLoopConfig(
            max_events_per_poll=-1,
        )


def test_empty_source_is_valid() -> None:
    """An empty observation source should produce an empty result."""
    source = FakeEventSource(())

    loop = PIAEObservationLoop(
        source,
        make_loop().runner,
    )

    result = loop.poll_once(
        candidates=(),
        intent=None,
        plan_factory=make_plan,
        sandbox=None,
    )

    assert result.events_seen == 0
    assert result.processed_count == 0
    assert result.failed_count == 0


def test_non_proactive_events_do_not_create_actions() -> None:
    """Ordinary observations should pass through without execution."""
    source = FakeEventSource(
        (
            make_event(
                "evt_non_proactive",
                proactive=False,
            ),
        )
    )

    loop = PIAEObservationLoop(
        source,
        make_loop().runner,
    )

    result = loop.poll_once(
        candidates=(),
        intent=None,
        plan_factory=make_plan,
        sandbox=None,
    )

    assert result.events_seen == 1
    assert result.processed_count == 1
    assert result.failed_count == 0
    assert result.cycle_result.results[0].opportunity_detected is False


def test_observation_loop_exposes_components() -> None:
    """Loop dependencies should remain inspectable."""
    source = FakeEventSource(())

    runner = make_loop().runner

    loop = PIAEObservationLoop(
        source,
        runner,
    )

    assert loop.source is source
    assert loop.runner is runner
    assert loop.config.max_events_per_poll == 16


def test_observation_loop_does_not_start_background_worker() -> None:
    """The bounded loop must not create an implicit worker."""
    loop = make_loop()

    assert hasattr(loop, "poll_once")
    assert not hasattr(loop, "start")
    assert not hasattr(loop, "run_forever")
    assert not hasattr(loop, "stop")


def test_audit_survives_observation_processing() -> None:
    """Observation-to-action processing should preserve audit evidence."""
    audit = ExecutionAuditLog()

    event = make_event(
        "evt_observe_audit",
    )

    source = FakeEventSource(
        (event,),
    )

    policy = default_aegis_policy()

    gateway = CapabilityGateway(
        AegisAuthorizationService(
            AegisPolicyEvaluator(policy),
            AuthorizationGuard(policy.policy_version),
            ReplayGuard(),
        )
    )

    cycle = PIAEProactiveCycle(
        OpportunityDetector(),
        PIAEActionLoop(
            ProactiveExecutionCoordinator(
                piae=PIAEDecisionEngine(),
                gateway=gateway,
                executor=SecureExecutor(
                    audit_log=audit,
                ),
            )
        ),
    )

    loop = PIAEObservationLoop(
        source,
        PIAEContinuousRunner(cycle),
    )

    result = loop.poll_once(
        candidates=(make_candidate(),),
        intent=make_intent(),
        plan_factory=make_plan,
        sandbox=make_sandbox(),
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
    )

    execution_result = (
        result.cycle_result.results[0].execution_result
    )

    assert execution_result is not None
    assert execution_result.status is ExecutionStatus.COMPLETED
    assert audit.verify_chain() is True
