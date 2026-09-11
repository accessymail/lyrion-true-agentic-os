"""Unit tests for Lyrion PIAE decision contracts."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lyrion.core.types import (
    AutonomyLevel,
    CorrelationId,
    DecisionAction,
    DecisionId,
    EventId,
    IdempotencyKey,
    OpportunityId,
    RiskLevel,
    TaskId,
)
from lyrion.events.models import EventSensitivity, EventTrustLevel
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


def make_opportunity(**overrides: object) -> Opportunity:
    """Create a valid baseline opportunity for tests."""
    now = datetime.now(UTC)

    values: dict[str, object] = {
        "opportunity_id": OpportunityId("opp_test_001"),
        "correlation_id": CorrelationId("corr_test_001"),
        "trigger_event_ids": (EventId("evt_test_001"),),
        "relevant_state_ids": ("state_test_001",),
        "goal_context": ("test_goal",),
        "title": "Test opportunity",
        "description": "Validate proactive decision contracts.",
        "user_relevance": 0.9,
        "expected_benefit": 0.85,
        "interruption_cost": 0.1,
        "risk_score": 0.1,
        "reversibility": 0.95,
        "urgency": 0.5,
        "confidence": 0.9,
        "required_capabilities": ("test_capability",),
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
    """Create a valid baseline decision constraint set."""
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


def make_context(**overrides: object) -> DecisionContext:
    """Create a valid baseline decision context."""
    now = datetime.now(UTC)

    values: dict[str, object] = {
        "opportunity": make_opportunity(),
        "state_records": (),
        "active_task_ids": (TaskId("task_test_001"),),
        "autonomy_level": AutonomyLevel.L1,
        "constraints": make_constraints(),
        "now": now,
    }

    values.update(overrides)
    return DecisionContext(**values)


def make_candidate(**overrides: object) -> DecisionCandidate:
    """Create a valid baseline decision candidate."""
    values: dict[str, object] = {
        "action": DecisionAction.SUGGEST,
        "rationale": DecisionReason.CONTEXT_RELEVANCE,
        "explanation": "The opportunity is relevant to the current context.",
        "confidence": 0.9,
        "estimated_risk": RiskLevel.LOW,
        "estimated_cost_units": 1.0,
        "estimated_runtime_seconds": 5.0,
        "requires_human_approval": False,
        "has_external_side_effect": False,
        "requires_network_access": False,
    }

    values.update(overrides)
    return DecisionCandidate(**values)


def make_result(**overrides: object) -> DecisionResult:
    """Create a valid baseline decision result."""
    now = datetime.now(UTC)

    values: dict[str, object] = {
        "decision_id": DecisionId("decision_test_001"),
        "input_context_ref": "context_test_001",
        "opportunity_ref": OpportunityId("opp_test_001"),
        "selected_action": DecisionAction.SUGGEST,
        "alternative_actions": (DecisionAction.WAIT,),
        "utility_estimate": 0.85,
        "interruption_cost": 0.1,
        "risk_estimate": 0.1,
        "autonomy_level": AutonomyLevel.L1,
        "authorization_result": PolicyResult.NOT_EVALUATED,
        "policy_result": PolicyResult.NOT_EVALUATED,
        "confidence": 0.9,
        "reason_codes": (DecisionReason.CONTEXT_RELEVANCE,),
        "authorization_required": False,
        "authorization_granted": False,
        "candidate_count": 1,
        "correlation_id": CorrelationId("corr_test_001"),
        "idempotency_key": IdempotencyKey("idem_test_001"),
        "expires_at": now + timedelta(minutes=5),
        "decided_at": now,
    }

    values.update(overrides)
    return DecisionResult(**values)


def test_opportunity_creation() -> None:
    """A valid opportunity should be accepted."""
    opportunity = make_opportunity()

    assert opportunity.opportunity_id == "opp_test_001"
    assert opportunity.status is OpportunityStatus.OPEN
    assert opportunity.user_relevance == 0.9
    assert opportunity.expected_benefit == 0.85
    assert opportunity.required_autonomy_level is AutonomyLevel.L1


def test_opportunity_is_immutable() -> None:
    """Opportunity fields must not be mutable after construction."""
    opportunity = make_opportunity()

    with pytest.raises(ValidationError):
        opportunity.title = "changed"


def test_opportunity_requires_timezone_aware_created_at() -> None:
    """Opportunity creation time must be timezone-aware."""
    with pytest.raises(ValidationError):
        make_opportunity(created_at=datetime.now())


def test_opportunity_rejects_invalid_expiry() -> None:
    """Opportunity expiry cannot precede creation."""
    created = datetime.now(UTC)

    with pytest.raises(ValidationError):
        make_opportunity(
            created_at=created,
            expires_at=created - timedelta(seconds=1),
        )


def test_opportunity_expiry_behavior() -> None:
    """Expired opportunities should be detectable."""
    created = datetime.now(UTC)

    opportunity = make_opportunity(
        created_at=created,
        expires_at=created + timedelta(seconds=1),
    )

    assert opportunity.is_expired(created) is False
    assert opportunity.is_expired(created + timedelta(seconds=2)) is True


def test_opportunity_requires_trigger_event() -> None:
    """An opportunity must reference at least one triggering event."""
    with pytest.raises(ValidationError):
        make_opportunity(trigger_event_ids=())


def test_opportunity_rejects_duplicate_trigger_events() -> None:
    """Triggering event references must be unique."""
    with pytest.raises(ValidationError):
        make_opportunity(
            trigger_event_ids=(
                EventId("evt_same"),
                EventId("evt_same"),
            )
        )


def test_opportunity_rejects_duplicate_capabilities() -> None:
    """Required capability identifiers must be unique."""
    with pytest.raises(ValidationError):
        make_opportunity(
            required_capabilities=(
                "test_capability",
                "test_capability",
            )
        )


def test_opportunity_rejects_invalid_scoring() -> None:
    """Opportunity scores must stay within the 0..1 range."""
    with pytest.raises(ValidationError):
        make_opportunity(user_relevance=1.1)

    with pytest.raises(ValidationError):
        make_opportunity(expected_benefit=-0.1)

    with pytest.raises(ValidationError):
        make_opportunity(interruption_cost=1.1)

    with pytest.raises(ValidationError):
        make_opportunity(risk_score=-0.1)

    with pytest.raises(ValidationError):
        make_opportunity(reversibility=1.1)


def test_decision_constraints_reject_invalid_limits() -> None:
    """Cost and runtime limits must remain valid."""
    with pytest.raises(ValidationError):
        make_constraints(max_cost_units=-1)

    with pytest.raises(ValidationError):
        make_constraints(max_runtime_seconds=0)


def test_decision_context_creation() -> None:
    """A valid decision context should be accepted."""
    context = make_context()

    assert context.autonomy_level is AutonomyLevel.L1
    assert context.active_task_ids == ("task_test_001",)


def test_decision_context_requires_timezone_aware_now() -> None:
    """Decision context time must be timezone-aware."""
    with pytest.raises(ValidationError):
        make_context(now=datetime.now())


def test_decision_candidate_creation() -> None:
    """A valid decision candidate should be accepted."""
    candidate = make_candidate()

    assert candidate.action is DecisionAction.SUGGEST
    assert candidate.estimated_risk is RiskLevel.LOW


def test_decision_candidate_rejects_invalid_confidence() -> None:
    """Candidate confidence must remain within 0..1."""
    with pytest.raises(ValidationError):
        make_candidate(confidence=1.1)

    with pytest.raises(ValidationError):
        make_candidate(confidence=-0.1)


def test_decision_candidate_rejects_negative_cost() -> None:
    """Candidate estimated cost cannot be negative."""
    with pytest.raises(ValidationError):
        make_candidate(estimated_cost_units=-1)


def test_decision_result_creation() -> None:
    """A valid decision result should be accepted."""
    result = make_result()

    assert result.decision_id == "decision_test_001"
    assert result.input_context_ref == "context_test_001"
    assert result.opportunity_ref == "opp_test_001"
    assert result.selected_action is DecisionAction.SUGGEST
    assert result.authorization_result is PolicyResult.NOT_EVALUATED
    assert result.policy_result is PolicyResult.NOT_EVALUATED
    assert result.reason_codes == (DecisionReason.CONTEXT_RELEVANCE,)


def test_decision_result_requires_timezone_aware_time() -> None:
    """Decision result time must be timezone-aware."""
    with pytest.raises(ValidationError):
        make_result(decided_at=datetime.now())


def test_decision_result_is_immutable() -> None:
    """Decision results must not be mutable after construction."""
    result = make_result()

    with pytest.raises(ValidationError):
        result.explanation = "changed"


def test_decision_result_rejects_negative_candidate_count() -> None:
    """Candidate count cannot be negative."""
    with pytest.raises(ValidationError):
        make_result(candidate_count=-1)


def test_decision_result_rejects_invalid_utility() -> None:
    """Utility estimates must remain within 0..1."""
    with pytest.raises(ValidationError):
        make_result(utility_estimate=1.1)

    with pytest.raises(ValidationError):
        make_result(utility_estimate=-0.1)


def test_decision_result_rejects_duplicate_alternatives() -> None:
    """Alternative actions must be unique."""
    with pytest.raises(ValidationError):
        make_result(
            alternative_actions=(
                DecisionAction.WAIT,
                DecisionAction.WAIT,
            )
        )


def test_decision_result_rejects_empty_reason_codes() -> None:
    """Every decision must contain at least one structured reason code."""
    with pytest.raises(ValidationError):
        make_result(reason_codes=())


def test_contracts_reject_unknown_fields() -> None:
    """Contract models must reject undeclared fields."""
    with pytest.raises(ValidationError):
        make_opportunity(unknown_field="not-allowed")

    with pytest.raises(ValidationError):
        make_candidate(unknown_field="not-allowed")

    with pytest.raises(ValidationError):
        make_result(unknown_field="not-allowed")


def test_decision_reason_policy_is_explicit() -> None:
    """Decision reasons should remain explicit enum values."""
    assert DecisionReason.SAFETY.value == "SAFETY"
    assert DecisionReason.POLICY.value == "POLICY"
    assert (
        DecisionReason.INSUFFICIENT_CONFIDENCE.value
        == "INSUFFICIENT_CONFIDENCE"
    )


def test_policy_results_are_explicit() -> None:
    """Authorization/policy outcomes should remain explicit enum values."""
    assert PolicyResult.NOT_EVALUATED.value == "NOT_EVALUATED"
    assert PolicyResult.ALLOWED.value == "ALLOWED"
    assert PolicyResult.DENIED.value == "DENIED"
    assert PolicyResult.REQUIRES_APPROVAL.value == "REQUIRES_APPROVAL"
