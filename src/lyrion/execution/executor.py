"""Controlled Secure Executor orchestration for Lyrion."""

from __future__ import annotations

from datetime import UTC, datetime

from lyrion.capabilities.gateway import ExecutionAdmission
from lyrion.execution.backends.linux.enforcement.application import (
    EnforcementApplication,
    EnforcementApplicationContext,
    EnforcementApplicationResult,
    EnforcementApplicationStatus,
)
from lyrion.execution.backends.linux.enforcement.planner import (
    LinuxEnforcementPlanner,
)
from lyrion.execution.checkpoint import CheckpointManager
from lyrion.execution.contracts import (
    ExecutionPlan,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)
from lyrion.execution.policy import (
    ExecutionPolicy,
    ExecutionPolicyEvaluator,
    default_execution_policy,
)
from lyrion.execution.runtime import (
    RuntimeBudget,
    RuntimeController,
    RuntimeState,
)
from lyrion.execution.sandbox import (
    SandboxConfig,
    SandboxPolicy,
    SandboxPolicyEvaluator,
    default_sandbox_policy,
)
from lyrion.execution.validator import ExecutionValidator
from lyrion.observability.execution_audit import ExecutionAuditLog


class SecureExecutor:
    """Orchestrate validated execution without real side effects.

    This first executor implementation is intentionally dry-run only.
    It consumes the exact execution request produced by the Capability
    Gateway and proves the complete pre-execution control chain.
    """

    def __init__(
        self,
        *,
        execution_policy: ExecutionPolicy | None = None,
        sandbox_policy: SandboxPolicy | None = None,
        execution_validator: ExecutionValidator | None = None,
        sandbox_evaluator: SandboxPolicyEvaluator | None = None,
        audit_log: ExecutionAuditLog | None = None,
        checkpoint_manager: CheckpointManager | None = None,
        enforcement_planner: LinuxEnforcementPlanner | None = None,
        enforcement_application: EnforcementApplication | None = None,
        enforcement_backend_id: str = "linux-native",
    ) -> None:
        """Initialize the secure executor and control boundaries."""
        self._execution_policy = (
            execution_policy or default_execution_policy()
        )
        self._sandbox_policy = (
            sandbox_policy or default_sandbox_policy()
        )
        self._execution_validator = (
            execution_validator or ExecutionValidator()
        )
        self._sandbox_evaluator = (
            sandbox_evaluator or SandboxPolicyEvaluator()
        )
        self._audit_log = audit_log or ExecutionAuditLog()
        self._checkpoint_manager = (
            checkpoint_manager or CheckpointManager()
        )

        if (
            enforcement_application is not None
            and enforcement_planner is None
        ):
            raise ValueError(
                "enforcement_planner is required when "
                "enforcement_application is configured"
            )

        if (
            enforcement_backend_id.strip() == ""
        ):
            raise ValueError(
                "enforcement_backend_id must not be empty"
            )

        self._enforcement_planner = enforcement_planner
        self._enforcement_application = enforcement_application
        self._enforcement_backend_id = enforcement_backend_id.strip()

    @property
    def audit_log(self) -> ExecutionAuditLog:
        """Return the configured execution audit log."""
        return self._audit_log

    @property
    def checkpoint_manager(self) -> CheckpointManager:
        """Return the configured checkpoint manager."""
        return self._checkpoint_manager

    @property
    def execution_policy(self) -> ExecutionPolicy:
        """Return the configured execution policy."""
        return self._execution_policy

    @property
    def sandbox_policy(self) -> SandboxPolicy:
        """Return the configured sandbox policy."""
        return self._sandbox_policy

    def execute(
        self,
        admission: ExecutionAdmission,
        plan: ExecutionPlan,
        sandbox: SandboxConfig,
        *,
        now: datetime | None = None,
    ) -> ExecutionResult:
        """Execute one controlled dry-run lifecycle."""

        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        request = admission.execution_request

        self._audit_log.append(
            execution_id=request.execution_id,
            event_type="EXECUTOR_RECEIVED",
            actor="secure-executor",
            details={
                "request_id": request.request_id,
                "admitted": admission.admitted,
                "authorization_decision": (
                    admission.authorization_decision.value
                ),
                "policy_version": request.policy_version,
                "capability_id": request.capability_id,
                "target_scope": request.target_scope,
            },
            occurred_at=current_time,
        )

        if not admission.admitted:
            return self._denied_result(
                request,
                reason=admission.authorization_reason,
                now=current_time,
            )

        validation_reasons = (
            self._execution_validator.failure_reasons(
                request,
                plan,
                now=current_time,
            )
        )

        if validation_reasons:
            reason = (
                "execution validation failed: "
                + ", ".join(validation_reasons)
            )

            self._audit_log.append(
                execution_id=request.execution_id,
                event_type="EXECUTION_VALIDATION_REJECTED",
                actor="secure-executor",
                details={
                    "reasons": validation_reasons,
                },
                occurred_at=current_time,
            )

            return self._denied_result(
                request,
                reason=reason,
                now=current_time,
            )

        execution_policy_reasons = (
            ExecutionPolicyEvaluator().failure_reasons(
                request,
                plan,
                self._execution_policy,
            )
        )

        if execution_policy_reasons:
            reason = (
                "execution policy rejected: "
                + ", ".join(execution_policy_reasons)
            )

            self._audit_log.append(
                execution_id=request.execution_id,
                event_type="EXECUTION_POLICY_REJECTED",
                actor="secure-executor",
                details={
                    "reasons": execution_policy_reasons,
                },
                occurred_at=current_time,
            )

            return self._denied_result(
                request,
                reason=reason,
                now=current_time,
            )

        sandbox_reasons = self._sandbox_evaluator.failure_reasons(
            sandbox,
            self._sandbox_policy,
        )

        if sandbox_reasons:
            reason = (
                "sandbox policy rejected: "
                + ", ".join(sandbox_reasons)
            )

            self._audit_log.append(
                execution_id=request.execution_id,
                event_type="SANDBOX_REJECTED",
                actor="secure-executor",
                details={
                    "reasons": sandbox_reasons,
                },
                occurred_at=current_time,
            )

            return self._denied_result(
                request,
                reason=reason,
                now=current_time,
            )

        if self._enforcement_application is not None:
            enforcement_result = self._apply_enforcement(
                request=request,
                sandbox=sandbox,
                current_time=current_time,
            )

            if not enforcement_result.execution_permitted:
                reason = (
                    enforcement_result.failure_reason
                    or "Linux enforcement verification failed."
                )

                self._audit_log.append(
                    execution_id=request.execution_id,
                    event_type="ENFORCEMENT_REJECTED",
                    actor="secure-executor",
                    details={
                        "backend_id": enforcement_result.backend_id,
                        "status": enforcement_result.status.value,
                        "reason": reason,
                    },
                    occurred_at=current_time,
                )

                return self._failed_enforcement_result(
                    request,
                    reason=reason,
                    now=current_time,
                )

            self._audit_log.append(
                execution_id=request.execution_id,
                event_type="ENFORCEMENT_VERIFIED",
                actor="secure-executor",
                details={
                    "backend_id": enforcement_result.backend_id,
                    "primitive_count": len(
                        enforcement_result.primitive_results
                    ),
                },
                occurred_at=current_time,
            )

        runtime = RuntimeController(
            RuntimeBudget.from_limits(
                request.resource_limits,
                started_at=current_time,
            )
        )

        runtime.start()

        self._audit_log.append(
            execution_id=request.execution_id,
            event_type="EXECUTION_STARTED",
            actor="secure-executor",
            details={
                "dry_run": True,
                "execution_target": sandbox.execution_target.value,
                "operation": request.operation,
            },
            occurred_at=current_time,
        )

        checkpoint_ref: str | None = None

        if plan.checkpoint_required:
            checkpoint_ref = (
                request.checkpoint_ref
                or f"checkpoint:{request.execution_id}"
            )

            checkpoint = self._checkpoint_manager.create(
                checkpoint_id=checkpoint_ref,
                execution_id=request.execution_id,
                revision=1,
                state_ref=f"dry-run:{request.execution_id}",
                metadata={
                    "dry_run": True,
                    "policy_version": request.policy_version,
                },
                created_at=current_time,
            )

            self._checkpoint_manager.seal(
                checkpoint.checkpoint_id,
            )

            self._audit_log.append(
                execution_id=request.execution_id,
                event_type="CHECKPOINT_SEALED",
                actor="secure-executor",
                details={
                    "checkpoint_id": checkpoint.checkpoint_id,
                },
                occurred_at=current_time,
            )

        snapshot = runtime.snapshot(
            now=current_time,
            cpu_seconds=0.0,
            memory_mb=0,
            output_bytes=0,
        )

        if snapshot.state is not RuntimeState.RUNNING:
            return self._runtime_failure_result(
                request,
                snapshot.state,
                (
                    snapshot.violation.value
                    if snapshot.violation is not None
                    else "RUNTIME_CONTROL_FAILED"
                ),
                current_time,
            )

        runtime.complete()

        self._audit_log.append(
            execution_id=request.execution_id,
            event_type="EXECUTION_COMPLETED",
            actor="secure-executor",
            details={
                "dry_run": True,
                "checkpoint_ref": checkpoint_ref,
            },
            occurred_at=current_time,
        )

        return ExecutionResult(
            execution_id=request.execution_id,
            request_id=request.request_id,
            status=ExecutionStatus.COMPLETED,
            started_at=current_time,
            completed_at=current_time,
            exit_code=0,
            output_ref=None,
            error_code=None,
            error_message=None,
            checkpoint_ref=checkpoint_ref,
        )

    def _apply_enforcement(
        self,
        *,
        request: ExecutionRequest,
        sandbox: SandboxConfig,
        current_time: datetime,
    ) -> EnforcementApplicationResult:
        """Plan, apply, and independently verify Linux enforcement."""
        planner = self._enforcement_planner
        application = self._enforcement_application

        if planner is None or application is None:
            raise RuntimeError(
                "Linux enforcement boundary is incompletely configured"
            )

        try:
            enforcement_plan = planner.plan(sandbox)
            enforcement_plan.assert_planning_only()

            context = EnforcementApplicationContext.create(
                execution_id=request.execution_id,
                backend_id=self._enforcement_backend_id,
                started_at=current_time,
                metadata={
                    "request_id": request.request_id,
                    "policy_version": request.policy_version,
                },
            )

            result = application.apply(
                enforcement_plan,
                context,
            )

            if result.execution_id != request.execution_id:
                raise RuntimeError(
                    "Linux enforcement returned an execution identity mismatch"
                )

            if result.backend_id != self._enforcement_backend_id:
                raise RuntimeError(
                    "Linux enforcement returned a backend identity mismatch"
                )

            return result

        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            self._audit_log.append(
                execution_id=request.execution_id,
                event_type="ENFORCEMENT_ERROR",
                actor="secure-executor",
                details={
                    "backend_id": self._enforcement_backend_id,
                    "error_type": type(exc).__name__,
                    "reason": str(exc),
                },
                occurred_at=current_time,
            )

            return EnforcementApplicationResult(
                execution_id=request.execution_id,
                backend_id=self._enforcement_backend_id,
                status=EnforcementApplicationStatus.FAILED,
                primitive_results=(),
                failure_reason=(
                    "Linux enforcement failed closed: "
                    + str(exc)
                ),
            )

    @staticmethod
    def _failed_enforcement_result(
        request: ExecutionRequest,
        *,
        reason: str,
        now: datetime,
    ) -> ExecutionResult:
        """Build a deterministic failed result for enforcement rejection."""
        return ExecutionResult(
            execution_id=request.execution_id,
            request_id=request.request_id,
            status=ExecutionStatus.FAILED,
            started_at=now,
            completed_at=now,
            exit_code=None,
            output_ref=None,
            error_code="ENFORCEMENT_REJECTED",
            error_message=reason,
            checkpoint_ref=None,
        )

    def _denied_result(
        self,
        request: ExecutionRequest,
        *,
        reason: str,
        now: datetime,
    ) -> ExecutionResult:
        """Build a deterministic denied execution result."""
        self._audit_log.append(
            execution_id=request.execution_id,
            event_type="EXECUTION_DENIED",
            actor="secure-executor",
            details={
                "reason": reason,
            },
            occurred_at=now,
        )

        return ExecutionResult(
            execution_id=request.execution_id,
            request_id=request.request_id,
            status=ExecutionStatus.DENIED,
            started_at=now,
            completed_at=None,
            exit_code=None,
            output_ref=None,
            error_code="EXECUTION_DENIED",
            error_message=reason,
            checkpoint_ref=None,
        )

    @staticmethod
    def _runtime_failure_result(
        request: ExecutionRequest,
        state: RuntimeState,
        error_code: str,
        now: datetime,
    ) -> ExecutionResult:
        """Build a result for a runtime-control failure."""
        status_map = {
            RuntimeState.TIMED_OUT: ExecutionStatus.TIMED_OUT,
            RuntimeState.CANCEL_REQUESTED: ExecutionStatus.CANCELLED,
            RuntimeState.TERMINATED: ExecutionStatus.TERMINATED,
        }

        status = status_map.get(
            state,
            ExecutionStatus.FAILED,
        )

        return ExecutionResult(
            execution_id=request.execution_id,
            request_id=request.request_id,
            status=status,
            started_at=now,
            completed_at=now,
            exit_code=None,
            output_ref=None,
            error_code=error_code,
            error_message="Runtime control rejected execution.",
            checkpoint_ref=None,
        )
