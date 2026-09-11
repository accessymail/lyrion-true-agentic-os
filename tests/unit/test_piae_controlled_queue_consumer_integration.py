"""Real integration tests for bounded PIAE queue consumption."""

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
from lyrion.piae.action_loop import PIAEActionLoop
from lyrion.piae.contracts import (
    DecisionCandidate,
    DecisionConstraints,
    DecisionReason,
    Opportunity,
)
from lyrion.piae.controlled_queue_consumer import (
    ControlledQueueConsumer,
    ControlledQueueConsumerConfig,
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
    now: datetime,
    urgency: float,
) -> Opportunity:
    """Create a valid executable opportunity."""
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
            "controlled-consumer-integration",
        ),
        title="Controlled consumer opportunity",
        description="Real queue-to-executor integration test.",
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
        created_at=now,
        expires_at=None,
    )


def make_candidate(
    opportunity: Opportunity,
) -> tuple[DecisionCandidate, ...]:
    """Create a safe executable candidate for one opportunity."""
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
    """Create capability intent scoped to one opportunity."""
    opportunity_id = str(
        opportunity.opportunity_id,
    )

    return CapabilityIntent(
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope=(
            f"lyrion/project/{opportunity_id}"
        ),
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        task_id=TaskId(
            f"task:{opportunity_id}",
        ),
        risk_level=RiskLevel.LOW,
        justification=(
            f"opportunity:{opportunity_id}: "
            "controlled consumer integration"
        ),
        idempotency_key=IdempotencyKey(
            f"idem:{opportunity_id}",
        ),
    )


def make_plan(
    opportunity: Opportunity,
) -> ExecutionPlan:
    """Create an execution plan matching opportunity identity."""
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


def make_consumer(
    queue: OpportunityQueue,
) -> OpportunityConsumer:
    """Create the real secure PIAE opportunity consumer."""
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
        executor=SecureExecutor(),
    )

    return OpportunityConsumer(
        queue,
        PIAEActionLoop(coordinator),
    )


def make_controller(
    queue: OpportunityQueue,
    *,
    max_opportunities: int,
) -> ControlledQueueConsumer:
    """Create the real bounded queue consumer."""
    context_factory = (
        DeterministicOpportunityContextFactory(
            autonomy_level=AutonomyLevel.L1,
            constraints=make_constraints(),
            intent_factory=make_intent,
            plan_factory=make_plan,
            sandbox_factory=lambda _opportunity: (
                make_sandbox()
            ),
        )
    )

    return ControlledQueueConsumer(
        queue,
        make_consumer(queue),
        context_factory,
        ControlledQueueConsumerConfig(
            max_opportunities_per_cycle=(
                max_opportunities
            ),
        ),
    )


def enqueue_opportunities(
    queue: OpportunityQueue,
    *,
    now: datetime,
) -> tuple[Opportunity, ...]:
    """Add three deterministically prioritized opportunities."""
    opportunities = (
        make_opportunity(
            "opp_controlled_a",
            now=now,
            urgency=0.9,
        ),
        make_opportunity(
            "opp_controlled_b",
            now=now,
            urgency=0.8,
        ),
        make_opportunity(
            "opp_controlled_c",
            now=now,
            urgency=0.7,
        ),
    )

    for opportunity in opportunities:
        assert queue.enqueue(
            opportunity,
            now=now,
        ) is True

    return opportunities


def test_real_consumer_respects_cycle_limit() -> None:
    """The real consumer must process no more than N opportunities."""
    now = datetime.now(UTC)
    queue = OpportunityQueue()

    opportunities = enqueue_opportunities(
        queue,
        now=now,
    )

    result = make_controller(
        queue,
        max_opportunities=2,
    ).run_once(
        candidates_factory=make_candidate,
        now=now,
    )

    assert result.attempted_count == 2
    assert result.succeeded_count == 2
    assert result.failed_count == 0
    assert result.stop_reason == (
        "MAX_OPPORTUNITIES_REACHED"
    )

    assert tuple(
        item.opportunity_id
        for item in result.items
    ) == (
        str(opportunities[0].opportunity_id),
        str(opportunities[1].opportunity_id),
    )

    assert queue.contains(
        opportunities[2].opportunity_id,
        now=now,
    )


