"""Aegis authorization policy evaluation for Lyrion."""

from datetime import UTC, datetime

from lyrion.capabilities.contracts import (
    AuthorizationDecision,
    AuthorizationResult,
    CapabilityRequest,
)
from lyrion.security.rules import AegisPolicy, AegisRuleEvaluator


class AegisPolicyEvaluator:
    """Deterministic Aegis authorization evaluator.

    Aegis evaluates a capability request against explicit policy rules.
    This component does not execute capabilities.
    """

    def __init__(self, policy: AegisPolicy) -> None:
        """Initialize the evaluator with an immutable policy."""
        self._policy = policy
        self._rule_evaluator = AegisRuleEvaluator()

    @property
    def policy(self) -> AegisPolicy:
        """Return the active immutable policy."""
        return self._policy

    def evaluate(
        self,
        request: CapabilityRequest,
        *,
        now: datetime | None = None,
    ) -> AuthorizationResult:
        """Evaluate a capability request against Aegis policy."""

        current_time = now or datetime.now(UTC)

        if current_time.tzinfo is None or current_time.utcoffset() is None:
            raise ValueError("now must be timezone-aware")

        if request.is_expired(current_time):
            return self._result(
                request,
                decision=AuthorizationDecision.EXPIRED,
                granted=False,
                reason="Capability request has expired.",
                evaluated_at=current_time,
                expires_at=None,
            )

        if request.authorization_decision is AuthorizationDecision.REVOKED:
            return self._result(
                request,
                decision=AuthorizationDecision.REVOKED,
                granted=False,
                reason="Capability request has been revoked.",
                evaluated_at=current_time,
                expires_at=None,
            )

        policy_evaluation = self._rule_evaluator.evaluate(
            request,
            self._policy,
        )

        if not policy_evaluation.allowed:
            reason = self._format_policy_denial(policy_evaluation)

            return self._result(
                request,
                decision=AuthorizationDecision.DENIED,
                granted=False,
                reason=reason,
                evaluated_at=current_time,
                expires_at=None,
            )

        if policy_evaluation.requires_human_approval:
            return self._result(
                request,
                decision=AuthorizationDecision.REQUIRES_APPROVAL,
                granted=False,
                reason=(
                    "Capability request matches policy but requires "
                    "human approval."
                ),
                evaluated_at=current_time,
                expires_at=request.expires_at,
            )

        return self._result(
            request,
            decision=AuthorizationDecision.ALLOWED,
            granted=True,
            reason="Capability request satisfied Aegis policy.",
            evaluated_at=current_time,
            expires_at=request.expires_at,
        )

    @staticmethod
    def _format_policy_denial(
        evaluation: object,
    ) -> str:
        """Create a stable human-readable policy denial reason."""
        violations = getattr(evaluation, "violations", ())
        if not violations:
            return "Capability request denied by Aegis policy."

        codes = ", ".join(violation.code for violation in violations)

        return f"Capability request denied by Aegis policy: {codes}."

    @staticmethod
    def _result(
        request: CapabilityRequest,
        *,
        decision: AuthorizationDecision,
        granted: bool,
        reason: str,
        evaluated_at: datetime,
        expires_at: datetime | None,
    ) -> AuthorizationResult:
        """Build a validated authorization result."""

        return AuthorizationResult(
            request_id=request.request_id,
            decision=decision,
            granted=granted,
            principal_id=request.principal_id,
            capability_id=request.capability_id,
            target_scope=request.target_scope,
            policy_version=request.policy_version,
            reason=reason,
            evaluated_at=evaluated_at.astimezone(UTC),
            expires_at=expires_at,
        )
