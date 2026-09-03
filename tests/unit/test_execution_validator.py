"""Adversarial tests for the execution request/plan validator."""

from datetime import UTC, datetime, timedelta

import pytest

from lyrion.core.types import (
    AutonomyLevel,
    ExecutionTarget,
    IdempotencyKey,
    RiskLevel,
    TaskId,
)
from lyrion.execution.contracts import (
    ExecutionPlan,
    ExecutionRequest,
    ResourceLimits,
)
from lyrion.execution.validator import (
    ExecutionValidationError,
    ExecutionValidator,
)


def make_limits(**overrides: object) -> ResourceLimits:
    """Create baseline resource limits."""
    values: dict[str, object] = {
        "max_runtime_seconds": 30.0,
        "max_memory_mb": 512,
        "max_output_bytes": 1_048_576,
        "max_cpu_seconds": 30.0,
    }

    values.update(overrides)

    return ResourceLimits(**values)


def make_request(**overrides: object) -> ExecutionRequest:
    """Create a valid baseline execution request."""
    now = datetime.now(UTC)

    values: dict[str, object] = {
        "execution_id": "exec_validator_001",
        "request_id": "request_validator_001",
        "task_id": TaskId("task_validator_001"),
        "capability_id": "development.prepare",
        "target_scope": "lyrion/project/src",
        "operation": "READ",
        "authorization_reference": "auth_validator_001",
        "policy_version": "aegis-policy-v1",
        "principal_id": "lyrion-piae",
        "autonomy_level": AutonomyLevel.L1,
        "risk_level": RiskLevel.LOW,
        "resource_limits": make_limits(),
        "network_access_allowed": False,
        "external_side_effects_allowed": False,
        "checkpoint_ref": None,
        "idempotency_key": IdempotencyKey(
            "idem_validator_001",
        ),
        "correlation_id": None,
        "requested_at": now,
        "expires_at": now + timedelta(minutes=5),
    }

    values.update(overrides)

    return ExecutionRequest(**values)


def make_plan(**overrides: object) -> ExecutionPlan:
    """Create a valid baseline execution plan."""
    values: dict[str, object] = {
        "execution_id": "exec_validator_001",
        "execution_target": ExecutionTarget.LOCAL_CPU,
        "command_ref": None,
        "input_ref": None,
        "output_ref": None,
        "resource_limits": make_limits(),
        "network_access_allowed": False,
        "external_side_effects_allowed": False,
        "checkpoint_required": False,
    }

    values.update(overrides)

    return ExecutionPlan(**values)


def test_matching_request_and_plan_are_valid() -> None:
    """A plan matching the request should pass validation."""
    request = make_request()
    plan = make_plan()

    validator = ExecutionValidator()

    assert validator.is_valid(
        request,
        plan,
        now=request.requested_at,
    )

    validator.validate(
        request,
        plan,
        now=request.requested_at,
    )


def test_execution_id_mismatch_is_rejected() -> None:
    """Plan and request must belong to the same execution."""
    request = make_request()
    plan = make_plan(
        execution_id="different-execution",
    )

    validator = ExecutionValidator()

    assert "EXECUTION_ID_MISMATCH" in validator.failure_reasons(
        request,
        plan,
        now=request.requested_at,
    )

    with pytest.raises(ExecutionValidationError):
        validator.validate(
            request,
            plan,
            now=request.requested_at,
        )


def test_expired_request_is_rejected() -> None:
    """Expired execution requests must not reach execution."""
    now = datetime.now(UTC)

    request = make_request(
        requested_at=now - timedelta(minutes=5),
        expires_at=now - timedelta(seconds=1),
    )
    plan = make_plan()

    validator = ExecutionValidator()

    reasons = validator.failure_reasons(
        request,
        plan,
        now=now,
    )

    assert "EXECUTION_REQUEST_EXPIRED" in reasons
    assert validator.is_valid(
        request,
        plan,
        now=now,
    ) is False


def test_resource_limit_escalation_is_rejected() -> None:
    """A plan must not exceed the request resource limits."""
    request = make_request(
        resource_limits=make_limits(
            max_runtime_seconds=30.0,
            max_memory_mb=512,
            max_output_bytes=1_048_576,
            max_cpu_seconds=30.0,
        )
    )

    plan = make_plan(
        resource_limits=make_limits(
            max_runtime_seconds=60.0,
            max_memory_mb=1024,
            max_output_bytes=2_097_152,
            max_cpu_seconds=60.0,
        )
    )

    validator = ExecutionValidator()

    assert "RESOURCE_LIMIT_MISMATCH" in validator.failure_reasons(
        request,
        plan,
        now=request.requested_at,
    )


def test_matching_resource_limits_are_accepted() -> None:
    """A plan using exactly the requested limits is valid."""
    limits = make_limits(
        max_runtime_seconds=10.0,
        max_memory_mb=256,
        max_output_bytes=500_000,
        max_cpu_seconds=10.0,
    )

    request = make_request(
        resource_limits=limits,
    )
    plan = make_plan(
        resource_limits=limits,
    )

    validator = ExecutionValidator()

    assert validator.is_valid(
        request,
        plan,
        now=request.requested_at,
    )


def test_network_access_escalation_is_rejected() -> None:
    """The plan cannot enable network access denied by the request."""
    request = make_request(
        network_access_allowed=False,
    )
    plan = make_plan(
        network_access_allowed=True,
    )

    validator = ExecutionValidator()

    assert "NETWORK_ACCESS_ESCALATION" in validator.failure_reasons(
        request,
        plan,
        now=request.requested_at,
    )


