"""Adversarial unit tests for the Aegis authorization guard."""

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
from lyrion.security.guards import AuthorizationGuard


def make_request(**overrides: object) -> CapabilityRequest:
    """Create a valid baseline capability request."""
    now = datetime.now(UTC)

    values: dict[str, object] = {
        "request_id": "guard_test_request",
        "decision_id": DecisionId("guard_test_decision"),
        "task_id": TaskId("guard_test_task"),
        "principal_id": "lyrion-piae",
        "capability_id": "development.prepare",
        "target_scope": "lyrion/project/src",
        "operation": CapabilityOperation.READ,
        "data_classification": EventSensitivity.INTERNAL,
        "autonomy_level": AutonomyLevel.L1,
        "risk_level": RiskLevel.LOW,
        "policy_version": "aegis-policy-v1",
        "idempotency_key": IdempotencyKey("guard_test_idempotency"),
        "requested_at": now,
        "expires_at": now + timedelta(minutes=5),
        "justification": "Authorization guard test.",
    }

    values.update(overrides)
    return CapabilityRequest(**values)


def make_authorization(
    request: CapabilityRequest,
    **overrides: object,
) -> AuthorizationResult:
    """Create a valid baseline authorization result."""
    now = datetime.now(UTC)

    values: dict[str, object] = {
        "request_id": request.request_id,
        "decision": AuthorizationDecision.ALLOWED,
        "granted": True,
        "principal_id": request.principal_id,
        "capability_id": request.capability_id,
        "target_scope": request.target_scope,
        "policy_version": request.policy_version,
        "reason": "Allowed.",
        "evaluated_at": now,
        "expires_at": request.expires_at,
    }

    values.update(overrides)
    return AuthorizationResult(**values)


def test_valid_authorization_is_usable() -> None:
    """A matching current authorization should be usable."""
    request = make_request()
    authorization = make_authorization(request)

    guard = AuthorizationGuard("aegis-policy-v1")

    assert guard.is_authorized(
        request,
        authorization,
        now=request.requested_at,
    )


def test_guard_requires_non_empty_policy_version() -> None:
    """The guard must reject an empty active policy version."""
    with pytest.raises(ValueError):
        AuthorizationGuard("")


def test_request_id_mismatch_is_rejected() -> None:
    """Authorization must be bound to the exact request."""
    request = make_request()
    authorization = make_authorization(
        request,
        request_id="different-request",
    )

    guard = AuthorizationGuard("aegis-policy-v1")

    reasons = guard.failure_reasons(
        request,
        authorization,
        now=request.requested_at,
    )

    assert "REQUEST_ID_MISMATCH" in reasons
    assert guard.is_authorized(
        request,
        authorization,
        now=request.requested_at,
    ) is False


def test_principal_mismatch_is_rejected() -> None:
    """Authorization must be bound to the requesting principal."""
    request = make_request()
    authorization = make_authorization(
        request,
        principal_id="different-principal",
    )

    guard = AuthorizationGuard("aegis-policy-v1")

    assert "PRINCIPAL_MISMATCH" in guard.failure_reasons(
        request,
        authorization,
        now=request.requested_at,
    )


def test_capability_mismatch_is_rejected() -> None:
    """Authorization must be bound to the requested capability."""
    request = make_request()
    authorization = make_authorization(
        request,
        capability_id="different.capability",
    )

    guard = AuthorizationGuard("aegis-policy-v1")

    assert "CAPABILITY_MISMATCH" in guard.failure_reasons(
        request,
        authorization,
        now=request.requested_at,
    )


def test_target_scope_mismatch_is_rejected() -> None:
    """Authorization must be bound to the exact target scope."""
    request = make_request()
    authorization = make_authorization(
        request,
        target_scope="lyrion/project/other",
    )

    guard = AuthorizationGuard("aegis-policy-v1")

    assert "TARGET_SCOPE_MISMATCH" in guard.failure_reasons(
        request,
        authorization,
        now=request.requested_at,
    )


