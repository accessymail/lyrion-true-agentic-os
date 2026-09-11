"""PIAE-to-secure-execution integration for Lyrion."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field

from lyrion.capabilities.contracts import (
    CapabilityOperation,
    CapabilityRequest,
)
from lyrion.capabilities.gateway import (
    CapabilityGateway,
    ExecutionAdmission,
)
from lyrion.core.types import (
    DecisionId,
    IdempotencyKey,
    RiskLevel,
    TaskId,
)
from lyrion.events.models import EventSensitivity
from lyrion.execution.contracts import (
    ExecutionPlan,
    ExecutionResult,
)
from lyrion.execution.executor import SecureExecutor
from lyrion.execution.sandbox import SandboxConfig
from lyrion.piae.contracts import (
    DecisionCandidate,
    DecisionContext,
    DecisionResult,
)
from lyrion.piae.engine import PIAEDecisionEngine


class CapabilityIntent(BaseModel):
    """Explicit capability authority requested by a proactive decision."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    principal_id: str = Field(
        min_length=1,
        max_length=500,
    )

    capability_id: str = Field(
        min_length=1,
        max_length=500,
    )

    target_scope: str = Field(
        min_length=1,
        max_length=2000,
    )

    operation: CapabilityOperation

    data_classification: EventSensitivity

    task_id: TaskId

    risk_level: RiskLevel

    justification: str = Field(
        min_length=1,
        max_length=4000,
    )

    idempotency_key: IdempotencyKey


class ProactiveExecutionCoordinator:
    """Bridge a PIAE decision to controlled secure execution."""

    def __init__(
        self,
        *,
        gateway: CapabilityGateway,
        executor: SecureExecutor,
        piae: PIAEDecisionEngine | None = None,
    ) -> None:
        """Initialize the proactive execution coordinator."""
        self._piae = piae or PIAEDecisionEngine()
        self._gateway = gateway
        self._executor = executor

    @property
    def piae(self) -> PIAEDecisionEngine:
        """Return the configured PIAE decision engine."""
        return self._piae

    @property
    def gateway(self) -> CapabilityGateway:
        """Return the configured Capability Gateway."""
        return self._gateway

    @property
    def executor(self) -> SecureExecutor:
        """Return the configured Secure Executor."""
        return self._executor

    def decide(
        self,
        context: DecisionContext,
        candidates: tuple[DecisionCandidate, ...],
        *,
        decision_id: DecisionId | None = None,
        input_context_ref: str = "runtime",
    ) -> DecisionResult:
        """Evaluate a proactive decision without executing anything."""
        return self._piae.decide(
            context,
            candidates,
            decision_id=decision_id,
            input_context_ref=input_context_ref,
        )

    def create_capability_request(
        self,
        decision: DecisionResult,
        intent: CapabilityIntent,
        *,
        now: datetime | None = None,
    ) -> CapabilityRequest:
        """Create a capability request from a proactive decision."""
        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        if decision.selected_action.value != "EXECUTE":
            raise ValueError(
                "only EXECUTE decisions can create capability requests"
            )

        if not decision.authorization_required:
            raise ValueError(
                "EXECUTE decision must require authorization"
            )

        if decision.authorization_result.value == "DENIED":
            raise PermissionError(
                "PIAE decision is authorization-denied"
            )

        expires_at = decision.expires_at

        if expires_at is None:
            expires_at = current_time + timedelta(minutes=5)

        if expires_at <= current_time:
            raise ValueError(
                "PIAE decision has expired"
            )

        return CapabilityRequest(
            request_id=f"capreq:{decision.decision_id}",
            decision_id=decision.decision_id,
            task_id=intent.task_id,
            principal_id=intent.principal_id,
            capability_id=intent.capability_id,
            target_scope=intent.target_scope,
            operation=intent.operation,
            data_classification=intent.data_classification,
            autonomy_level=decision.autonomy_level,
            risk_level=intent.risk_level,
            policy_version="aegis-policy-v1",
            correlation_id=decision.correlation_id,
            idempotency_key=intent.idempotency_key,
            requested_at=current_time,
            expires_at=expires_at,
            justification=intent.justification,
        )

    def admit(
        self,
        request: CapabilityRequest,
        *,
        now: datetime | None = None,
    ) -> ExecutionAdmission:
        """Authorize a capability request through Aegis."""
        return self._gateway.admit(
            request,
            now=now,
        )

    def execute(
        self,
        admission: ExecutionAdmission,
        plan: ExecutionPlan,
        sandbox: SandboxConfig,
        *,
        now: datetime | None = None,
    ) -> ExecutionResult:
        """Execute an admitted request through the Secure Executor."""
        return self._executor.execute(
            admission,
            plan,
            sandbox,
            now=now,
        )

    def execute_decision(
        self,
        decision: DecisionResult,
        intent: CapabilityIntent,
        plan: ExecutionPlan,
        sandbox: SandboxConfig,
        *,
        now: datetime | None = None,
    ) -> ExecutionResult:
        """Run the complete controlled decision-to-execution path."""
        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        request = self.create_capability_request(
            decision,
            intent,
            now=current_time,
        )

        admission = self.admit(
            request,
            now=current_time,
        )

        return self.execute(
            admission,
            plan,
            sandbox,
            now=current_time,
        )
