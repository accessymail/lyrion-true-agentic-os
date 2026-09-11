"""Capability and authorization-boundary contracts for Lyrion."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from lyrion.core.types import (
    AutonomyLevel,
    CorrelationId,
    DecisionId,
    IdempotencyKey,
    RiskLevel,
    TaskId,
)
from lyrion.events.models import EventSensitivity


class CapabilityOperation(StrEnum):
    """Normalized operations a capability request may ask to perform."""

    READ = "READ"
    WRITE = "WRITE"
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    EXECUTE = "EXECUTE"
    SEND = "SEND"
    TRANSFORM = "TRANSFORM"


class AuthorizationDecision(StrEnum):
    """Result returned by the authorization boundary."""

    NOT_EVALUATED = "NOT_EVALUATED"
    ALLOWED = "ALLOWED"
    DENIED = "DENIED"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class CapabilityRequest(BaseModel):
    """Immutable request from PIAE toward the authorization boundary.

    A CapabilityRequest expresses requested authority but never grants it.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    request_id: str = Field(min_length=1, max_length=200)

    decision_id: DecisionId
    task_id: TaskId

    principal_id: str = Field(min_length=1, max_length=500)

    capability_id: str = Field(min_length=1, max_length=500)

    target_scope: str = Field(min_length=1, max_length=2000)
    operation: CapabilityOperation

    data_classification: EventSensitivity

    autonomy_level: AutonomyLevel
    risk_level: RiskLevel

    policy_version: str = Field(min_length=1, max_length=200)

    correlation_id: CorrelationId | None = None
    idempotency_key: IdempotencyKey

    requested_at: datetime
    expires_at: datetime

    justification: str = Field(min_length=1, max_length=4000)

    authorization_decision: AuthorizationDecision = (
        AuthorizationDecision.NOT_EVALUATED
    )

    authorization_granted: bool = False

    @field_validator("requested_at", "expires_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime,
    ) -> datetime:
        """Require timezone-aware authorization-boundary timestamps."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("capability request timestamps must be timezone-aware")

        return value

    @field_validator("expires_at")
    @classmethod
    def validate_expiry(
        cls,
        value: datetime,
        info: object,
    ) -> datetime:
        """Ensure expiry does not precede request creation."""
        data = getattr(info, "data", {})
        requested_at = data.get("requested_at")

        if requested_at is not None and value < requested_at:
            raise ValueError("expires_at cannot be earlier than requested_at")

        return value

    @model_validator(mode="after")
    def validate_authorization_state(self) -> CapabilityRequest:
        """Prevent inconsistent self-granted authorization state."""

        if (
            self.authorization_granted
            and self.authorization_decision is not AuthorizationDecision.ALLOWED
        ):
            raise ValueError(
                "authorization_granted requires an ALLOWED authorization decision"
            )

        return self

    def is_expired(self, now: datetime | None = None) -> bool:
        """Return whether the capability request has expired."""
        current_time = now or datetime.now(UTC)

        if current_time.tzinfo is None or current_time.utcoffset() is None:
            raise ValueError("now must be timezone-aware")

        return current_time >= self.expires_at


class AuthorizationResult(BaseModel):
    """Immutable authorization result produced by the Aegis boundary."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    request_id: str = Field(min_length=1, max_length=200)

    decision: AuthorizationDecision
    granted: bool = False

    principal_id: str = Field(min_length=1, max_length=500)
    capability_id: str = Field(min_length=1, max_length=500)
    target_scope: str = Field(min_length=1, max_length=2000)

    policy_version: str = Field(min_length=1, max_length=200)

    reason: str = Field(min_length=1, max_length=4000)

    evaluated_at: datetime
    expires_at: datetime | None = None

    @field_validator("evaluated_at", "expires_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        """Require timezone-aware authorization timestamps."""
        if value is None:
            return None

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("authorization timestamps must be timezone-aware")

        return value

    @field_validator("expires_at")
    @classmethod
    def validate_authorization_expiry(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        """Ensure authorization does not expire before evaluation."""
        if value is None:
            return None

        data = getattr(info, "data", {})
        evaluated_at = data.get("evaluated_at")

        if evaluated_at is not None and value < evaluated_at:
            raise ValueError("authorization expiry cannot precede evaluation")

        return value

    @model_validator(mode="after")
    def validate_grant_state(self) -> AuthorizationResult:
        """Keep grant state consistent with the authorization decision."""

        if self.granted and self.decision is not AuthorizationDecision.ALLOWED:
            raise ValueError("granted requires an ALLOWED authorization decision")

        if self.decision is AuthorizationDecision.ALLOWED and not self.granted:
            raise ValueError("ALLOWED authorization decisions must be granted")

        return self
