"""Bounded Agent Harness orchestration over existing secure execution."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final

from lyrion.capabilities.contracts import (
    AuthorizationDecision,
    AuthorizationResult,
    CapabilityRequest,
)
from lyrion.capabilities.gateway import ExecutionAdmission
from lyrion.execution.contracts import ExecutionPlan, ExecutionResult
from lyrion.execution.executor import SecureExecutor
from lyrion.execution.sandbox import SandboxConfig
from lyrion.observability.execution_audit import ExecutionAuditLog
from lyrion.tasks.models import Task

from .contracts import (
    AgentBinding,
    AgentBindingState,
    AgentExecutionProvenance,
    AgentIdentity,
    BindingValidationResult,
)
from .isolation import AgentIsolationContract


class AgentBindingError(ValueError):
    """Raised when an Agent Harness binding violates its contract."""


class AgentHarness:
    """Bind attributable agents to existing authorized execution context.

    This class deliberately has no authorization, capability-granting,
    admission-creation, sandbox, process-launch, or host-privilege API.
    """

    _VALIDATION_ACTOR: Final[str] = "agent-harness"

    def __init__(
        self,
        *,
        secure_executor: SecureExecutor,
        audit_log: ExecutionAuditLog | None = None,
    ) -> None:
        self._secure_executor = secure_executor
        self._audit_log = audit_log or secure_executor.audit_log

    @property
    def secure_executor(self) -> SecureExecutor:
        """Return the existing secure executor used for delegation."""
        return self._secure_executor

    @property
    def audit_log(self) -> ExecutionAuditLog:
        """Return the attribution/audit boundary used by the harness."""
        return self._audit_log

    def bind(
        self,
        *,
        identity: AgentIdentity,
        task: Task,
        authority_context: AuthorizationResult,
        capability_context: CapabilityRequest,
        execution_admission: ExecutionAdmission,
        provenance_context: str,
    ) -> AgentBinding:
        """Create a binding from already-established execution context."""
        binding = AgentBinding(
            identity=identity,
            task_id=task.task_id,
            authority_context=authority_context,
            capability_context=capability_context,
            execution_admission=execution_admission,
            isolation_contract=AgentIsolationContract(
                agent_id=identity.agent_id,
                task_id=str(task.task_id),
            ),
            provenance_context=provenance_context,
        )

        result = self.validate(binding, task=task)
        if not result.valid:
            raise AgentBindingError(result.failure_reason or "binding rejected")

        self._audit_log.append(
            execution_id=execution_admission.execution_request.execution_id,
            event_type="AGENT_BINDING_VALIDATED",
            actor=self._VALIDATION_ACTOR,
            details={
                "agent_id": identity.agent_id,
                "task_id": str(task.task_id),
                "request_id": execution_admission.request_id,
                "provenance_context": provenance_context,
            },
            occurred_at=execution_admission.admitted_at,
        )

        return binding.transition(AgentBindingState.VALIDATED)

    def validate(
        self,
        binding: AgentBinding,
        *,
        task: Task,
        now: datetime | None = None,
    ) -> BindingValidationResult:
        """Validate all trusted context dimensions and fail closed."""
        current_time = now or datetime.now(UTC)
        if current_time.tzinfo is None or current_time.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        current_time = current_time.astimezone(UTC)

        request = binding.execution_admission.execution_request
        authority = binding.authority_context
        capability = binding.capability_context
        admission = binding.execution_admission

        checks: tuple[tuple[str, bool], ...] = (
            (
                "UNBOUND_AGENT",
                bool(binding.identity.agent_id.strip())
                and bool(binding.identity.identity_provenance_ref.strip()),
            ),
            (
                "TASK_MISMATCH",
                binding.task_id == task.task_id == capability.task_id == request.task_id,
            ),
            (
                "ISOLATION_INVALID",
                binding.isolation_contract.valid
                and binding.isolation_contract.agent_id == binding.identity.agent_id
                and binding.isolation_contract.task_id == str(task.task_id),
            ),
            (
                "LIFECYCLE_INVALID",
                task.status.value == "RUNNING",
            ),
            (
                "AUTHORITY_MISSING",
                authority.decision is AuthorizationDecision.ALLOWED
                and authority.granted,
            ),
            (
                "AUTHORITY_EXPIRED",
                authority.expires_at is not None
                and current_time < authority.expires_at,
            ),
            (
                "AUTHORITY_INVALID",
                authority.request_id == capability.request_id == request.request_id
                and authority.principal_id == capability.principal_id == request.principal_id
                and authority.capability_id == capability.capability_id == request.capability_id
                and authority.target_scope == capability.target_scope == request.target_scope
                and authority.policy_version == capability.policy_version == request.policy_version,
            ),
            (
                "CAPABILITY_MISMATCH",
                admission.capability_id == capability.capability_id
                and admission.target_scope == capability.target_scope,
            ),
            (
                "ADMISSION_INVALID",
                admission.admitted
                and admission.authorization_decision is AuthorizationDecision.ALLOWED
                and admission.execution_request.request_id == capability.request_id
                and admission.admitted_at <= current_time,
            ),
            (
                "CAPABILITY_EXPIRED",
                current_time < capability.expires_at,
            ),
            (
                "EXECUTION_REQUEST_EXPIRED",
                current_time < request.expires_at,
            ),
        )

        for reason, passed in checks:
            if not passed:
                return BindingValidationResult(
                    valid=False,
                    failure_reason=reason,
                )

        if authority.expires_at is None or current_time >= authority.expires_at:
            return BindingValidationResult(
                valid=False,
                failure_reason="AUTHORITY_EXPIRED",
            )

        return BindingValidationResult(
            valid=True,
            validated_agent_id=binding.identity.agent_id,
            validated_task_id=binding.task_id,
            validated_admission=admission,
        )

    def delegate(
        self,
        binding: AgentBinding,
        *,
        task: Task,
        plan: ExecutionPlan,
        sandbox: SandboxConfig,
        now: datetime | None = None,
    ) -> ExecutionResult:
        """Delegate one validated binding through the existing SecureExecutor."""
        if binding.lifecycle_state is not AgentBindingState.VALIDATED:
            raise AgentBindingError(
                "execution requires a VALIDATED agent binding"
            )

        validation = self.validate(binding, task=task, now=now)
        if not validation.valid:
            raise AgentBindingError(
                validation.failure_reason or "binding rejected"
            )

        execution_request = binding.execution_admission.execution_request
        if plan.execution_id != execution_request.execution_id:
            raise AgentBindingError("EXECUTION_ID_MISMATCH")

        result = self._secure_executor.execute(
            binding.execution_admission,
            plan,
            sandbox,
            now=now,
        )

        self._audit_log.append(
            execution_id=execution_request.execution_id,
            event_type="AGENT_EXECUTION_DELEGATED",
            actor=self._VALIDATION_ACTOR,
            details={
                "agent_id": binding.identity.agent_id,
                "task_id": str(task.task_id),
                "request_id": execution_request.request_id,
                "status": result.status.value,
            },
            occurred_at=result.completed_at or result.started_at,
        )

        return result

    def provenance(
        self,
        binding: AgentBinding,
        *,
        task: Task,
        now: datetime | None = None,
    ) -> AgentExecutionProvenance:
        """Return attributable provenance without creating authority."""
        validation = self.validate(binding, task=task, now=now)
        if not validation.valid:
            raise AgentBindingError(
                validation.failure_reason or "binding rejected"
            )

        request = binding.execution_admission.execution_request
        return AgentExecutionProvenance(
            agent_id=binding.identity.agent_id,
            identity_provenance_ref=binding.identity.identity_provenance_ref,
            task_id=task.task_id,
            principal_id=request.principal_id,
            request_id=request.request_id,
            execution_id=request.execution_id,
            capability_id=request.capability_id,
            target_scope=request.target_scope,
            authorization_reference=request.authorization_reference,
            policy_version=request.policy_version,
            provenance_context=binding.provenance_context,
            correlation_id=(
                str(request.correlation_id)
                if request.correlation_id is not None
                else None
            ),
        )


__all__ = [
    "AgentBindingError",
    "AgentHarness",
]
