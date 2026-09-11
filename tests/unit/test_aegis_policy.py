"""Adversarial unit tests for the Lyrion Aegis policy evaluator."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lyrion.capabilities.contracts import (
    AuthorizationDecision,
    CapabilityOperation,
    CapabilityRequest,
)
from lyrion.core.types import (
    AutonomyLevel,
    DecisionId,
    IdempotencyKey,
    RiskLevel,
    TaskId,
)
from lyrion.events.models import EventSensitivity
from lyrion.security.policy import AegisPolicyEvaluator
from lyrion.security.rules import default_aegis_policy


def make_request(**overrides: object) -> CapabilityRequest:
    """Create a valid baseline capability request."""
    now = datetime.now(UTC)

    values: dict[str, object] = {
        "request_id": "capreq_aegis_test_001",
        "decision_id": DecisionId("decision_aegis_test_001"),
        "task_id": TaskId("task_aegis_test_001"),
        "principal_id": "lyrion-piae",
        "capability_id": "development.prepare",
        "target_scope": "lyrion/project",
        "operation": CapabilityOperation.READ,
        "data_classification": EventSensitivity.INTERNAL,
        "autonomy_level": AutonomyLevel.L1,
        "risk_level": RiskLevel.LOW,
        "policy_version": "aegis-policy-v1",
        "correlation_id": None,
        "idempotency_key": IdempotencyKey("idem_aegis_test_001"),
        "requested_at": now,
        "expires_at": now + timedelta(minutes=5),
        "justification": "Aegis policy evaluator test.",
        "authorization_decision": AuthorizationDecision.NOT_EVALUATED,
        "authorization_granted": False,
    }

    values.update(overrides)
    return CapabilityRequest(**values)


@pytest.fixture
def evaluator() -> AegisPolicyEvaluator:
    """Provide a fresh Aegis policy evaluator."""
    return AegisPolicyEvaluator(default_aegis_policy())


def test_low_risk_request_is_allowed(
    evaluator: AegisPolicyEvaluator,
) -> None:
    """A valid low-risk request should be allowed."""
    request = make_request(risk_level=RiskLevel.LOW)

    result = evaluator.evaluate(request, now=request.requested_at)

    assert result.decision is AuthorizationDecision.ALLOWED
    assert result.granted is True


def test_medium_risk_request_is_denied_by_capability_policy(
    evaluator: AegisPolicyEvaluator,
) -> None:
    """Medium-risk requests exceed the capability risk policy."""
    request = make_request(risk_level=RiskLevel.MEDIUM)

    result = evaluator.evaluate(request, now=request.requested_at)

    assert result.decision is AuthorizationDecision.DENIED
    assert result.granted is False
    assert "RISK_EXCEEDED" in result.reason


def test_high_risk_is_denied_by_capability_policy(
    evaluator: AegisPolicyEvaluator,
) -> None:
    """High-risk requests exceed the default capability risk policy."""
    request = make_request(risk_level=RiskLevel.HIGH)

    result = evaluator.evaluate(request, now=request.requested_at)

    assert result.decision is AuthorizationDecision.DENIED
    assert result.granted is False
    assert 'RISK_EXCEEDED' in result.reason


def test_critical_risk_is_denied_by_capability_policy(
    evaluator: AegisPolicyEvaluator,
) -> None:
    """Critical-risk requests exceed the default capability risk policy."""
    request = make_request(risk_level=RiskLevel.CRITICAL)

    result = evaluator.evaluate(request, now=request.requested_at)

    assert result.decision is AuthorizationDecision.DENIED
    assert result.granted is False
    assert 'RISK_EXCEEDED' in result.reason


def test_expired_request_is_not_authorized(
    evaluator: AegisPolicyEvaluator,
) -> None:
    """Expired requests must produce no authorization grant."""
    requested = datetime.now(UTC)

    request = make_request(
        requested_at=requested - timedelta(minutes=10),
        expires_at=requested - timedelta(seconds=1),
    )

    result = evaluator.evaluate(request, now=requested)

    assert result.decision is AuthorizationDecision.EXPIRED
    assert result.granted is False
    assert result.expires_at is None


def test_revoked_request_is_not_authorized(
    evaluator: AegisPolicyEvaluator,
) -> None:
    """Revoked requests must remain non-executable."""
    request = make_request(
        authorization_decision=AuthorizationDecision.REVOKED,
        authorization_granted=False,
    )

    result = evaluator.evaluate(request, now=request.requested_at)

    assert result.decision is AuthorizationDecision.REVOKED
    assert result.granted is False
    assert result.expires_at is None


def test_missing_principal_is_rejected_by_request_contract() -> None:
    """An empty principal identifier must be rejected before evaluation."""
    with pytest.raises(ValidationError):
        make_request(principal_id="")


def test_missing_capability_is_rejected_by_request_contract() -> None:
    """An empty capability identifier must be rejected."""
    with pytest.raises(ValidationError):
        make_request(capability_id="")


def test_missing_target_scope_is_rejected_by_request_contract() -> None:
    """An empty target scope must be rejected."""
    with pytest.raises(ValidationError):
        make_request(target_scope="")


def test_naive_evaluation_time_is_rejected(
    evaluator: AegisPolicyEvaluator,
) -> None:
    """Evaluation time must be timezone-aware."""
    request = make_request()

    with pytest.raises(ValueError):
        evaluator.evaluate(
            request,
            now=datetime.now(),
        )


def test_result_preserves_identity_binding(
    evaluator: AegisPolicyEvaluator,
) -> None:
    """Authorization results preserve request identity dimensions."""
    request = make_request(
        principal_id="principal-001",
        capability_id="capability-001",
        target_scope="resource-001",
    )

    result = evaluator.evaluate(request, now=request.requested_at)

    assert result.request_id == request.request_id
    assert result.principal_id == request.principal_id
    assert result.capability_id == request.capability_id
    assert result.target_scope == request.target_scope


def test_result_preserves_policy_version(
    evaluator: AegisPolicyEvaluator,
) -> None:
    """Authorization results identify the evaluated policy version."""
    request = make_request(policy_version="aegis-policy-v17")

    result = evaluator.evaluate(request, now=request.requested_at)

    assert result.policy_version == "aegis-policy-v17"


def test_allowed_result_preserves_expiry(
    evaluator: AegisPolicyEvaluator,
) -> None:
    """Valid authorization retains the request expiry."""
    request = make_request()

    result = evaluator.evaluate(request, now=request.requested_at)

    assert result.decision is AuthorizationDecision.ALLOWED
    assert result.granted is True
    assert result.expires_at == request.expires_at


def test_high_risk_result_never_grants(
    evaluator: AegisPolicyEvaluator,
) -> None:
    """Approval-required requests never become grants."""
    request = make_request(risk_level=RiskLevel.HIGH)

    result = evaluator.evaluate(request, now=request.requested_at)

    assert result.granted is False


def test_re_evaluation_does_not_mutate_request(
    evaluator: AegisPolicyEvaluator,
) -> None:
    """Policy evaluation must not mutate the immutable request."""
    request = make_request()

    before = request.model_dump(mode="json")
    evaluator.evaluate(request, now=request.requested_at)
    after = request.model_dump(mode="json")

    assert before == after


def test_authorization_decision_remains_explicit(
    evaluator: AegisPolicyEvaluator,
) -> None:
    """Authorization results must use explicit decision values."""
    request = make_request()

    result = evaluator.evaluate(request, now=request.requested_at)

    assert result.decision in {
        AuthorizationDecision.ALLOWED,
        AuthorizationDecision.DENIED,
        AuthorizationDecision.REQUIRES_APPROVAL,
        AuthorizationDecision.EXPIRED,
        AuthorizationDecision.REVOKED,
    }


def test_self_grant_is_rejected_by_contract() -> None:
    """A capability request cannot manufacture its own authority."""
    with pytest.raises(ValidationError):
        make_request(
            authorization_decision=AuthorizationDecision.NOT_EVALUATED,
            authorization_granted=True,
        )