def test_policy_version_mismatch_is_rejected() -> None:
    """Authorization from an old active policy must not remain usable."""
    request = make_request()
    authorization = make_authorization(
        request,
        policy_version="aegis-policy-v0",
    )

    guard = AuthorizationGuard("aegis-policy-v1")

    reasons = guard.failure_reasons(
        request,
        authorization,
        now=request.requested_at,
    )

    assert "POLICY_VERSION_MISMATCH" in reasons
    assert guard.is_authorized(
        request,
        authorization,
        now=request.requested_at,
    ) is False


def test_request_authorization_policy_versions_must_match() -> None:
    """Request and authorization must use the same policy version."""
    request = make_request(
        policy_version="aegis-policy-v1",
    )
    authorization = make_authorization(
        request,
        policy_version="aegis-policy-v0",
    )

    guard = AuthorizationGuard("aegis-policy-v1")

    reasons = guard.failure_reasons(
        request,
        authorization,
        now=request.requested_at,
    )

    assert "REQUEST_POLICY_VERSION_MISMATCH" in reasons
    assert guard.is_authorized(
        request,
        authorization,
        now=request.requested_at,
    ) is False


def test_matching_policy_versions_are_accepted() -> None:
    """Request, authorization, and active policy versions must agree."""
    request = make_request(
        policy_version="aegis-policy-v7",
    )
    authorization = make_authorization(
        request,
        policy_version="aegis-policy-v7",
    )

    guard = AuthorizationGuard("aegis-policy-v7")

    reasons = guard.failure_reasons(
        request,
        authorization,
        now=request.requested_at,
    )

    assert "POLICY_VERSION_MISMATCH" not in reasons
    assert "REQUEST_POLICY_VERSION_MISMATCH" not in reasons
    assert guard.is_authorized(
        request,
        authorization,
        now=request.requested_at,
    )


def test_expired_request_is_rejected() -> None:
    """An expired capability request must not remain executable."""
    requested = datetime.now(UTC)
    request_expiry = requested + timedelta(seconds=1)

    request = make_request(
        requested_at=requested,
        expires_at=request_expiry,
    )

    authorization = make_authorization(
        request,
        evaluated_at=requested,
        expires_at=request_expiry,
    )

    guard = AuthorizationGuard("aegis-policy-v1")

    future = requested + timedelta(seconds=2)

    reasons = guard.failure_reasons(
        request,
        authorization,
        now=future,
    )

    assert "REQUEST_EXPIRED" in reasons
    assert "AUTHORIZATION_EXPIRED" in reasons
    assert guard.is_authorized(
        request,
        authorization,
        now=future,
    ) is False


def test_expired_authorization_is_rejected() -> None:
    """An expired authorization result must not remain usable."""
    requested = datetime.now(UTC)
    expiry = requested + timedelta(seconds=1)

    request = make_request(
        requested_at=requested,
        expires_at=expiry,
    )
    authorization = make_authorization(
        request,
        evaluated_at=requested,
        expires_at=expiry,
    )

    guard = AuthorizationGuard("aegis-policy-v1")

    future = requested + timedelta(seconds=2)

    assert "AUTHORIZATION_EXPIRED" in guard.failure_reasons(
        request,
        authorization,
        now=future,
    )
    assert guard.is_authorized(
        request,
        authorization,
        now=future,
    ) is False


def test_expired_decision_is_rejected() -> None:
    """An EXPIRED authorization decision must not be usable."""
    request = make_request()
    authorization = make_authorization(
        request,
        decision=AuthorizationDecision.EXPIRED,
        granted=False,
        expires_at=None,
    )

    guard = AuthorizationGuard("aegis-policy-v1")

    reasons = guard.failure_reasons(
        request,
        authorization,
        now=request.requested_at,
    )

    assert "AUTHORIZATION_EXPIRED" in reasons
    assert "AUTHORIZATION_NOT_ALLOWED" in reasons
    assert "AUTHORIZATION_NOT_GRANTED" in reasons