def test_network_access_allowed_by_request_is_valid() -> None:
    """Network access is valid when explicitly allowed by the request."""
    request = make_request(
        network_access_allowed=True,
    )
    plan = make_plan(
        network_access_allowed=True,
    )

    validator = ExecutionValidator()

    assert validator.is_valid(
        request,
        plan,
        now=request.requested_at,
    )


def test_external_side_effect_escalation_is_rejected() -> None:
    """The plan cannot enable side effects denied by the request."""
    request = make_request(
        external_side_effects_allowed=False,
    )
    plan = make_plan(
        external_side_effects_allowed=True,
    )

    validator = ExecutionValidator()

    assert "EXTERNAL_SIDE_EFFECT_ESCALATION" in validator.failure_reasons(
        request,
        plan,
        now=request.requested_at,
    )


def test_external_side_effects_authorized_by_request_are_valid() -> None:
    """Explicitly authorized side effects may be represented."""
    request = make_request(
        external_side_effects_allowed=True,
    )
    plan = make_plan(
        external_side_effects_allowed=True,
    )

    validator = ExecutionValidator()

    assert validator.is_valid(
        request,
        plan,
        now=request.requested_at,
    )


def test_checkpoint_required_plan_allows_generated_reference() -> None:
    """A checkpoint-required plan may generate its reference at execution."""
    request = make_request(
        checkpoint_ref=None,
    )
    plan = make_plan(
        checkpoint_required=True,
    )

    validator = ExecutionValidator()

    assert validator.is_valid(
        request,
        plan,
        now=request.requested_at,
    )


def test_checkpoint_requirement_is_valid_with_reference() -> None:
    """A checkpoint-required plan is valid with a request reference."""
    request = make_request(
        checkpoint_ref="checkpoint_validator_001",
    )
    plan = make_plan(
        checkpoint_required=True,
    )

    validator = ExecutionValidator()

    assert validator.is_valid(
        request,
        plan,
        now=request.requested_at,
    )


def test_cloud_gpu_target_is_closed_by_default() -> None:
    """Unenabled execution targets must fail closed."""
    request = make_request()
    plan = make_plan(
        execution_target=ExecutionTarget.CLOUD_GPU,
    )

    validator = ExecutionValidator()

    assert "EXECUTION_TARGET_NOT_ENABLED" in (
        validator.failure_reasons(
            request,
            plan,
            now=request.requested_at,
        )
    )


def test_execute_operation_requires_command_reference() -> None:
    """Execution-like operations require a command reference."""
    request = make_request(
        operation="EXECUTE",
    )
    plan = make_plan(
        command_ref=None,
    )

    validator = ExecutionValidator()

    assert "COMMAND_REFERENCE_REQUIRED" in (
        validator.failure_reasons(
            request,
            plan,
            now=request.requested_at,
        )
    )


def test_execute_operation_with_command_reference_is_valid() -> None:
    """An explicit command reference satisfies the requirement."""
    request = make_request(
        operation="EXECUTE",
    )
    plan = make_plan(
        command_ref="command_ref_001",
    )

    validator = ExecutionValidator()

    assert validator.is_valid(
        request,
        plan,
        now=request.requested_at,
    )


def test_read_operation_does_not_require_command_reference() -> None:
    """Read operations can remain plan-only at this stage."""
    request = make_request(
        operation="READ",
    )
    plan = make_plan(
        command_ref=None,
    )

    validator = ExecutionValidator()

    assert validator.is_valid(
        request,
        plan,
        now=request.requested_at,
    )


def test_naive_validation_time_is_rejected() -> None:
    """Validator clocks must be timezone-aware."""
    request = make_request()
    plan = make_plan()

    with pytest.raises(ValueError):
        ExecutionValidator().is_valid(
            request,
            plan,
            now=datetime.now(),
        )


def test_failure_reasons_are_deterministic() -> None:
    """The same inputs must produce identical failure reasons."""
    request = make_request()

    plan = make_plan(
        execution_id="plan-execution",
        resource_limits=make_limits(
            max_runtime_seconds=60.0,
        ),
        network_access_allowed=True,
        external_side_effects_allowed=True,
        checkpoint_required=True,
        execution_target=ExecutionTarget.CLOUD_GPU,
    )

    validator = ExecutionValidator()

    first = validator.failure_reasons(
        request,
        plan,
        now=request.requested_at,
    )
    second = validator.failure_reasons(
        request,
        plan,
        now=request.requested_at,
    )

    assert first == second
    assert "EXECUTION_ID_MISMATCH" in first
    assert "RESOURCE_LIMIT_MISMATCH" in first
    assert "NETWORK_ACCESS_ESCALATION" in first
    assert "EXTERNAL_SIDE_EFFECT_ESCALATION" in first
    assert "EXECUTION_TARGET_NOT_ENABLED" in first


def test_validator_does_not_modify_request_or_plan() -> None:
    """Validation must be observational and side-effect free."""
    request = make_request()
    plan = make_plan()

    validator = ExecutionValidator()

    before_request = request.model_dump(mode="json")
    before_plan = plan.model_dump(mode="json")

    validator.is_valid(
        request,
        plan,
        now=request.requested_at,
    )

    assert request.model_dump(mode="json") == before_request
    assert plan.model_dump(mode="json") == before_plan


def test_validator_preserves_fail_closed_behavior() -> None:
    """Any validation error means execution is not considered valid."""
    request = make_request()
    plan = make_plan(
        network_access_allowed=True,
    )

    validator = ExecutionValidator()

    with pytest.raises(ExecutionValidationError):
        validator.validate(
            request,
            plan,
            now=request.requested_at,
        )
