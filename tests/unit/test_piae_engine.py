"""Adversarial unit tests for the Lyrion PIAE decision engine."""

from datetime import UTC, datetime, timedelta

import pytest

from lyrion.core.types import (
    AutonomyLevel,
    DecisionAction,
    EventId,
    OpportunityId,
    RiskLevel,
)
from lyrion.events.models import EventSensitivity, EventTrustLevel
from lyrion.piae.contracts import (
    DecisionCandidate,
    DecisionConstraints,
    DecisionContext,
    DecisionReason,
    Opportunity,
    OpportunityStatus,
    PolicyResult,
)
from lyrion.piae.engine import PIAEDecisionEngine


def make_opportunity(**overrides: object) -> Opportunity:
    """Create a valid baseline proactive opportunity."""
    now = datetime.now(UTC)

    values: dict[str, object] = {
        "opportunity_id": OpportunityId("opp_engine_test"),
        "trigger_event_ids": (EventId("evt_engine_test"),),
        "relevant_state_ids": (),
        "goal_context": ("test_goal",),
        "title": "Engine test opportunity",
        "description": "Test deterministic PIAE behavior.",
        "user_relevance": 0.9,
        "expected_benefit": 0.9,
        "interruption_cost": 0.1,
        "risk_score": 0.1,
        "reversibility": 1.0,
        "urgency": 0.8,
        "confidence": 0.95,
        "required_capabilities": (),
        "required_autonomy_level": AutonomyLevel.L1,
        "sensitivity": EventSensitivity.INTERNAL,
        "trust_level": EventTrustLevel.SYSTEM,
        "status": OpportunityStatus.OPEN,
        "created_at": now,
        "expires_at": now + timedelta(minutes=5),
    }

    values.update(overrides)
    return Opportunity(**values)


def make_constraints(**overrides: object) -> DecisionConstraints:
    """Create valid decision constraints."""
    values: dict[str, object] = {
        "max_risk_level": RiskLevel.LOW,
        "requires_human_approval": False,
        "allow_external_side_effects": False,
        "allow_network_access": False,
        "max_cost_units": 10.0,
        "max_runtime_seconds": 30.0,
    }

    values.update(overrides)
    return DecisionConstraints(**values)


def make_context(
    *,
    opportunity: Opportunity | None = None,
    constraints: DecisionConstraints | None = None,
    autonomy_level: AutonomyLevel = AutonomyLevel.L1,
) -> DecisionContext:
    """Create a valid decision context."""
    return DecisionContext(
        opportunity=opportunity or make_opportunity(),
        state_records=(),
        active_task_ids=(),
        autonomy_level=autonomy_level,
        constraints=constraints or make_constraints(),
        now=datetime.now(UTC),
    )


def make_candidate(**overrides: object) -> DecisionCandidate:
    """Create a valid decision candidate."""
    values: dict[str, object] = {
        "action": DecisionAction.SUGGEST,
        "rationale": DecisionReason.GOAL_ALIGNMENT,
        "explanation": "The candidate supports the current goal.",
        "confidence": 0.95,
        "estimated_risk": RiskLevel.LOW,
        "estimated_cost_units": 1.0,
        "estimated_runtime_seconds": 2.0,
        "requires_human_approval": False,
        "has_external_side_effect": False,
        "requires_network_access": False,
    }

    values.update(overrides)
    return DecisionCandidate(**values)


@pytest.fixture
def engine() -> PIAEDecisionEngine:
    """Provide a fresh decision engine."""
    return PIAEDecisionEngine()


def test_expired_opportunity_returns_wait(engine: PIAEDecisionEngine) -> None:
    """Expired opportunities must not produce actionable decisions."""
    created = datetime.now(UTC)

    opportunity = make_opportunity(
        created_at=created - timedelta(minutes=10),
        expires_at=created - timedelta(seconds=1),
    )

    context = make_context(opportunity=opportunity)
    candidate = make_candidate()

    result = engine.decide(context, (candidate,))

    assert result.selected_action is DecisionAction.WAIT
    assert result.reason_codes[0] is DecisionReason.TIME_SENSITIVITY
    assert result.authorization_required is False
    assert result.authorization_granted is False


