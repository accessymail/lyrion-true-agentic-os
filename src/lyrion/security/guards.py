"""Security guards for validating Aegis authorization results."""

from datetime import UTC, datetime

from lyrion.capabilities.contracts import (
    AuthorizationDecision,
    AuthorizationResult,
    CapabilityRequest,
)


class AuthorizationGuard:
    """Validate whether an authorization result remains usable."""

    def __init__(self, expected_policy_version: str) -> None:
        """Initialize the guard with the currently active policy version."""
        if not expected_policy_version.strip():
            raise ValueError("expected_policy_version must not be empty")

        self._expected_policy_version = expected_policy_version

    @property
    def expected_policy_version(self) -> str:
        """Return the policy version this guard accepts."""
        return self._expected_policy_version

    def is_authorized(
        self,
        request: CapabilityRequest,
        authorization: AuthorizationResult,
        *,
        now: datetime | None = None,
    ) -> bool:
        """Return whether the authorization is currently executable."""

        return not self.failure_reasons(
            request,
            authorization,
            now=now,
        )

    def failure_reasons(
        self,
        request: CapabilityRequest,
        authorization: AuthorizationResult,
        *,
        now: datetime | None = None,
    ) -> tuple[str, ...]:
        """Return all reasons why authorization cannot be used."""

        current_time = now or datetime.now(UTC)

        if current_time.tzinfo is None or current_time.utcoffset() is None:
            raise ValueError("now must be timezone-aware")

        reasons: list[str] = []

        if authorization.request_id != request.request_id:
            reasons.append("REQUEST_ID_MISMATCH")

        if authorization.principal_id != request.principal_id:
            reasons.append("PRINCIPAL_MISMATCH")

        if authorization.capability_id != request.capability_id:
            reasons.append("CAPABILITY_MISMATCH")

        if authorization.target_scope != request.target_scope:
            reasons.append("TARGET_SCOPE_MISMATCH")

        if authorization.policy_version != self._expected_policy_version:
            reasons.append("POLICY_VERSION_MISMATCH")

        if request.policy_version != authorization.policy_version:
            reasons.append("REQUEST_POLICY_VERSION_MISMATCH")

        if request.is_expired(current_time):
            reasons.append("REQUEST_EXPIRED")

        if authorization.expires_at is not None:
            authorization_expired = current_time >= authorization.expires_at
            if authorization_expired:
                reasons.append("AUTHORIZATION_EXPIRED")

        if authorization.decision is AuthorizationDecision.EXPIRED:
            reasons.append("AUTHORIZATION_EXPIRED")

        if authorization.decision is AuthorizationDecision.REVOKED:
            reasons.append("AUTHORIZATION_REVOKED")

        if authorization.decision is not AuthorizationDecision.ALLOWED:
            reasons.append("AUTHORIZATION_NOT_ALLOWED")

        if authorization.granted is not True:
            reasons.append("AUTHORIZATION_NOT_GRANTED")

        if (
            authorization.expires_at is not None
            and authorization.expires_at > request.expires_at
        ):
            reasons.append("AUTHORIZATION_EXPIRY_EXCEEDS_REQUEST")

        return tuple(dict.fromkeys(reasons))

    def require_authorized(
        self,
        request: CapabilityRequest,
        authorization: AuthorizationResult,
        *,
        now: datetime | None = None,
    ) -> None:
        """Raise when authorization is not currently usable."""

        reasons = self.failure_reasons(
            request,
            authorization,
            now=now,
        )

        if reasons:
            raise PermissionError(
                "authorization rejected: " + ", ".join(reasons)
            )
