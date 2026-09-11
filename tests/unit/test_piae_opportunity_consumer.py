"""Adversarial tests for queue-driven PIAE consumption."""

from datetime import UTC, datetime, timedelta

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
    urgency: float = 0.8,
    expires_at: datetime | None = None,
) -> Opportunity:
    """Create a valid queue opportunity."""
    current_time = now or datetime.now(UTC)

    return Opportunity(
        opportunity_id=OpportunityId(
            opportunity_id,
        ),
        correlation_id=CorrelationId(
            f"corr:{opportunity_id}",
        ),
        trigger_event_ids=(
            EventId(
                f"event:{opportunity_id}",
            ),
        ),
        relevant_state_ids=(),
        goal_context=(
            "queue-consumer-test",
        ),
        title="Queue consumer opportunity",
        description="A bounded queue consumer action.",
        user_relevance=0.9,
        expected_benefit=0.9,
        interruption_cost=0.1,
        risk_score=0.1,
        reversibility=0.9,
        urgency=urgency,
        confidence=0.95,
        required_capabilities=(
            "development.prepare",
        ),
        required_autonomy_level=AutonomyLevel.L1,
        sensitivity=EventSensitivity.INTERNAL,
        trust_level=EventTrustLevel.SYSTEM,
        created_at=current_time,
        expires_at=expires_at,
    )


def make_candidate() -> DecisionCandidate:
    """Create a safe executable candidate."""
    return DecisionCandidate(
        action=DecisionAction.EXECUTE,
        rationale=DecisionReason.EFFICIENCY,
        explanation="Execute a bounded queued action.",
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


def make_intent() -> CapabilityIntent:
    """Create a safe capability intent."""
    return CapabilityIntent(
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope="lyrion/project/src",
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        task_id="task:queue-consumer",
        risk_level=RiskLevel.LOW,
        justification="Run bounded queue consumer action.",
        idempotency_key=IdempotencyKey(
            "idem:queue-consumer",
        ),
    )


def make_plan(opportunity: Opportunity) -> ExecutionPlan:
    """Create a plan matching the deterministic consumer identity."""
    decision_id = f"opportunity:{opportunity.opportunity_id}"

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


def make_consumer(
    *,
    audit: ExecutionAuditLog | None = None,
) -> OpportunityConsumer:
    """Create the complete queue consumer."""
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
        OpportunityQueue(),
        PIAEActionLoop(coordinator),
    )


def test_consumer_executes_highest_priority_opportunity() -> None:
    """The consumer should execute the queue's highest-priority item."""
    now = datetime.now(UTC)

    queue = OpportunityQueue()

    low = make_opportunity(
        "opp_low",
        now=now,
        urgency=0.2,
    )

    high = make_opportunity(
        "opp_high",
        now=now,
        urgency=0.9,
    )

    queue.enqueue(low, now=now)
    queue.enqueue(high, now=now)

    consumer = OpportunityConsumer(
        queue,
        make_consumer().action_loop,
    )

    result = consumer.consume_once(
        candidates=(make_candidate(),),
        intent=make_intent(),
        plan=make_plan(high),
        sandbox=make_sandbox(),
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
        now=now,
    )

    assert result is not None
    assert result.decision.selected_action is DecisionAction.EXECUTE
    assert result.execution_result is not None
    assert result.execution_result.status is ExecutionStatus.COMPLETED

    assert queue.contains(
        low.opportunity_id,
        now=now,
    )


def test_empty_queue_returns_none() -> None:
    """An empty queue should not invoke PIAE."""
    consumer = make_consumer()

    result = consumer.consume_once(
        candidates=(),
        intent=None,
        plan=None,
        sandbox=None,
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
    )

    assert result is None


def test_expired_opportunity_is_not_executed() -> None:
    """Expired opportunities must never cross into execution."""
    now = datetime.now(UTC)

    queue = OpportunityQueue()

    expired = make_opportunity(
        "opp_expired",
        now=now,
        expires_at=now + timedelta(seconds=1),
    )

    queue.enqueue(
        expired,
        now=now,
    )

    consumer = OpportunityConsumer(
        queue,
        make_consumer().action_loop,
    )

    result = consumer.consume_once(
        candidates=(),
        intent=None,
        plan=None,
        sandbox=None,
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
        now=now + timedelta(seconds=2),
    )

    assert result is None


