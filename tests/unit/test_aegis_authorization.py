"""Adversarial tests for the final Aegis authorization boundary."""

from datetime import UTC, datetime, timedelta

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
from lyrion.security.authorization import AegisAuthorizationService
from lyrion.security.guards import AuthorizationGuard
from lyrion.security.policy import AegisPolicyEvaluator
from lyrion.security.replay import ReplayGuard
from lyrion.security.rules import (
    AegisPolicy,
    CapabilityRule,
    default_aegis_policy,
)


def make_request(**overrides: object) -> CapabilityRequest:
    """Create a valid baseline capability request."""
    now = datetime.now(UTC)

    values: dict[str, object] = {
        "request_id": "auth_test_request",
        "decision_id": DecisionId("auth_test_decision"),
        "task_id": TaskId("auth_test_task"),
        "principal_id": "lyrion-piae",
        "capability_id": "development.prepare",
        "target_scope": "lyrion/project/src",
        "operation": CapabilityOperation.READ,
        "data_classification": EventSensitivity.INTERNAL,
        "autonomy_level": AutonomyLevel.L1,
        "risk_level": RiskLevel.LOW,
        "policy_version": "aegis-policy-v1",
        "idempotency_key": IdempotencyKey("auth_test_idempotency"),
        "requested_at": now,
        "expires_at": now + timedelta(minutes=5),
        "justification": "Final Aegis authorization test.",
    }

    values.update(overrides)
    return CapabilityRequest(**values)


def make_service(
    *,
    policy: AegisPolicy | None = None,
    replay: ReplayGuard | None = None,
) -> AegisAuthorizationService:
    """Create the final Aegis authorization service."""
    active_policy = policy or default_aegis_policy()

    return AegisAuthorizationService(
        AegisPolicyEvaluator(active_policy),
        AuthorizationGuard(active_policy.policy_version),
        replay or ReplayGuard(),
    )


def test_allowed_request_passes_final_boundary() -> None:
    """A valid request should receive authorization."""
    request = make_request()

    result = make_service().authorize(
        request,
        now=request.requested_at,
    )

    assert result.decision is AuthorizationDecision.ALLOWED
    assert result.granted is True


def test_denied_policy_request_remains_denied() -> None:
    """Policy denial must survive final authorization composition."""
    request = make_request(
        target_scope="protected/system",
    )

    result = make_service().authorize(
        request,
        now=request.requested_at,
    )

    assert result.decision is AuthorizationDecision.DENIED
    assert result.granted is False
    assert "TARGET_SCOPE_NOT_ALLOWED" in result.reason


def test_request_policy_version_must_match_active_policy() -> None:
    """Requests using an old policy version must fail closed."""
    request = make_request(
        policy_version="aegis-policy-v0",
    )

    result = make_service().authorize(
        request,
        now=request.requested_at,
    )

    assert result.decision is AuthorizationDecision.DENIED
    assert result.granted is False
    assert "active Aegis policy" in result.reason


def test_replay_is_rejected_by_final_boundary() -> None:
    """An already-authorized idempotency key cannot be reused."""
    request = make_request()

    service = make_service()

    first = service.authorize(
        request,
        now=request.requested_at,
    )
    second = service.authorize(
        request,
        now=request.requested_at,
    )

    assert first.decision is AuthorizationDecision.ALLOWED
    assert first.granted is True

    assert second.decision is AuthorizationDecision.DENIED
    assert second.granted is False
    assert "Replay detected" in second.reason


def test_different_request_with_new_key_is_independent() -> None:
    """Distinct requests should not share replay state."""
    first_request = make_request(
        request_id="request-001",
        decision_id=DecisionId("decision-001"),
        task_id=TaskId("task-001"),
        idempotency_key=IdempotencyKey("idem-001"),
    )
    second_request = make_request(
        request_id="request-002",
        decision_id=DecisionId("decision-002"),
        task_id=TaskId("task-002"),
        idempotency_key=IdempotencyKey("idem-002"),
    )

    service = make_service()

    first = service.authorize(
        first_request,
        now=first_request.requested_at,
    )
    second = service.authorize(
        second_request,
        now=second_request.requested_at,
    )

    assert first.granted is True
    assert second.granted is True


def test_expired_request_is_not_authorized() -> None:
    """Expired requests must never reach an executable authorization."""
    requested = datetime.now(UTC)

    request = make_request(
        requested_at=requested - timedelta(minutes=10),
        expires_at=requested - timedelta(seconds=1),
    )

    result = make_service().authorize(
        request,
        now=requested,
    )

    assert result.decision is AuthorizationDecision.EXPIRED
    assert result.granted is False


def test_revoked_request_is_not_authorized() -> None:
    """Revoked requests must remain non-executable."""
    request = make_request(
        authorization_decision=AuthorizationDecision.REVOKED,
        authorization_granted=False,
    )

    result = make_service().authorize(
        request,
        now=request.requested_at,
    )

    assert result.decision is AuthorizationDecision.REVOKED
    assert result.granted is False


