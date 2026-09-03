"""Tests for per-opportunity consumer context binding."""

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
    OpportunityId,
    RiskLevel,
    TaskId,
)
from lyrion.events.models import (
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
    Opportunity,
)
from lyrion.piae.engine import PIAEDecisionEngine
from lyrion.piae.opportunity_binding import (
    DeterministicOpportunityContextFactory,
)
from lyrion.piae.opportunity_consumer import OpportunityConsumer
from lyrion.piae.opportunity_queue import OpportunityQueue
from lyrion.security.authorization import AegisAuthorizationService
from lyrion.security.guards import AuthorizationGuard
from lyrion.security.policy import AegisPolicyEvaluator
from lyrion.security.replay import ReplayGuard
from lyrion.security.rules import default_aegis_policy


def make_opportunity(
    opportunity_id: str,
    *,
    now: datetime | None = None,
) -> Opportunity:
    """Create an executable test opportunity."""
    current_time = now or datetime.now(UTC)

    return Opportunity(
        opportunity_id=OpportunityId(opportunity_id),
        correlation_id=CorrelationId(
            f"corr:{opportunity_id}",
        ),
        trigger_event_ids=(
            EventId(f"event:{opportunity_id}"),
        ),
        relevant_state_ids=(),
        goal_context=("consumer-binding-test",),
        title="Consumer binding opportunity",
        description="Opportunity-specific context test.",
        user_relevance=0.9,
        expected_benefit=0.9,
        interruption_cost=0.1,
        risk_score=0.1,
        reversibility=0.9,
        urgency=0.8,
        confidence=0.95,
        required_capabilities=("development.prepare",),
        required_autonomy_level=AutonomyLevel.L1,
        sensitivity=EventSensitivity.INTERNAL,
        trust_level=EventTrustLevel.SYSTEM,
        created_at=current_time,
        expires_at=None,
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


def make_candidate(
    opportunity: Opportunity,
) -> tuple[DecisionCandidate, ...]:
    """Create candidates specifically for one opportunity."""
    return (
        DecisionCandidate(
            action=DecisionAction.EXECUTE,
            rationale=DecisionReason.EFFICIENCY,
            explanation=(
                f"Execute {opportunity.opportunity_id}."
            ),
            confidence=0.95,
            estimated_risk=RiskLevel.LOW,
            estimated_cost_units=0.5,
            estimated_runtime_seconds=1.0,
            requires_human_approval=False,
            has_external_side_effect=False,
            requires_network_access=False,
        ),
    )


def make_intent(
    opportunity: Opportunity,
) -> CapabilityIntent:
    """Create an intent specifically for one opportunity."""
    opportunity_id = str(opportunity.opportunity_id)

    return CapabilityIntent(
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope=f"lyrion/project/{opportunity_id}",
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        task_id=TaskId(f"task:{opportunity_id}"),
        risk_level=RiskLevel.LOW,
        justification=(
            f"opportunity:{opportunity_id}: "
            "consumer binding test"
        ),
        idempotency_key=IdempotencyKey(
            f"idem:{opportunity_id}",
        ),
    )


def make_plan(
    opportunity: Opportunity,
) -> ExecutionPlan:
    """Create an execution plan bound to one opportunity."""
    decision_id = (
        f"opportunity:{opportunity.opportunity_id}"
    )

    return ExecutionPlan(
        execution_id=(
            f"execution:capreq:{decision_id}"
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


def make_context_factory() -> (
    DeterministicOpportunityContextFactory
):
    """Create a context factory that derives all action data per opportunity."""
    return DeterministicOpportunityContextFactory(
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
        intent_factory=make_intent,
        plan_factory=make_plan,
        sandbox_factory=lambda _opportunity: make_sandbox(),
    )


def make_consumer(
    queue: OpportunityQueue,
    *,
    audit: ExecutionAuditLog | None = None,
) -> OpportunityConsumer:
    """Create a complete secure consumer using the supplied queue."""
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

    return OpportunityConsumer(
        queue,
        PIAEActionLoop(coordinator),
    )


def test_bound_consumer_uses_opportunity_specific_factory() -> None:
    """The bound path passes the dequeued opportunity to the factory."""
    now = datetime.now(UTC)
    opportunity = make_opportunity(
        "opp_bound_001",
        now=now,
    )

    queue = OpportunityQueue()
    assert queue.enqueue(
        opportunity,
        now=now,
    ) is True

    received: list[Opportunity] = []

    def intent_factory(
        item: Opportunity,
    ) -> CapabilityIntent:
        received.append(item)
        return make_intent(item)

    factory = DeterministicOpportunityContextFactory(
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
        intent_factory=intent_factory,
        plan_factory=make_plan,
        sandbox_factory=lambda _item: make_sandbox(),
    )

    result = make_consumer(queue).consume_bound_once(
        context_factory=factory,
        candidates_factory=make_candidate,
        now=now,
    )

    assert result is not None
    assert received == [opportunity]
    assert result.decision.decision_id == (
        f"opportunity:{opportunity.opportunity_id}"
    )


def test_bound_consumer_keeps_execution_identity_aligned() -> None:
    """Decision and execution identities must remain aligned."""
    now = datetime.now(UTC)
    opportunity = make_opportunity(
        "opp_identity",
        now=now,
    )

    queue = OpportunityQueue()
    assert queue.enqueue(
        opportunity,
        now=now,
    ) is True

    result = make_consumer(queue).consume_bound_once(
        context_factory=make_context_factory(),
        candidates_factory=make_candidate,
        now=now,
    )

    assert result is not None
    assert result.capability_request is not None
    assert result.execution_result is not None

    assert result.capability_request.decision_id == (
        result.decision.decision_id
    )

    assert result.execution_result.execution_id == (
        f"execution:capreq:{result.decision.decision_id}"
    )

    assert result.execution_result.status is ExecutionStatus.COMPLETED


def test_bound_consumer_rejects_mismatched_plan() -> None:
    """A plan belonging to another opportunity must fail closed."""
    now = datetime.now(UTC)
    opportunity = make_opportunity(
        "opp_a",
        now=now,
    )

    queue = OpportunityQueue()
    assert queue.enqueue(
        opportunity,
        now=now,
    ) is True

    bad_factory = DeterministicOpportunityContextFactory(
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
        intent_factory=make_intent,
        plan_factory=lambda _item: make_plan(
            make_opportunity(
                "opp_b",
                now=now,
            )
        ),
        sandbox_factory=lambda _item: make_sandbox(),
    )

    with pytest.raises(
        ValueError,
        match="execution plan is not bound",
    ):
        make_consumer(queue).consume_bound_once(
            context_factory=bad_factory,
            candidates_factory=make_candidate,
            now=now,
        )


def test_bound_consumer_uses_opportunity_specific_candidates() -> None:
    """Candidate generation receives the exact queued opportunity."""
    now = datetime.now(UTC)
    opportunity = make_opportunity(
        "opp_candidates",
        now=now,
    )

    queue = OpportunityQueue()
    assert queue.enqueue(
        opportunity,
        now=now,
    ) is True

    received: list[Opportunity] = []

    def candidates_factory(
        item: Opportunity,
    ) -> tuple[DecisionCandidate, ...]:
        received.append(item)
        return make_candidate(item)

    result = make_consumer(queue).consume_bound_once(
        context_factory=make_context_factory(),
        candidates_factory=candidates_factory,
        now=now,
    )

    assert result is not None
    assert received == [opportunity]


def test_bound_consumer_empty_queue_returns_none() -> None:
    """An empty queue must not invoke context generation."""
    calls = 0

    def candidates_factory(
        _item: Opportunity,
    ) -> tuple[DecisionCandidate, ...]:
        nonlocal calls
        calls += 1
        return ()

    queue = OpportunityQueue()

    result = make_consumer(queue).consume_bound_once(
        context_factory=make_context_factory(),
        candidates_factory=candidates_factory,
    )

    assert result is None
    assert calls == 0


def test_bound_consumer_requires_timezone_aware_time() -> None:
    """Bound consumption must reject naive timestamps."""
    queue = OpportunityQueue()
    consumer = make_consumer(queue)

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        consumer.consume_bound_once(
            context_factory=make_context_factory(),
            candidates_factory=make_candidate,
            now=datetime.now(),
        )


def test_bound_consumer_preserves_audit_boundary() -> None:
    """Bound execution continues through the existing audit path."""
    now = datetime.now(UTC)
    audit = ExecutionAuditLog()

    opportunity = make_opportunity(
        "opp_audit",
        now=now,
    )

    queue = OpportunityQueue()
    assert queue.enqueue(
        opportunity,
        now=now,
    ) is True

    result = make_consumer(
        queue,
        audit=audit,
    ).consume_bound_once(
        context_factory=make_context_factory(),
        candidates_factory=make_candidate,
        now=now,
    )

    assert result is not None
    assert result.execution_result is not None
    assert result.execution_result.status is ExecutionStatus.COMPLETED
    assert audit.verify_chain() is True