def test_no_candidates_returns_wait(engine: PIAEDecisionEngine) -> None:
    """No candidate should result in a safe wait decision."""
    context = make_context()

    result = engine.decide(context, ())

    assert result.selected_action is DecisionAction.WAIT
    assert result.reason_codes[0] is DecisionReason.INSUFFICIENT_CONFIDENCE
    assert result.candidate_count == 0


def test_excessive_risk_candidate_is_denied(
    engine: PIAEDecisionEngine,
) -> None:
    """Candidates above the configured risk bound must be denied."""
    constraints = make_constraints(max_risk_level=RiskLevel.LOW)
    context = make_context(constraints=constraints)

    candidate = make_candidate(
        action=DecisionAction.EXECUTE,
        estimated_risk=RiskLevel.HIGH,
    )

    result = engine.decide(context, (candidate,))

    assert result.selected_action is DecisionAction.DENY
    assert result.authorization_result is PolicyResult.DENIED
    assert result.policy_result is PolicyResult.DENIED
    assert result.authorization_granted is False


def test_medium_risk_is_accepted_when_constraint_allows_it(
    engine: PIAEDecisionEngine,
) -> None:
    """A candidate within the risk bound may remain admissible."""
    constraints = make_constraints(max_risk_level=RiskLevel.MEDIUM)
    context = make_context(constraints=constraints)

    candidate = make_candidate(
        estimated_risk=RiskLevel.MEDIUM,
    )

    result = engine.decide(context, (candidate,))

    assert result.selected_action is DecisionAction.SUGGEST
    assert result.authorization_granted is False


def test_cost_budget_violation_is_denied(
    engine: PIAEDecisionEngine,
) -> None:
    """Candidates exceeding cost limits must be rejected."""
    constraints = make_constraints(max_cost_units=1.0)
    context = make_context(constraints=constraints)

    candidate = make_candidate(
        estimated_cost_units=2.0,
    )

    result = engine.decide(context, (candidate,))

    assert result.selected_action is DecisionAction.DENY
    assert result.policy_result is PolicyResult.DENIED


def test_runtime_budget_violation_is_denied(
    engine: PIAEDecisionEngine,
) -> None:
    """Candidates exceeding runtime limits must be rejected."""
    constraints = make_constraints(max_runtime_seconds=1.0)
    context = make_context(constraints=constraints)

    candidate = make_candidate(
        estimated_runtime_seconds=2.0,
    )

    result = engine.decide(context, (candidate,))

    assert result.selected_action is DecisionAction.DENY
    assert result.policy_result is PolicyResult.DENIED


def test_external_side_effect_is_escalated_when_disallowed(
    engine: PIAEDecisionEngine,
) -> None:
    """External side effects must escalate when not permitted."""
    constraints = make_constraints(
        allow_external_side_effects=False,
    )
    context = make_context(constraints=constraints)

    candidate = make_candidate(
        action=DecisionAction.EXECUTE,
        has_external_side_effect=True,
    )

    result = engine.decide(context, (candidate,))

    assert result.selected_action is DecisionAction.ESCALATE
    assert result.reason_codes[0] is DecisionReason.POLICY
    assert result.authorization_required is True
    assert result.authorization_result is PolicyResult.REQUIRES_APPROVAL
    assert result.authorization_granted is False


def test_network_access_is_escalated_when_disallowed(
    engine: PIAEDecisionEngine,
) -> None:
    """Network-dependent candidates must escalate when network is disallowed."""
    constraints = make_constraints(
        allow_network_access=False,
    )
    context = make_context(constraints=constraints)

    candidate = make_candidate(
        action=DecisionAction.EXECUTE,
        requires_network_access=True,
    )

    result = engine.decide(context, (candidate,))

    assert result.selected_action is DecisionAction.ESCALATE
    assert result.reason_codes[0] is DecisionReason.POLICY
    assert result.authorization_required is True
    assert result.authorization_granted is False