def test_real_consumer_processes_remaining_item_on_next_cycle() -> None:
    """A second bounded cycle should process the remaining opportunity."""
    now = datetime.now(UTC)
    queue = OpportunityQueue()

    opportunities = enqueue_opportunities(
        queue,
        now=now,
    )

    controller = make_controller(
        queue,
        max_opportunities=2,
    )

    first = controller.run_once(
        candidates_factory=make_candidate,
        now=now,
    )

    second = controller.run_once(
        candidates_factory=make_candidate,
        now=now,
    )

    assert first.attempted_count == 2
    assert second.attempted_count == 1
    assert second.succeeded_count == 1
    assert second.stop_reason == "QUEUE_EMPTY"

    assert second.items[0].opportunity_id == (
        str(opportunities[2].opportunity_id)
    )

    assert queue.size(now=now) == 0


def test_real_consumer_preserves_piae_execution_identity() -> None:
    """Real execution must preserve opportunity-derived identity."""
    now = datetime.now(UTC)
    queue = OpportunityQueue()

    opportunity = make_opportunity(
        "opp_identity_real",
        now=now,
        urgency=0.9,
    )

    assert queue.enqueue(
        opportunity,
        now=now,
    ) is True

    controller = make_controller(
        queue,
        max_opportunities=1,
    )

    result = controller.run_once(
        candidates_factory=make_candidate,
        now=now,
    )

    assert result.succeeded_count == 1

    item = result.items[0]

    assert item.result is not None
    assert item.result.decision.decision_id == (
        f"opportunity:{opportunity.opportunity_id}"
    )

    assert item.result.capability_request is not None
    assert item.result.capability_request.decision_id == (
        item.result.decision.decision_id
    )

    assert item.result.execution_result is not None
    assert item.result.execution_result.execution_id == (
        f"execution:capreq:{item.result.decision.decision_id}"
    )

    assert item.result.execution_result.status is (
        ExecutionStatus.COMPLETED
    )


def test_real_consumer_isolates_candidate_failure() -> None:
    """One failed opportunity must not stop later opportunities."""
    now = datetime.now(UTC)
    queue = OpportunityQueue()

    opportunities = enqueue_opportunities(
        queue,
        now=now,
    )

    failed_once = False

    def candidates_factory(
        opportunity: Opportunity,
    ) -> tuple[DecisionCandidate, ...]:
        nonlocal failed_once

        if (
            opportunity.opportunity_id
            == opportunities[0].opportunity_id
            and not failed_once
        ):
            failed_once = True
            raise RuntimeError(
                "intentional candidate-generation failure"
            )

        return make_candidate(opportunity)

    result = make_controller(
        queue,
        max_opportunities=2,
    ).run_once(
        candidates_factory=candidates_factory,
        now=now,
    )

    assert result.attempted_count == 2
    assert result.failed_count == 1
    assert result.succeeded_count == 1
    assert result.stop_reason == (
        "MAX_OPPORTUNITIES_REACHED"
    )

    assert result.items[0].opportunity_id == (
        str(opportunities[0].opportunity_id)
    )
    assert result.items[0].succeeded is False
    assert result.items[0].error_type == "RuntimeError"

    assert result.items[1].opportunity_id == (
        str(opportunities[1].opportunity_id)
    )
    assert result.items[1].succeeded is True

    assert queue.contains(
        opportunities[2].opportunity_id,
        now=now,
    )


def test_real_consumer_does_not_retry_failed_item_implicitly() -> None:
    """A failed dequeued opportunity must not return automatically."""
    now = datetime.now(UTC)
    queue = OpportunityQueue()

    opportunities = enqueue_opportunities(
        queue,
        now=now,
    )

    def candidates_factory(
        opportunity: Opportunity,
    ) -> tuple[DecisionCandidate, ...]:
        if (
            opportunity.opportunity_id
            == opportunities[0].opportunity_id
        ):
            raise RuntimeError(
                "terminal test failure"
            )

        return make_candidate(opportunity)

    result = make_controller(
        queue,
        max_opportunities=1,
    ).run_once(
        candidates_factory=candidates_factory,
        now=now,
    )

    assert result.attempted_count == 1
    assert result.failed_count == 1
    assert result.items[0].succeeded is False

    assert queue.contains(
        opportunities[0].opportunity_id,
        now=now,
    ) is False

    assert queue.contains(
        opportunities[1].opportunity_id,
        now=now,
    ) is True


def test_real_consumer_rejects_naive_time() -> None:
    """The real bounded consumer must preserve time validation."""
    queue = OpportunityQueue()

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        make_controller(
            queue,
            max_opportunities=1,
        ).run_once(
            candidates_factory=make_candidate,
            now=datetime.now(),
        )
