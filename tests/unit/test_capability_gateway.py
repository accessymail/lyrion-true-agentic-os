"""Tests for the authorization-enforcing Capability Gateway."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lyrion.capabilities.contracts import (
    AuthorizationDecision,
    CapabilityOperation,
    CapabilityRequest,
)
from lyrion.capabilities.gateway import CapabilityGateway
from lyrion.core.types import (
    AutonomyLevel,
    DecisionId,
    IdempotencyKey,
    RiskLevel,
    TaskId,
)
from lyrion.events.models import EventSensitivity
from lyrion.security.authorization import AegisAuthorizationService
from lyrion.security.guards import AuthorizationGuard
from lyrion.security.policy import AegisPolicyEvaluator
from lyrion.security.replay import ReplayGuard
from lyrion.security.rules import default_aegis_policy


def make_request(**overrides: object) -> CapabilityRequest:
    """Create a valid gateway test request."""
    now = datetime.now(UTC)

    values: dict[str, object] = {
        "request_id": "gateway_test_request",
        "decision_id": DecisionId("gateway_test_decision"),
        "task_id": TaskId("gateway_test_task"),
        "principal_id": "lyrion-piae",
        "capability_id": "development.prepare",
        "target_scope": "lyrion/project/src",
        "operation": CapabilityOperation.READ,
        "data_classification": EventSensitivity.INTERNAL,
        "autonomy_level": AutonomyLevel.L1,
        "risk_level": RiskLevel.LOW,
        "policy_version": "aegis-policy-v1",
        "idempotency_key": IdempotencyKey("gateway_test_idempotency"),
        "requested_at": now,
        "expires_at": now + timedelta(minutes=5),
        "justification": "Capability gateway test.",
    }

    values.update(overrides)

    return CapabilityRequest(**values)


def make_gateway(
    *,
    replay: ReplayGuard | None = None,
) -> CapabilityGateway:
    """Create a gateway backed by the default Aegis policy."""
    policy = default_aegis_policy()

    return CapabilityGateway(
        AegisAuthorizationService(
            AegisPolicyEvaluator(policy),
            AuthorizationGuard(policy.policy_version),
            replay or ReplayGuard(),
        )
    )


def test_allowed_request_is_admitted() -> None:
    """A valid authorized request should be admitted."""
    request = make_request()

    admission = make_gateway().admit(
        request,
        now=request.requested_at,
    )

    assert admission.admitted is True
    assert admission.authorization_decision is AuthorizationDecision.ALLOWED


def test_denied_request_is_not_admitted() -> None:
    """A policy-denied request must not be admitted."""
    request = make_request(
        target_scope="protected/system",
    )

    admission = make_gateway().admit(
        request,
        now=request.requested_at,
    )

    assert admission.admitted is False
    assert admission.authorization_decision is AuthorizationDecision.DENIED
    assert "TARGET_SCOPE_NOT_ALLOWED" in admission.authorization_reason


def test_unknown_capability_is_not_admitted() -> None:
    """Unknown capabilities must fail closed."""
    request = make_request(
        capability_id="unknown.capability",
    )

    admission = make_gateway().admit(
        request,
        now=request.requested_at,
    )

    assert admission.admitted is False
    assert admission.authorization_decision is AuthorizationDecision.DENIED


def test_policy_version_mismatch_is_not_admitted() -> None:
    """Requests using a stale policy must not be admitted."""
    request = make_request(
        policy_version="aegis-policy-v0",
    )

    admission = make_gateway().admit(
        request,
        now=request.requested_at,
    )

    assert admission.admitted is False
    assert admission.authorization_decision is AuthorizationDecision.DENIED


def test_expired_request_is_not_admitted() -> None:
    """Expired requests must never be admitted."""
    now = datetime.now(UTC)

    request = make_request(
        requested_at=now - timedelta(minutes=5),
        expires_at=now - timedelta(seconds=1),
    )

    admission = make_gateway().admit(
        request,
        now=now,
    )

    assert admission.admitted is False
    assert admission.authorization_decision is AuthorizationDecision.EXPIRED


def test_replay_is_not_admitted_twice() -> None:
    """An idempotent request may only be admitted once."""
    request = make_request()

    replay = ReplayGuard()
    gateway = make_gateway(replay=replay)

    first = gateway.admit(
        request,
        now=request.requested_at,
    )
    second = gateway.admit(
        request,
        now=request.requested_at,
    )

    assert first.admitted is True
    assert second.admitted is False
    assert second.authorization_decision is AuthorizationDecision.DENIED
    assert "Replay detected" in second.authorization_reason


def test_require_admission_raises_for_denied_request() -> None:
    """Denied requests must raise at the gateway boundary."""
    request = make_request(
        target_scope="protected/system",
    )

    with pytest.raises(PermissionError):
        make_gateway().require_admission(
            request,
            now=request.requested_at,
        )


def test_admission_preserves_request_identity() -> None:
    """Admission preserves request identity dimensions."""
    request = make_request(
        request_id="identity-request",
    )

    admission = make_gateway().admit(
        request,
        now=request.requested_at,
    )

    assert admission.request_id == request.request_id
    assert admission.capability_id == request.capability_id
    assert admission.target_scope == request.target_scope


def test_admission_preserves_policy_version() -> None:
    """Admission preserves the evaluated policy version."""
    request = make_request()

    admission = make_gateway().admit(
        request,
        now=request.requested_at,
    )

    assert admission.policy_version == "aegis-policy-v1"


def test_naive_gateway_time_is_rejected() -> None:
    """Gateway evaluation time must be timezone-aware."""
    request = make_request()

    with pytest.raises(ValueError):
        make_gateway().admit(
            request,
            now=datetime.now(),
        )


def test_admission_is_immutable() -> None:
    """Execution admissions must be immutable."""
    request = make_request()

    admission = make_gateway().admit(
        request,
        now=request.requested_at,
    )

    with pytest.raises(ValidationError):
        admission.admitted = False


def test_gateway_does_not_execute() -> None:
    """The gateway only creates admission metadata."""
    request = make_request()

    admission = make_gateway().admit(
        request,
        now=request.requested_at,
    )

    assert admission.admitted is True
    assert admission.authorization_decision is AuthorizationDecision.ALLOWED
