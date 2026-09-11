"""Unit tests for secure execution contracts."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lyrion.core.types import (
    AutonomyLevel,
    ExecutionTarget,
    IdempotencyKey,
    RiskLevel,
    TaskId,
)
from lyrion.execution.contracts import (
    ExecutionAdmissionEnvelope,
    ExecutionPlan,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ResourceLimits,
)


def make_limits(**overrides: object) -> ResourceLimits:
    """Create valid resource limits."""
    values: dict[str, object] = {
        "max_runtime_seconds": 30.0,
        "max_memory_mb": 512,
        "max_output_bytes": 1_048_576,
        "max_cpu_seconds": 30.0,
    }

    values.update(overrides)
    return ResourceLimits(**values)


def make_request(**overrides: object) -> ExecutionRequest:
    """Create a valid execution request."""
    now = datetime.now(UTC)

    values: dict[str, object] = {
        "execution_id": "exec_test_001",
        "request_id": "request_test_001",
        "task_id": TaskId("task_test_001"),
        "capability_id": "development.prepare",
        "target_scope": "lyrion/project/src",
        "operation": "read",
        "authorization_reference": "auth_test_001",
        "policy_version": "aegis-policy-v1",
        "principal_id": "lyrion-piae",
        "autonomy_level": AutonomyLevel.L1,
        "risk_level": RiskLevel.LOW,
        "resource_limits": make_limits(),
        "network_access_allowed": False,
        "external_side_effects_allowed": False,
        "checkpoint_ref": None,
        "idempotency_key": IdempotencyKey("idem_test_001"),
        "correlation_id": None,
        "requested_at": now,
        "expires_at": now + timedelta(minutes=5),
    }

    values.update(overrides)
    return ExecutionRequest(**values)


def make_result(**overrides: object) -> ExecutionResult:
    """Create a valid execution result."""
    now = datetime.now(UTC)

    values: dict[str, object] = {
        "execution_id": "exec_test_001",
        "request_id": "request_test_001",
        "status": ExecutionStatus.COMPLETED,
        "started_at": now,
        "completed_at": now,
        "exit_code": 0,
        "output_ref": "output_test_001",
        "error_code": None,
        "error_message": None,
        "checkpoint_ref": None,
    }

    values.update(overrides)
    return ExecutionResult(**values)


def test_resource_limits_creation() -> None:
    """Valid resource limits should be accepted."""
    limits = make_limits()

    assert limits.max_runtime_seconds == 30.0
    assert limits.max_memory_mb == 512
    assert limits.max_output_bytes == 1_048_576


def test_resource_limits_reject_zero_runtime() -> None:
    """Runtime must be strictly positive."""
    with pytest.raises(ValidationError):
        make_limits(max_runtime_seconds=0)


def test_resource_limits_reject_negative_memory() -> None:
    """Memory limits must be positive."""
    with pytest.raises(ValidationError):
        make_limits(max_memory_mb=-1)


def test_execution_request_creation() -> None:
    """Valid execution requests should be accepted."""
    request = make_request()

    assert request.execution_id == "exec_test_001"
    assert request.operation == "READ"
    assert request.network_access_allowed is False


def test_operation_is_normalized() -> None:
    """Operation identifiers should normalize to uppercase."""
    request = make_request(operation="  execute ")

    assert request.operation == "EXECUTE"


def test_execution_request_is_immutable() -> None:
    """Execution requests must be immutable."""
    request = make_request()

    with pytest.raises(ValidationError):
        request.target_scope = "changed"


def test_execution_request_requires_timezone_aware_timestamps() -> None:
    """Execution request timestamps must be timezone-aware."""
    with pytest.raises(ValidationError):
        make_request(
            requested_at=datetime.now(),
        )


def test_execution_request_expiry_must_follow_request_time() -> None:
    """Expiry cannot precede request creation."""
    requested = datetime.now(UTC)

    with pytest.raises(ValidationError):
        make_request(
            requested_at=requested,
            expires_at=requested - timedelta(seconds=1),
        )


def test_execution_plan_creation() -> None:
    """Valid execution plans should be accepted."""
    plan = ExecutionPlan(
        execution_id="exec_test_001",
        execution_target=ExecutionTarget.REMOTE_SANDBOX,
        resource_limits=make_limits(),
        network_access_allowed=False,
        external_side_effects_allowed=False,
        checkpoint_required=True,
    )

    assert plan.execution_target is ExecutionTarget.REMOTE_SANDBOX
    assert plan.checkpoint_required is True


def test_execution_plan_is_immutable() -> None:
    """Execution plans must be immutable."""
    plan = ExecutionPlan(
        execution_id="exec_test_001",
        execution_target=ExecutionTarget.LOCAL_CPU,
        resource_limits=make_limits(),
    )

    with pytest.raises(ValidationError):
        plan.execution_target = ExecutionTarget.CLOUD_GPU


def test_completed_execution_result_is_valid() -> None:
    """Completed executions should accept successful metadata."""
    result = make_result()

    assert result.status is ExecutionStatus.COMPLETED
    assert result.exit_code == 0


def test_failed_execution_requires_error_information() -> None:
    """Failed executions require error information."""
    with pytest.raises(ValidationError):
        make_result(
            status=ExecutionStatus.FAILED,
            error_code=None,
            error_message=None,
        )


def test_failed_execution_can_have_error_code() -> None:
    """A failed execution with an error code is valid."""
    result = make_result(
        status=ExecutionStatus.FAILED,
        exit_code=1,
        error_code="EXECUTION_FAILED",
    )

    assert result.status is ExecutionStatus.FAILED
    assert result.error_code == "EXECUTION_FAILED"


def test_completion_cannot_precede_start() -> None:
    """Completion time cannot precede execution start."""
    started = datetime.now(UTC)

    with pytest.raises(ValidationError):
        make_result(
            started_at=started,
            completed_at=started - timedelta(seconds=1),
        )


def test_execution_result_is_immutable() -> None:
    """Execution results must be immutable."""
    result = make_result()

    with pytest.raises(ValidationError):
        result.status = ExecutionStatus.CANCELLED


def test_admission_envelope_requires_timezone_aware_time() -> None:
    """Admission timestamp must be timezone-aware."""
    request = make_request()

    with pytest.raises(ValidationError):
        ExecutionAdmissionEnvelope(
            execution_request=request,
            admitted_at=datetime.now(),
        )


def test_admission_envelope_creation() -> None:
    """Valid admission envelopes should be accepted."""
    request = make_request()
    now = datetime.now(UTC)

    envelope = ExecutionAdmissionEnvelope(
        execution_request=request,
        admitted_at=now,
    )

    assert envelope.execution_request.execution_id == request.execution_id
    assert envelope.admitted_at.tzinfo is UTC


def test_execution_request_rejects_unknown_fields() -> None:
    """Execution requests must reject undeclared fields."""
    with pytest.raises(ValidationError):
        make_request(unknown_field="not-allowed")


def test_execution_plan_rejects_unknown_fields() -> None:
    """Execution plans must reject undeclared fields."""
    with pytest.raises(ValidationError):
        ExecutionPlan(
            execution_id="exec_test_001",
            execution_target=ExecutionTarget.LOCAL_CPU,
            resource_limits=make_limits(),
            unknown_field="not-allowed",
        )


def test_execution_result_rejects_unknown_fields() -> None:
    """Execution results must reject undeclared fields."""
    with pytest.raises(ValidationError):
        make_result(unknown_field="not-allowed")


def test_execution_boundaries_are_explicit() -> None:
    """Network and side-effect permissions default to denied."""
    request = make_request()

    assert request.network_access_allowed is False
    assert request.external_side_effects_allowed is False


def test_checkpoint_reference_can_be_provided() -> None:
    """Execution requests can carry checkpoint references."""
    request = make_request(
        checkpoint_ref="checkpoint_001",
    )

    assert request.checkpoint_ref == "checkpoint_001"
