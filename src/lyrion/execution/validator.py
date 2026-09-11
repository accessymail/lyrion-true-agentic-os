"""Validation boundary between execution requests and execution plans."""

from __future__ import annotations

from datetime import UTC, datetime

from lyrion.execution.contracts import ExecutionPlan, ExecutionRequest


class ExecutionValidationError(ValueError):
    """Raised when an execution request and plan are incompatible."""


class ExecutionValidator:
    """Validate execution admission data before secure execution."""

    def validate(
        self,
        request: ExecutionRequest,
        plan: ExecutionPlan,
        *,
        now: datetime | None = None,
    ) -> None:
        """Validate that a plan is permitted by its execution request."""
        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        errors = self.failure_reasons(
            request,
            plan,
            now=current_time,
        )

        if errors:
            raise ExecutionValidationError(
                "execution validation failed: "
                + ", ".join(errors)
            )

    def is_valid(
        self,
        request: ExecutionRequest,
        plan: ExecutionPlan,
        *,
        now: datetime | None = None,
    ) -> bool:
        """Return whether the request and plan are compatible."""
        return not self.failure_reasons(
            request,
            plan,
            now=now,
        )

    def failure_reasons(
        self,
        request: ExecutionRequest,
        plan: ExecutionPlan,
        *,
        now: datetime | None = None,
    ) -> tuple[str, ...]:
        """Return deterministic reasons why a plan must be rejected."""
        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        reasons: list[str] = []

        if request.execution_id != plan.execution_id:
            reasons.append("EXECUTION_ID_MISMATCH")

        if request.expires_at <= current_time:
            reasons.append("EXECUTION_REQUEST_EXPIRED")

        if plan.resource_limits != request.resource_limits:
            reasons.append("RESOURCE_LIMIT_MISMATCH")

        if (
            plan.network_access_allowed
            and not request.network_access_allowed
        ):
            reasons.append("NETWORK_ACCESS_ESCALATION")

        if (
            plan.external_side_effects_allowed
            and not request.external_side_effects_allowed
        ):
            reasons.append("EXTERNAL_SIDE_EFFECT_ESCALATION")

        if (
            plan.checkpoint_required
            and request.checkpoint_ref is not None
            and not request.checkpoint_ref.strip()
        ):
            reasons.append("INVALID_CHECKPOINT_REFERENCE")

        if plan.execution_target.name == "CLOUD_GPU":
            reasons.append("EXECUTION_TARGET_NOT_ENABLED")

        if (
            plan.command_ref is None
            and request.operation in {
                "EXECUTE",
                "WRITE",
                "DELETE",
                "MODIFY",
            }
        ):
            reasons.append("COMMAND_REFERENCE_REQUIRED")

        return tuple(dict.fromkeys(reasons))