def test_high_risk_policy_requires_approval() -> None:
    """Approval-required rules must not become automatic grants."""
    policy = AegisPolicy(
        policy_version="aegis-approval-v1",
        rules=(
            CapabilityRule(
                capability_id="approval.required",
                allowed_principals=frozenset({"lyrion-piae"}),
                allowed_operations=frozenset(
                    {CapabilityOperation.EXECUTE}
                ),
                target_prefixes=("protected",),
                max_autonomy_level=AutonomyLevel.L2,
                max_risk_level=RiskLevel.MEDIUM,
                max_data_classification=EventSensitivity.SENSITIVE,
                requires_human_approval=True,
            ),
        ),
    )

    request = make_request(
        capability_id="approval.required",
        target_scope="protected/resource",
        operation=CapabilityOperation.EXECUTE,
        autonomy_level=AutonomyLevel.L2,
        risk_level=RiskLevel.MEDIUM,
        data_classification=EventSensitivity.SENSITIVE,
        policy_version="aegis-approval-v1",
        idempotency_key=IdempotencyKey("idem-approval"),
    )

    result = make_service(
        policy=policy,
    ).authorize(
        request,
        now=request.requested_at,
    )

    assert result.decision is AuthorizationDecision.REQUIRES_APPROVAL
    assert result.granted is False


def test_approval_required_request_does_not_consume_replay_key() -> None:
    """Approval-required requests should remain retryable for approval."""
    policy = AegisPolicy(
        policy_version="aegis-approval-v1",
        rules=(
            CapabilityRule(
                capability_id="approval.required",
                allowed_principals=frozenset({"lyrion-piae"}),
                allowed_operations=frozenset(
                    {CapabilityOperation.EXECUTE}
                ),
                target_prefixes=("protected",),
                max_autonomy_level=AutonomyLevel.L2,
                max_risk_level=RiskLevel.MEDIUM,
                max_data_classification=EventSensitivity.SENSITIVE,
                requires_human_approval=True,
            ),
        ),
    )

    request = make_request(
        capability_id="approval.required",
        target_scope="protected/resource",
        operation=CapabilityOperation.EXECUTE,
        autonomy_level=AutonomyLevel.L2,
        risk_level=RiskLevel.MEDIUM,
        data_classification=EventSensitivity.SENSITIVE,
        policy_version="aegis-approval-v1",
        idempotency_key=IdempotencyKey("idem-approval-retry"),
    )

    replay = ReplayGuard()
    service = make_service(
        policy=policy,
        replay=replay,
    )

    first = service.authorize(
        request,
        now=request.requested_at,
    )
    second = service.authorize(
        request,
        now=request.requested_at,
    )

    assert first.decision is AuthorizationDecision.REQUIRES_APPROVAL
    assert second.decision is AuthorizationDecision.REQUIRES_APPROVAL
    assert replay.seen(str(request.idempotency_key)) is False


def test_final_boundary_is_fail_closed_for_wrong_principal() -> None:
    """A principal mismatch must never yield a grant."""
    request = make_request()

    authorization_guard = AuthorizationGuard("aegis-policy-v1")
    policy_evaluator = AegisPolicyEvaluator(default_aegis_policy())

    policy_result = policy_evaluator.evaluate(
        request,
        now=request.requested_at,
    )

    mismatched = policy_result.model_copy(
        update={
            "principal_id": "different-principal",
        }
    )

    assert authorization_guard.is_authorized(
        request,
        mismatched,
        now=request.requested_at,
    ) is False


def test_final_boundary_preserves_policy_identity() -> None:
    """Successful authorization must preserve the active policy version."""
    request = make_request()

    result = make_service().authorize(
        request,
        now=request.requested_at,
    )

    assert result.policy_version == "aegis-policy-v1"


def test_same_valid_input_is_authorized_once() -> None:
    """Identical valid requests are allowed once and replayed thereafter."""
    request = make_request(
        request_id="single_use_request",
        decision_id=DecisionId("single_use_decision"),
        task_id=TaskId("single_use_task"),
        idempotency_key=IdempotencyKey("single_use_key"),
    )

    service = make_service()

    first = service.authorize(
        request,
        now=request.requested_at,
    )
    second = service.authorize(
        request,
        now=request.requested_at,
    )

    assert first.granted is True
    assert second.granted is False
    assert second.decision is AuthorizationDecision.DENIED


def test_final_boundary_does_not_execute_capability() -> None:
    """Authorization must only produce a decision, never perform execution."""
    request = make_request()

    result = make_service().authorize(
        request,
        now=request.requested_at,
    )

    assert result.decision is AuthorizationDecision.ALLOWED
    assert result.granted is True
