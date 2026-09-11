"""Execution policy constraints for the Lyrion secure execution boundary."""

from __future__ import annotations

from dataclasses import dataclass

from lyrion.core.types import ExecutionTarget, RiskLevel
from lyrion.execution.contracts import ExecutionPlan, ExecutionRequest


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    """Immutable platform-level execution constraints."""

    allowed_targets: frozenset[ExecutionTarget] = frozenset(
        {
            ExecutionTarget.LOCAL_CPU,
            ExecutionTarget.REMOTE_SANDBOX,
        }
    )

    max_runtime_seconds: float = 30.0
    max_memory_mb: int = 512
    max_output_bytes: int = 1_048_576
    max_cpu_seconds: float = 30.0

    allow_network_access: bool = False
    allow_external_side_effects: bool = False

    max_risk_level: RiskLevel = RiskLevel.LOW


class ExecutionPolicyEvaluator:
    """Evaluate requests and plans against platform execution limits."""

    _risk_order: dict[RiskLevel, int] = {
        RiskLevel.LOW: 0,
        RiskLevel.MEDIUM: 1,
        RiskLevel.HIGH: 2,
        RiskLevel.CRITICAL: 3,
    }

    def evaluate_request(
        self,
        request: ExecutionRequest,
        policy: ExecutionPolicy,
    ) -> tuple[str, ...]:
        """Return policy violations for an execution request."""
        violations: list[str] = []

        limits = request.resource_limits

        if limits.max_runtime_seconds > policy.max_runtime_seconds:
            violations.append("MAX_RUNTIME_EXCEEDED")

        if limits.max_memory_mb > policy.max_memory_mb:
            violations.append("MAX_MEMORY_EXCEEDED")

        if limits.max_output_bytes > policy.max_output_bytes:
            violations.append("MAX_OUTPUT_EXCEEDED")

        if limits.max_cpu_seconds > policy.max_cpu_seconds:
            violations.append("MAX_CPU_EXCEEDED")

        if (
            request.network_access_allowed
            and not policy.allow_network_access
        ):
            violations.append("NETWORK_ACCESS_NOT_PERMITTED")

        if (
            request.external_side_effects_allowed
            and not policy.allow_external_side_effects
        ):
            violations.append("EXTERNAL_SIDE_EFFECTS_NOT_PERMITTED")

        if self._risk_order[request.risk_level] > self._risk_order[
            policy.max_risk_level
        ]:
            violations.append("RISK_LEVEL_NOT_PERMITTED")

        return tuple(violations)

    def evaluate_plan(
        self,
        plan: ExecutionPlan,
        policy: ExecutionPolicy,
    ) -> tuple[str, ...]:
        """Return policy violations for an execution plan."""
        violations: list[str] = []
        limits = plan.resource_limits

        if plan.execution_target not in policy.allowed_targets:
            violations.append("EXECUTION_TARGET_NOT_PERMITTED")

        if limits.max_runtime_seconds > policy.max_runtime_seconds:
            violations.append("MAX_RUNTIME_EXCEEDED")

        if limits.max_memory_mb > policy.max_memory_mb:
            violations.append("MAX_MEMORY_EXCEEDED")

        if limits.max_output_bytes > policy.max_output_bytes:
            violations.append("MAX_OUTPUT_EXCEEDED")

        if limits.max_cpu_seconds > policy.max_cpu_seconds:
            violations.append("MAX_CPU_EXCEEDED")

        if (
            plan.network_access_allowed
            and not policy.allow_network_access
        ):
            violations.append("NETWORK_ACCESS_NOT_PERMITTED")

        if (
            plan.external_side_effects_allowed
            and not policy.allow_external_side_effects
        ):
            violations.append("EXTERNAL_SIDE_EFFECTS_NOT_PERMITTED")

        return tuple(violations)

    def failure_reasons(
        self,
        request: ExecutionRequest,
        plan: ExecutionPlan,
        policy: ExecutionPolicy,
    ) -> tuple[str, ...]:
        """Return combined deterministic request/plan policy violations."""
        violations = list(
            self.evaluate_request(
                request,
                policy,
            )
        )

        violations.extend(
            self.evaluate_plan(
                plan,
                policy,
            )
        )

        return tuple(dict.fromkeys(violations))

    def is_allowed(
        self,
        request: ExecutionRequest,
        plan: ExecutionPlan,
        policy: ExecutionPolicy,
    ) -> bool:
        """Return whether both request and plan satisfy platform policy."""
        return not self.failure_reasons(
            request,
            plan,
            policy,
        )

    def require_allowed(
        self,
        request: ExecutionRequest,
        plan: ExecutionPlan,
        policy: ExecutionPolicy,
    ) -> None:
        """Raise when request or plan exceeds platform execution policy."""
        reasons = self.failure_reasons(
            request,
            plan,
            policy,
        )

        if reasons:
            raise PermissionError(
                "execution policy rejected request: "
                + ", ".join(reasons)
            )


def default_execution_policy() -> ExecutionPolicy:
    """Return the conservative default execution policy."""
    return ExecutionPolicy()
