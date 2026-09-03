"""Final Aegis authorization composition boundary."""

from datetime import UTC, datetime

from lyrion.capabilities.contracts import (
    AuthorizationDecision,
    AuthorizationResult,
    CapabilityRequest,
)
from lyrion.security.guards import AuthorizationGuard
from lyrion.security.policy import AegisPolicyEvaluator
from lyrion.security.replay import ReplayGuard


class AegisAuthorizationService:
    """Compose policy, authorization guards, and replay protection.

    This is the final authorization boundary consumed by downstream
    capability infrastructure. It never executes capabilities.
    """

    def __init__(
        self,
        policy_evaluator: AegisPolicyEvaluator,
        authorization_guard: AuthorizationGuard,
        replay_guard: ReplayGuard,
    ) -> None:
        """Initialize the composed Aegis authorization service."""
        self._policy_evaluator = policy_evaluator
        self._authorization_guard = authorization_guard
        self._replay_guard = replay_guard

    @property
    def policy_evaluator(self) -> AegisPolicyEvaluator:
        """Return the underlying policy evaluator."""
        return self._policy_evaluator

    @property
    def authorization_guard(self) -> AuthorizationGuard:
        """Return the authorization guard."""
        return self._authorization_guard

    @property
    def replay_guard(self) -> ReplayGuard:
        """Return the replay guard."""
        return self._replay_guard

    def authorize(
        self,
        request: CapabilityRequest,
        *,
        now: datetime | None = None,
    ) -> AuthorizationResult:
        """Return the final authorization decision for a request."""

        current_time = now or datetime.now(UTC)

        if current_time.tzinfo is None or current_time.utcoffset() is None:
            raise ValueError("now must be timezone-aware")

        active_policy_version = (
            self._policy_evaluator.policy.policy_version
        )

        if request.policy_version != active_policy_version:
            return self._denied_result(
                request,
                reason=(
                    "Request policy version does not match the active "
                    "Aegis policy."
                ),
                evaluated_at=current_time,
            )

        policy_result = self._policy_evaluator.evaluate(
            request,
            now=current_time,
        )

        if policy_result.decision is not AuthorizationDecision.ALLOWED:
            return policy_result

        if not self._authorization_guard.is_authorized(
            request,
            policy_result,
            now=current_time,
        ):
            reasons = self._authorization_guard.failure_reasons(
                request,
                policy_result,
                now=current_time,
            )

            return self._denied_result(
                request,
                reason=(
                    "Authorization guard rejected the policy decision: "
                    + ", ".join(reasons)
                ),
                evaluated_at=current_time,
            )

        if not self._replay_guard.check_and_record(
            str(request.idempotency_key),
            request.request_id,
        ):
            return self._denied_result(
                request,
                reason="Replay detected for idempotency key.",
                evaluated_at=current_time,
            )

        return policy_result

    @staticmethod
    def _denied_result(
        request: CapabilityRequest,
        *,
        reason: str,
        evaluated_at: datetime,
    ) -> AuthorizationResult:
        """Build a fail-closed denied authorization result."""

        return AuthorizationResult(
            request_id=request.request_id,
            decision=AuthorizationDecision.DENIED,
            granted=False,
            principal_id=request.principal_id,
            capability_id=request.capability_id,
            target_scope=request.target_scope,
            policy_version=request.policy_version,
            reason=reason,
            evaluated_at=evaluated_at.astimezone(UTC),
            expires_at=None,
        )