def test_human_approval_requirement_is_preserved(
    engine: PIAEDecisionEngine,
) -> None:
    """A candidate requiring approval must never self-authorize."""
    context = make_context()

    candidate = make_candidate(
        action=DecisionAction.EXECUTE,
        requires_human_approval=True,
    )

    result = engine.decide(context, (candidate,))

    assert result.selected_action is DecisionAction.EXECUTE
    assert result.authorization_required is True
    assert result.authorization_result is PolicyResult.REQUIRES_APPROVAL
    assert result.authorization_granted is False


def test_same_inputs_produce_deterministic_substantive_decision(
    engine: PIAEDecisionEngine,
) -> None:
    """Equal context and candidates must yield equal decision semantics."""
    created = datetime.now(UTC)
    expires = created + timedelta(minutes=5)

    opportunity = make_opportunity(
        created_at=created,
        expires_at=expires,
    )
    context = make_context(opportunity=opportunity)
    candidate = make_candidate()

    first = engine.decide(
        context,
        (candidate,),
        input_context_ref="determinism_test",
    )
    second = engine.decide(
        context,
        (candidate,),
        input_context_ref="determinism_test",
    )

    assert first.selected_action is second.selected_action
    assert first.reason_codes == second.reason_codes
    assert first.utility_estimate == second.utility_estimate
    assert first.confidence == second.confidence
    assert first.risk_estimate == second.risk_estimate


def test_multiple_candidates_select_highest_scoring_candidate(
    engine: PIAEDecisionEngine,
) -> None:
    """The engine should deterministically select the highest-scoring candidate."""
    context = make_context()

    low_value = make_candidate(
        action=DecisionAction.WAIT,
        rationale=DecisionReason.EFFICIENCY,
        confidence=0.2,
        estimated_cost_units=2.0,
    )
    high_value = make_candidate(
        action=DecisionAction.SUGGEST,
        rationale=DecisionReason.GOAL_ALIGNMENT,
        confidence=0.95,
        estimated_cost_units=0.1,
    )

    result = engine.decide(
        context,
        (low_value, high_value),
    )

    assert result.selected_action is DecisionAction.SUGGEST
    assert result.candidate_count == 2


def test_decision_never_grants_authorization(
    engine: PIAEDecisionEngine,
) -> None:
    """PIAE must never grant authorization itself."""
    context = make_context()

    candidate = make_candidate(
        action=DecisionAction.EXECUTE,
        requires_human_approval=False,
        has_external_side_effect=False,
        requires_network_access=False,
    )

    result = engine.decide(context, (candidate,))

    assert result.authorization_granted is False


def test_decision_result_preserves_opportunity_expiry(
    engine: PIAEDecisionEngine,
) -> None:
    """Decision expiry should inherit the opportunity expiry."""
    context = make_context()

    candidate = make_candidate()

    result = engine.decide(context, (candidate,))

    assert result.expires_at == context.opportunity.expires_at


def test_low_confidence_candidate_is_still_bounded(
    engine: PIAEDecisionEngine,
) -> None:
    """Low-confidence candidates must remain within explicit safe outcomes."""
    context = make_context()

    candidate = make_candidate(
        confidence=0.01,
    )

    result = engine.decide(context, (candidate,))

    assert result.selected_action in {
        DecisionAction.WAIT,
        DecisionAction.SUGGEST,
        DecisionAction.PREPARE,
        DecisionAction.EXECUTE,
        DecisionAction.ESCALATE,
        DecisionAction.DENY,
    }
    assert 0.0 <= result.confidence <= 1.0


def test_denied_candidate_has_no_authority(
    engine: PIAEDecisionEngine,
) -> None:
    """A denied decision must carry no execution authority."""
    context = make_context(
        constraints=make_constraints(max_risk_level=RiskLevel.LOW),
    )

    candidate = make_candidate(
        action=DecisionAction.EXECUTE,
        estimated_risk=RiskLevel.CRITICAL,
    )

    result = engine.decide(context, (candidate,))

    assert result.selected_action is DecisionAction.DENY
    assert result.authorization_required is False
    assert result.authorization_granted is False