def test_revoked_decision_is_rejected() -> None:
    """A REVOKED authorization decision must not be usable."""
    request = make_request()
    authorization = make_authorization(
        request,
        decision=AuthorizationDecision.REVOKED,
        granted=False,
        expires_at=None,
    )

    guard = AuthorizationGuard("aegis-policy-v1")

    reasons = guard.failure_reasons(
        request,
        authorization,
        now=request.requested_at,
    )

    assert "AUTHORIZATION_REVOKED" in reasons
    assert "AUTHORIZATION_NOT_ALLOWED" in reasons
    assert "AUTHORIZATION_NOT_GRANTED" in reasons


def test_denied_decision_is_rejected() -> None:
    """A denied authorization decision must not be usable."""
    request = make_request()
    authorization = make_authorization(
        request,
        decision=AuthorizationDecision.DENIED,
        granted=False,
        expires_at=None,
    )

    guard = AuthorizationGuard("aegis-policy-v1")

    assert guard.is_authorized(
        request,
        authorization,
        now=request.requested_at,
    ) is False


def test_ungranted_allowed_result_is_rejected() -> None:
    """An ALLOWED result without a grant must be rejected by its contract."""
    request = make_request()

    with pytest.raises(ValidationError):
        make_authorization(
            request,
            decision=AuthorizationDecision.ALLOWED,
            granted=False,
        )


def test_authorization_expiry_cannot_exceed_request_expiry() -> None:
    """Authorization cannot outlive the request authority window."""
    request = make_request()
    authorization = make_authorization(
        request,
        expires_at=request.expires_at + timedelta(minutes=1),
    )

    guard = AuthorizationGuard("aegis-policy-v1")

    reasons = guard.failure_reasons(
        request,
        authorization,
        now=request.requested_at,
    )

    assert "AUTHORIZATION_EXPIRY_EXCEEDS_REQUEST" in reasons
    assert guard.is_authorized(
        request,
        authorization,
        now=request.requested_at,
    ) is False


def test_naive_clock_is_rejected() -> None:
    """The guard clock must be timezone-aware."""
    request = make_request()
    authorization = make_authorization(request)

    guard = AuthorizationGuard("aegis-policy-v1")

    with pytest.raises(ValueError):
        guard.is_authorized(
            request,
            authorization,
            now=datetime.now(),
        )


def test_require_authorized_raises_on_denial() -> None:
    """Denied authorization must raise at the enforcement boundary."""
    request = make_request()
    authorization = make_authorization(
        request,
        decision=AuthorizationDecision.DENIED,
        granted=False,
        expires_at=None,
    )

    guard = AuthorizationGuard("aegis-policy-v1")

    with pytest.raises(PermissionError, match="authorization rejected"):
        guard.require_authorized(
            request,
            authorization,
            now=request.requested_at,
        )


def test_failure_reasons_are_deterministic() -> None:
    """Equal inputs must produce the same ordered failure reasons."""
    request = make_request()
    authorization = make_authorization(
        request,
        request_id="wrong-request",
        principal_id="wrong-principal",
        capability_id="wrong.capability",
        target_scope="wrong-scope",
        policy_version="aegis-policy-v0",
        decision=AuthorizationDecision.DENIED,
        granted=False,
        expires_at=None,
    )

    guard = AuthorizationGuard("aegis-policy-v1")

    first = guard.failure_reasons(
        request,
        authorization,
        now=request.requested_at,
    )
    second = guard.failure_reasons(
        request,
        authorization,
        now=request.requested_at,
    )

    assert first == second


def test_guard_never_turns_denial_into_authorization() -> None:
    """The guard only rejects or permits; it never creates a grant."""
    request = make_request()
    authorization = make_authorization(
        request,
        decision=AuthorizationDecision.REQUIRES_APPROVAL,
        granted=False,
    )

    guard = AuthorizationGuard("aegis-policy-v1")

    assert guard.is_authorized(
        request,
        authorization,
        now=request.requested_at,
    ) is False


def test_matching_policy_version_is_exposed() -> None:
    """The active policy version should be inspectable."""
    guard = AuthorizationGuard("aegis-policy-v42")

    assert guard.expected_policy_version == "aegis-policy-v42"
