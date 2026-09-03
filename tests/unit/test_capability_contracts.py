"""Security-focused unit tests for Lyrion capability contracts."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lyrion.capabilities.contracts import (
    AuthorizationDecision,
    AuthorizationResult,
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


def make_request(**overrides: object) -> CapabilityRequest:
    """Create a valid baseline capability request."""
    now = datetime.now(UTC)

    values: dict[str, object] = {
        "request_id": "capreq_test_001",
        "decision_id": DecisionId("decision_test_001"),
        "task_id": TaskId("task_test_001"),
        "principal_id": "lyrion-piae",
        "capability_id": "development.prepare",
        "target_scope": "lyrion/project",
        "operation": CapabilityOperation.READ,
        "data_classification": EventSensitivity.INTERNAL,
        "autonomy_level": AutonomyLevel.L1,
        "risk_level": RiskLevel.LOW,
        "policy_version": "aegis-policy-v1",
        "correlation_id": None,
        "idempotency_key": IdempotencyKey("idem_capreq_001"),
        "requested_at": now,
        "expires_at": now + timedelta(minutes=5),
        "justification": "Bounded capability request for testing.",
        "authorization_decision": AuthorizationDecision.NOT_EVALUATED,
        "authorization_granted": False,
    }

    values.update(overrides)
    return CapabilityRequest(**values)


def make_authorization_result(**overrides: object) -> AuthorizationResult:
    """Create a valid baseline authorization result."""
    now = datetime.now(UTC)

    values: dict[str, object] = {
        "request_id": "capreq_test_001",
        "decision": AuthorizationDecision.ALLOWED,
        "granted": True,
        "principal_id": "lyrion-piae",
        "capability_id": "development.prepare",
        "target_scope": "lyrion/project",
        "policy_version": "aegis-policy-v1",
        "reason": "Request allowed by policy.",
        "evaluated_at": now,
        "expires_at": now + timedelta(minutes=5),
    }

    values.update(overrides)
    return AuthorizationResult(**values)


def test_capability_request_creation() -> None:
    """A valid capability request should be accepted."""
    request = make_request()

    assert request.request_id == "capreq_test_001"
    assert request.capability_id == "development.prepare"
    assert request.authorization_decision is AuthorizationDecision.NOT_EVALUATED
    assert request.authorization_granted is False


def test_capability_request_is_immutable() -> None:
    """Capability requests must not be mutable."""
    request = make_request()

    with pytest.raises(ValidationError):
        request.target_scope = "changed"


def test_capability_request_rejects_unknown_fields() -> None:
    """Undeclared request fields must be rejected."""
    with pytest.raises(ValidationError):
        make_request(unknown_field="not-allowed")


def test_capability_request_requires_aware_timestamps() -> None:
    """Request timestamps must be timezone-aware."""
    with pytest.raises(ValidationError):
        make_request(requested_at=datetime.now())


def test_capability_request_rejects_invalid_expiry() -> None:
    """Request expiry cannot precede request creation."""
    requested = datetime.now(UTC)

    with pytest.raises(ValidationError):
        make_request(
            requested_at=requested,
            expires_at=requested - timedelta(seconds=1),
        )


def test_capability_request_expiry_behavior() -> None:
    """Capability request expiry should be detectable."""
    requested = datetime.now(UTC)

    request = make_request(
        requested_at=requested,
        expires_at=requested + timedelta(seconds=1),
    )

    assert request.is_expired(requested) is False
    assert request.is_expired(requested + timedelta(seconds=2)) is True


def test_capability_request_prevents_self_grant() -> None:
    """PIAE must not be able to self-grant authority."""
    with pytest.raises(ValidationError):
        make_request(
            authorization_decision=AuthorizationDecision.NOT_EVALUATED,
            authorization_granted=True,
        )


def test_capability_request_requires_allowed_for_grant() -> None:
    """A granted request must have an ALLOWED authorization decision."""
    with pytest.raises(ValidationError):
        make_request(
            authorization_decision=AuthorizationDecision.DENIED,
            authorization_granted=True,
        )


def test_authorization_result_creation() -> None:
    """A valid allowed authorization result should be accepted."""
    result = make_authorization_result()

    assert result.decision is AuthorizationDecision.ALLOWED
    assert result.granted is True
    assert result.policy_version == "aegis-policy-v1"


def test_authorization_result_is_immutable() -> None:
    """Authorization results must not be mutable."""
    result = make_authorization_result()

    with pytest.raises(ValidationError):
        result.reason = "changed"


def test_authorization_result_rejects_unknown_fields() -> None:
    """Undeclared authorization fields must be rejected."""
    with pytest.raises(ValidationError):
        make_authorization_result(unknown_field="not-allowed")


def test_denied_authorization_cannot_be_granted() -> None:
    """DENIED authorization must never carry a grant."""
    with pytest.raises(ValidationError):
        make_authorization_result(
            decision=AuthorizationDecision.DENIED,
            granted=True,
        )


def test_allowed_authorization_must_be_granted() -> None:
    """ALLOWED authorization must explicitly carry the grant."""
    with pytest.raises(ValidationError):
        make_authorization_result(
            decision=AuthorizationDecision.ALLOWED,
            granted=False,
        )


def test_authorization_result_requires_aware_timestamps() -> None:
    """Authorization timestamps must be timezone-aware."""
    with pytest.raises(ValidationError):
        make_authorization_result(evaluated_at=datetime.now())


def test_authorization_result_rejects_invalid_expiry() -> None:
    """Authorization expiry cannot precede evaluation."""
    evaluated = datetime.now(UTC)

    with pytest.raises(ValidationError):
        make_authorization_result(
            evaluated_at=evaluated,
            expires_at=evaluated - timedelta(seconds=1),
        )


def test_authorization_result_rejects_negative_boundary_data() -> None:
    """Boundary identifiers cannot be empty."""
    with pytest.raises(ValidationError):
        make_request(principal_id="")

    with pytest.raises(ValidationError):
        make_request(capability_id="")

    with pytest.raises(ValidationError):
        make_request(target_scope="")


def test_request_supports_all_declared_operations() -> None:
    """Capability operation values should remain explicit."""
    assert CapabilityOperation.READ.value == "READ"
    assert CapabilityOperation.WRITE.value == "WRITE"
    assert CapabilityOperation.CREATE.value == "CREATE"
    assert CapabilityOperation.UPDATE.value == "UPDATE"
    assert CapabilityOperation.DELETE.value == "DELETE"
    assert CapabilityOperation.EXECUTE.value == "EXECUTE"
    assert CapabilityOperation.SEND.value == "SEND"
    assert CapabilityOperation.TRANSFORM.value == "TRANSFORM"


def test_authorization_decisions_are_explicit() -> None:
    """Authorization outcomes should remain explicit."""
    assert AuthorizationDecision.NOT_EVALUATED.value == "NOT_EVALUATED"
    assert AuthorizationDecision.ALLOWED.value == "ALLOWED"
    assert AuthorizationDecision.DENIED.value == "DENIED"
    assert (
        AuthorizationDecision.REQUIRES_APPROVAL.value
        == "REQUIRES_APPROVAL"
    )
    assert AuthorizationDecision.EXPIRED.value == "EXPIRED"
    assert AuthorizationDecision.REVOKED.value == "REVOKED"
