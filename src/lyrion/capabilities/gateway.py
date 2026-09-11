"""Authorization-enforcing Capability Gateway for Lyrion."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from lyrion.capabilities.contracts import (
    AuthorizationDecision,
    AuthorizationResult,
    CapabilityRequest,
)
from lyrion.execution.contracts import ExecutionRequest, ResourceLimits
from lyrion.security.authorization import AegisAuthorizationService


class ExecutionAdmission(BaseModel):
    """Immutable authorization admission passed toward execution."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    request_id: str = Field(
        min_length=1,
        max_length=500,
    )
    capability_id: str = Field(
        min_length=1,
        max_length=500,
    )
    target_scope: str = Field(
        min_length=1,
        max_length=1000,
    )

    admitted: bool
    authorization_decision: AuthorizationDecision

    authorization_reason: str = Field(
        min_length=1,
        max_length=4000,
    )

    policy_version: str = Field(
        min_length=1,
        max_length=200,
    )

    admitted_at: datetime

    execution_request: ExecutionRequest

    @classmethod
    def from_authorization(
        cls,
        request: CapabilityRequest,
        authorization: AuthorizationResult,
        *,
        admitted_at: datetime,
    ) -> ExecutionAdmission:
        """Construct an execution admission from authorization."""

        if (
            admitted_at.tzinfo is None
            or admitted_at.utcoffset() is None
        ):
            raise ValueError(
                "admitted_at must be timezone-aware"
            )

        execution_request = ExecutionRequest(
            execution_id=f"execution:{request.request_id}",
            request_id=request.request_id,
            task_id=request.task_id,
            capability_id=request.capability_id,
            target_scope=request.target_scope,
            operation=request.operation.value,
            authorization_reference=(
                f"authorization:{request.request_id}"
            ),
            policy_version=authorization.policy_version,
            principal_id=request.principal_id,
            autonomy_level=request.autonomy_level,
            risk_level=request.risk_level,
            resource_limits=ResourceLimits(),
            network_access_allowed=False,
            external_side_effects_allowed=False,
            checkpoint_ref=None,
            idempotency_key=request.idempotency_key,
            correlation_id=request.correlation_id,
            requested_at=request.requested_at,
            expires_at=request.expires_at,
        )

        return cls(
            request_id=request.request_id,
            capability_id=request.capability_id,
            target_scope=request.target_scope,
            admitted=(
                authorization.decision
                is AuthorizationDecision.ALLOWED
                and authorization.granted
            ),
            authorization_decision=authorization.decision,
            authorization_reason=authorization.reason,
            policy_version=authorization.policy_version,
            admitted_at=admitted_at.astimezone(UTC),
            execution_request=execution_request,
        )


class CapabilityGateway:
    """Authorize capability requests without executing them."""

    def __init__(
        self,
        authorization_service: AegisAuthorizationService,
    ) -> None:
        """Initialize the gateway with the Aegis boundary."""
        self._authorization_service = authorization_service

    @property
    def authorization_service(
        self,
    ) -> AegisAuthorizationService:
        """Return the configured Aegis authorization service."""
        return self._authorization_service

    def admit(
        self,
        request: CapabilityRequest,
        *,
        now: datetime | None = None,
    ) -> ExecutionAdmission:
        """Evaluate a request and produce an execution admission."""

        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        authorization = self._authorization_service.authorize(
            request,
            now=current_time,
        )

        return ExecutionAdmission.from_authorization(
            request,
            authorization,
            admitted_at=current_time,
        )

    def require_admission(
        self,
        request: CapabilityRequest,
        *,
        now: datetime | None = None,
    ) -> ExecutionAdmission:
        """Return an admission or fail closed."""

        admission = self.admit(
            request,
            now=now,
        )

        if not admission.admitted:
            raise PermissionError(
                "capability admission rejected: "
                + admission.authorization_reason
            )

        return admission