def test_consumer_removes_dequeued_opportunity() -> None:
    """A consumed opportunity should no longer remain queued."""
    now = datetime.now(UTC)

    queue = OpportunityQueue()

    opportunity = make_opportunity(
        "opp_removed",
        now=now,
    )

    queue.enqueue(
        opportunity,
        now=now,
    )

    consumer = OpportunityConsumer(
        queue,
        make_consumer().action_loop,
    )

    result = consumer.consume_once(
        candidates=(make_candidate(),),
        intent=make_intent(),
        plan=make_plan(opportunity),
        sandbox=make_sandbox(),
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
        now=now,
    )

    assert result is not None
    assert queue.contains(
        opportunity.opportunity_id,
        now=now,
    ) is False


def test_consumer_preserves_opportunity_identity() -> None:
    """The opportunity identity must reach the resulting request."""
    now = datetime.now(UTC)

    queue = OpportunityQueue()

    opportunity = make_opportunity(
        "opp_identity",
        now=now,
    )

    queue.enqueue(
        opportunity,
        now=now,
    )

    consumer = OpportunityConsumer(
        queue,
        make_consumer().action_loop,
    )

    result = consumer.consume_once(
        candidates=(make_candidate(),),
        intent=make_intent(),
        plan=make_plan(opportunity),
        sandbox=make_sandbox(),
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
        now=now,
    )

    assert result is not None
    assert result.decision.decision_id == (
        f"opportunity:{opportunity.opportunity_id}"
    )
    assert result.capability_request is not None
    assert result.capability_request.decision_id == (
        result.decision.decision_id
    )


def test_consumer_requires_timezone_aware_now() -> None:
    """Queue consumption must preserve timezone safety."""
    opportunity = make_opportunity(
        "opp_naive",
    )

    queue = OpportunityQueue()

    queue.enqueue(
        opportunity,
        now=opportunity.created_at,
    )

    consumer = OpportunityConsumer(
        queue,
        make_consumer().action_loop,
    )

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        consumer.consume_once(
            candidates=(),
            intent=None,
            plan=None,
            sandbox=None,
            autonomy_level=AutonomyLevel.L1,
            constraints=make_constraints(),
            now=datetime.now(),
        )


def test_denied_execution_still_consumes_opportunity() -> None:
    """Authorization denial should not leave a consumed item queued."""
    now = datetime.now(UTC)

    queue = OpportunityQueue()

    opportunity = make_opportunity(
        "opp_denied",
        now=now,
    )

    queue.enqueue(
        opportunity,
        now=now,
    )

    consumer = make_consumer()

    result = OpportunityConsumer(
        queue,
        consumer.action_loop,
    ).consume_once(
        candidates=(make_candidate(),),
        intent=CapabilityIntent(
            principal_id="lyrion-piae",
            capability_id="development.prepare",
            target_scope="protected/system",
            operation=CapabilityOperation.READ,
            data_classification=EventSensitivity.INTERNAL,
            task_id="task:denied",
            risk_level=RiskLevel.LOW,
            justification="Test authorization denial.",
            idempotency_key=IdempotencyKey(
                "idem:denied",
            ),
        ),
        plan=make_plan(opportunity),
        sandbox=make_sandbox(),
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
        now=now,
    )

    assert result is not None
    assert result.admission is not None
    assert result.admission.admitted is False
    assert queue.size(now=now) == 0


def test_audit_survives_queue_consumption() -> None:
    """Queue-driven execution should preserve audit evidence."""
    now = datetime.now(UTC)
    audit = ExecutionAuditLog()

    queue = OpportunityQueue()

    opportunity = make_opportunity(
        "opp_audit",
        now=now,
    )

    queue.enqueue(
        opportunity,
        now=now,
    )

    consumer = make_consumer(
        audit=audit,
    )

    result = OpportunityConsumer(
        queue,
        consumer.action_loop,
    ).consume_once(
        candidates=(make_candidate(),),
        intent=make_intent(),
        plan=make_plan(opportunity),
        sandbox=make_sandbox(),
        autonomy_level=AutonomyLevel.L1,
        constraints=make_constraints(),
        now=now,
    )

    assert result is not None
    assert result.execution_result is not None
    assert result.execution_result.status is ExecutionStatus.COMPLETED
    assert audit.verify_chain() is True


def test_consumer_does_not_authorize_directly() -> None:
    """Authorization must remain delegated to the existing action path."""
    consumer = make_consumer()

    assert hasattr(
        consumer,
        "action_loop",
    )
    assert hasattr(
        consumer.action_loop,
        "coordinator",
    )
