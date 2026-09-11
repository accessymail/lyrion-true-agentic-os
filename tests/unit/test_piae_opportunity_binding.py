"""Adversarial tests for per-opportunity PIAE context binding."""

from datetime import UTC, datetime, timedelta

import pytest

from lyrion.capabilities.contracts import CapabilityOperation
from lyrion.core.types import (
    AutonomyLevel,
    CorrelationId,
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
from lyrion.piae.contracts import (
    DecisionConstraints,
    Opportunity,
)
from lyrion.piae.opportunity_binding import (
    DeterministicOpportunityContextFactory,
    OpportunityContext,
)


def make_opportunity(
    opportunity_id: str,
    *,
    now: datetime | None = None,
    expires_at: datetime | None = None,
) -> Opportunity:
    """Create a valid opportunity."""
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
        goal_context=("binding-test",),
        title="Binding opportunity",
        description="Per-opportunity binding test.",
        user_relevance=0.9,
        expected_benefit=0.9,
        interruption_cost=0.1,
        risk_score=0.1,
        reversibility=0.9,
        urgency=0.7,
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


def make_intent(
    opportunity: Opportunity,
) -> CapabilityIntent:
    """Create an opportunity-specific capability intent."""
    opportunity_id = str(opportunity.opportunity_id)

    return CapabilityIntent(
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope="lyrion/project/src",
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        task_id=TaskId(
            f"task:{opportunity_id}",
        ),
        risk_level=RiskLevel.LOW,
        justification=(
            f"opportunity:{opportunity_id}: "
            "bounded proactive action"
        ),
        idempotency_key=IdempotencyKey(
            f"idem:{opportunity_id}",
        ),
    )


def make_plan(
    opportunity_id: str,
) -> ExecutionPlan:
    """Create a plan with deterministic opportunity-derived identity."""
    decision_id = f"opportunity:{opportunity_id}"

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


def make_factory(
    opportunity_id: str,
) -> DeterministicOpportunityContextFactory:
    """Create a provider whose resources are bound to one opportunity."""
    return DeterministicOpportunityContextFactory(
        autonomy_level=AutonomyLevel.L1,
        constraints=DecisionConstraints(
            max_risk_level=RiskLevel.LOW,
            requires_human_approval=False,
            allow_external_side_effects=False,
            allow_network_access=False,
            max_cost_units=10.0,
            max_runtime_seconds=30.0,
        ),
        intent_factory=lambda opportunity: (
            make_intent(opportunity)
        ),
        plan_factory=lambda opportunity: (
            make_plan(
                str(opportunity.opportunity_id),
            )
        ),
        sandbox_factory=lambda _opportunity: (
            make_sandbox()
        ),
    )


def test_build_returns_identity_bound_context() -> None:
    """A valid opportunity should receive deterministic context."""
    now = datetime.now(UTC)
    opportunity = make_opportunity(
        "opp_binding_001",
        now=now,
    )

    binding = make_factory(
        str(opportunity.opportunity_id),
    ).build(
        opportunity,
        now=now,
    )

    assert isinstance(
        binding,
        OpportunityContext,
    )
    assert binding.opportunity == opportunity
    assert binding.decision_id == (
        "opportunity:opp_binding_001"
    )
    assert binding.plan is not None
    assert binding.plan.execution_id == (
        "execution:capreq:opportunity:opp_binding_001"
    )


def test_decision_id_is_derived_from_opportunity() -> None:
    """Decision identity must never be independently supplied."""
    now = datetime.now(UTC)
    opportunity = make_opportunity(
        "opp_identity",
        now=now,
    )

    binding = make_factory(
        str(opportunity.opportunity_id),
    ).build(
        opportunity,
        now=now,
    )

    assert binding.decision_id == (
        f"opportunity:{opportunity.opportunity_id}"
    )


def test_execution_plan_must_match_opportunity() -> None:
    """A plan belonging to another opportunity must be rejected."""
    now = datetime.now(UTC)
    opportunity = make_opportunity(
        "opp_a",
        now=now,
    )

    provider = DeterministicOpportunityContextFactory(
        autonomy_level=AutonomyLevel.L1,
        constraints=DecisionConstraints(
            max_risk_level=RiskLevel.LOW,
            requires_human_approval=False,
            allow_external_side_effects=False,
            allow_network_access=False,
            max_cost_units=10.0,
            max_runtime_seconds=30.0,
        ),
        intent_factory=lambda item: make_intent(item),
        plan_factory=lambda _item: make_plan("opp_b"),
        sandbox_factory=lambda _item: make_sandbox(),
    )

    with pytest.raises(
        ValueError,
        match="execution plan is not bound to opportunity",
    ):
        provider.build(
            opportunity,
            now=now,
        )


def test_intent_factory_receives_exact_opportunity() -> None:
    """Factories must receive the exact queued opportunity."""
    now = datetime.now(UTC)
    opportunity = make_opportunity(
        "opp_exact",
        now=now,
    )

    received: list[Opportunity] = []

    def intent_factory(
        item: Opportunity,
    ) -> CapabilityIntent | None:
        received.append(item)
        return None

    provider = DeterministicOpportunityContextFactory(
        autonomy_level=AutonomyLevel.L1,
        constraints=DecisionConstraints(),
        intent_factory=intent_factory,
    )

    provider.build(
        opportunity,
        now=now,
    )

    assert received == [opportunity]


def test_expired_opportunity_is_rejected() -> None:
    """Expired opportunities must never be bound."""
    now = datetime.now(UTC)
    opportunity = make_opportunity(
        "opp_expired",
        now=now,
        expires_at=now,
    )

    provider = make_factory(
        str(opportunity.opportunity_id),
    )

    with pytest.raises(
        ValueError,
        match="expired opportunity",
    ):
        provider.build(
            opportunity,
            now=now,
        )


def test_naive_time_is_rejected() -> None:
    """Binding requires timezone-aware time."""
    opportunity = make_opportunity(
        "opp_naive",
    )

    provider = make_factory(
        str(opportunity.opportunity_id),
    )

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        provider.build(
            opportunity,
            now=datetime.now(),
        )


def test_utc_normalization_is_preserved() -> None:
    """Timezone-aware timestamps should be accepted safely."""
    now = datetime.now(UTC)
    opportunity = make_opportunity(
        "opp_utc",
        now=now,
    )

    binding = make_factory(
        str(opportunity.opportunity_id),
    ).build(
        opportunity,
        now=now,
    )

    assert binding.opportunity.opportunity_id == (
        OpportunityId("opp_utc")
    )


def test_different_opportunities_receive_different_identities() -> None:
    """Two opportunities must never share their decision identity."""
    now = datetime.now(UTC)

    first = make_opportunity(
        "opp_first",
        now=now,
    )
    second = make_opportunity(
        "opp_second",
        now=now,
    )

    provider = DeterministicOpportunityContextFactory(
        autonomy_level=AutonomyLevel.L1,
        constraints=DecisionConstraints(),
        intent_factory=make_intent,
        plan_factory=lambda item: make_plan(
            str(item.opportunity_id),
        ),
        sandbox_factory=lambda _item: make_sandbox(),
    )

    first_binding = provider.build(
        first,
        now=now,
    )
    second_binding = provider.build(
        second,
        now=now,
    )

    assert first_binding.decision_id != (
        second_binding.decision_id
    )
    assert first_binding.intent != second_binding.intent
    assert first_binding.plan != second_binding.plan


def test_opportunity_expiry_remains_external_to_context() -> None:
    """Binding must not extend the opportunity's lifetime."""
    now = datetime.now(UTC)
    expiry = now + timedelta(seconds=1)

    opportunity = make_opportunity(
        "opp_no_extension",
        now=now,
        expires_at=expiry,
    )

    binding = make_factory(
        str(opportunity.opportunity_id),
    ).build(
        opportunity,
        now=now,
    )

    assert binding.opportunity.expires_at == expiry


def test_context_is_frozen() -> None:
    """The binding must be immutable at the dataclass level."""
    now = datetime.now(UTC)
    opportunity = make_opportunity(
        "opp_frozen",
        now=now,
    )

    binding = make_factory(
        str(opportunity.opportunity_id),
    ).build(
        opportunity,
        now=now,
    )

    with pytest.raises(
        AttributeError,
    ):
        binding.decision_id = "forged"  # type: ignore[misc,assignment]


def test_missing_optional_execution_context_is_supported() -> None:
    """Non-executable opportunities can have no intent or plan."""
    now = datetime.now(UTC)
    opportunity = make_opportunity(
        "opp_nonexec",
        now=now,
    )

    provider = DeterministicOpportunityContextFactory(
        autonomy_level=AutonomyLevel.L0,
        constraints=DecisionConstraints(),
    )

    binding = provider.build(
        opportunity,
        now=now,
    )

    assert binding.intent is None
    assert binding.plan is None
    assert binding.sandbox is None


def test_state_and_task_context_are_preserved() -> None:
    """Context collections should pass through without mutation."""
    now = datetime.now(UTC)
    opportunity = make_opportunity(
        "opp_context",
        now=now,
    )

    provider = DeterministicOpportunityContextFactory(
        state_records=(),
        active_task_ids=(
            TaskId("task:context"),
        ),
        autonomy_level=AutonomyLevel.L1,
        constraints=DecisionConstraints(),
    )

    binding = provider.build(
        opportunity,
        now=now,
    )

    assert binding.active_task_ids == (
        TaskId("task:context"),
    )
    assert binding.state_records == ()
