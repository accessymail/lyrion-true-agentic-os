"""Adversarial tests for the controlled Secure Executor."""

from datetime import UTC, datetime, timedelta

import pytest

from lyrion.capabilities.contracts import (
    AuthorizationDecision,
    AuthorizationResult,
    CapabilityOperation,
    CapabilityRequest,
)
from lyrion.capabilities.gateway import ExecutionAdmission
from lyrion.core.types import (
    AutonomyLevel,
    DecisionId,
    ExecutionTarget,
    IdempotencyKey,
    RiskLevel,
    TaskId,
)
from lyrion.events.models import EventSensitivity
from lyrion.execution.checkpoint import CheckpointManager
from lyrion.execution.contracts import (
    ExecutionPlan,
    ExecutionStatus,
    ResourceLimits,
)
from lyrion.execution.executor import SecureExecutor
from lyrion.execution.sandbox import (
    EnvironmentMode,
    FilesystemMode,
    IsolationLevel,
    NetworkMode,
    SandboxConfig,
)
from lyrion.observability.execution_audit import ExecutionAuditLog


def make_capability_request(
    **overrides: object,
) -> CapabilityRequest:
    """Create a valid capability request."""
    now = datetime.now(UTC)

    values: dict[str, object] = {
        "request_id": "executor-request-001",
        "decision_id": DecisionId("executor-decision-001"),
        "task_id": TaskId("executor-task-001"),
        "principal_id": "lyrion-piae",
        "capability_id": "development.prepare",
        "target_scope": "lyrion/project/src",
        "operation": CapabilityOperation.READ,
        "data_classification": EventSensitivity.INTERNAL,
        "autonomy_level": AutonomyLevel.L1,
        "risk_level": RiskLevel.LOW,
        "policy_version": "aegis-policy-v1",
        "correlation_id": None,
        "idempotency_key": IdempotencyKey(
            "executor-idempotency-001",
        ),
        "requested_at": now,
        "expires_at": now + timedelta(minutes=5),
        "justification": "Secure executor test.",
    }

    values.update(overrides)

    return CapabilityRequest(**values)


def make_admission(
    *,
    admitted: bool = True,
    authorization_decision: AuthorizationDecision = (
        AuthorizationDecision.ALLOWED
    ),
    authorization_reason: str = "Authorized.",
    **request_overrides: object,
) -> ExecutionAdmission:
    """Create an execution admission from an authorization result."""
    request = make_capability_request(
        **request_overrides,
    )

    authorization = AuthorizationResult(
        request_id=request.request_id,
        decision=authorization_decision,
        granted=admitted,
        principal_id=request.principal_id,
        capability_id=request.capability_id,
        target_scope=request.target_scope,
        policy_version=request.policy_version,
        reason=authorization_reason,
        evaluated_at=request.requested_at,
        expires_at=request.expires_at,
    )

    return ExecutionAdmission.from_authorization(
        request,
        authorization,
        admitted_at=request.requested_at,
    )


def make_plan(**overrides: object) -> ExecutionPlan:
    """Create a valid execution plan."""
    values: dict[str, object] = {
        "execution_id": "execution:executor-request-001",
        "execution_target": ExecutionTarget.REMOTE_SANDBOX,
        "command_ref": None,
        "input_ref": None,
        "output_ref": None,
        "resource_limits": ResourceLimits(),
        "network_access_allowed": False,
        "external_side_effects_allowed": False,
        "checkpoint_required": False,
    }

    values.update(overrides)

    return ExecutionPlan(**values)


def make_sandbox(**overrides: object) -> SandboxConfig:
    """Create a valid sandbox configuration."""
    values: dict[str, object] = {
        "execution_target": ExecutionTarget.REMOTE_SANDBOX,
        "filesystem_mode": FilesystemMode.ISOLATED,
        "network_mode": NetworkMode.DISABLED,
        "environment_mode": EnvironmentMode.EMPTY,
        "isolation_level": IsolationLevel.STRICT,
        "writable_paths": (),
        "read_only_paths": (),
        "allowed_environment_keys": (),
        "resource_limits": ResourceLimits(),
        "allow_process_creation": False,
        "allow_privileged_operations": False,
    }

    values.update(overrides)

    return SandboxConfig(**values)


def test_allowed_admission_completes_dry_run() -> None:
    """An authorized, policy-valid execution should complete."""
    admission = make_admission()
    plan = make_plan()
    sandbox = make_sandbox()

    executor = SecureExecutor()

    result = executor.execute(
        admission,
        plan,
        sandbox,
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.COMPLETED
    assert result.exit_code == 0
    assert result.execution_id == (
        admission.execution_request.execution_id
    )
    assert result.request_id == (
        admission.execution_request.request_id
    )


def test_dry_run_does_not_execute_real_command() -> None:
    """The dry-run executor must not execute a command."""
    admission = make_admission()
    plan = make_plan(
        command_ref="would-be-executed-command",
    )
    sandbox = make_sandbox()

    result = SecureExecutor().execute(
        admission,
        plan,
        sandbox,
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.COMPLETED
    assert result.exit_code == 0
    assert result.output_ref is None


def test_denied_admission_returns_denied_result() -> None:
    """A denied admission must fail closed."""
    admission = make_admission(
        admitted=False,
        authorization_decision=AuthorizationDecision.DENIED,
        authorization_reason="Policy denied request.",
    )
    plan = make_plan()
    sandbox = make_sandbox()

    result = SecureExecutor().execute(
        admission,
        plan,
        sandbox,
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.DENIED
    assert result.error_code == "EXECUTION_DENIED"
    assert "Policy denied request." in (
        result.error_message or ""
    )


def test_validation_mismatch_returns_denied_result() -> None:
    """An execution identity mismatch must be rejected."""
    admission = make_admission()
    plan = make_plan(
        execution_id="different-execution",
    )
    sandbox = make_sandbox()

    result = SecureExecutor().execute(
        admission,
        plan,
        sandbox,
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.DENIED
    assert "EXECUTION_ID_MISMATCH" in (
        result.error_message or ""
    )


def test_execution_policy_violation_returns_denied_result() -> None:
    """A policy violation must be rejected before execution."""
    admission = make_admission(
        risk_level=RiskLevel.HIGH,
    )
    plan = make_plan()
    sandbox = make_sandbox()

    result = SecureExecutor().execute(
        admission,
        plan,
        sandbox,
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.DENIED
    assert "RISK_LEVEL_NOT_PERMITTED" in (
        result.error_message or ""
    )


def test_sandbox_policy_violation_returns_denied_result() -> None:
    """A sandbox policy violation must fail closed."""
    admission = make_admission()
    plan = make_plan()
    sandbox = make_sandbox(
        execution_target=ExecutionTarget.CLOUD_GPU,
    )

    result = SecureExecutor().execute(
        admission,
        plan,
        sandbox,
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.DENIED
    assert "SANDBOX_TARGET_NOT_PERMITTED" in (
        result.error_message or ""
    )


def test_checkpoint_is_created_and_sealed() -> None:
    """Checkpoint-required execution creates sealed evidence."""
    admission = make_admission()
    plan = make_plan(
        checkpoint_required=True,
        execution_id=admission.execution_request.execution_id,
    )
    sandbox = make_sandbox()

    checkpoint_manager = CheckpointManager()

    result = SecureExecutor(
        checkpoint_manager=checkpoint_manager,
    ).execute(
        admission,
        plan,
        sandbox,
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.COMPLETED
    assert result.checkpoint_ref is not None

    checkpoint = checkpoint_manager.get(
        result.checkpoint_ref,
    )

    assert checkpoint is not None
    assert checkpoint.status.value == "SEALED"
    assert checkpoint_manager.verify(
        result.checkpoint_ref,
    ) is True


def test_audit_events_are_emitted() -> None:
    """Secure execution should leave an auditable lifecycle."""
    admission = make_admission()
    plan = make_plan(
        execution_id=admission.execution_request.execution_id,
    )
    sandbox = make_sandbox()

    audit = ExecutionAuditLog()

    result = SecureExecutor(
        audit_log=audit,
    ).execute(
        admission,
        plan,
        sandbox,
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.COMPLETED

    events = audit.events_for(
        admission.execution_request.execution_id,
    )

    event_types = [
        event.event_type
        for event in events
    ]

    assert "EXECUTOR_RECEIVED" in event_types
    assert "EXECUTION_STARTED" in event_types
    assert "EXECUTION_COMPLETED" in event_types
    assert audit.verify_chain() is True


def test_denied_execution_is_audited() -> None:
    """Denied execution must also produce evidence."""
    admission = make_admission(
        admitted=False,
        authorization_decision=AuthorizationDecision.DENIED,
        authorization_reason="Denied by policy.",
    )
    plan = make_plan(
        execution_id=admission.execution_request.execution_id,
    )
    sandbox = make_sandbox()

    audit = ExecutionAuditLog()

    result = SecureExecutor(
        audit_log=audit,
    ).execute(
        admission,
        plan,
        sandbox,
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.DENIED

    events = audit.events_for(
        admission.execution_request.execution_id,
    )

    assert any(
        event.event_type == "EXECUTION_DENIED"
        for event in events
    )


def test_naive_executor_time_is_rejected() -> None:
    """Executor time must be timezone-aware."""
    admission = make_admission()
    plan = make_plan()
    sandbox = make_sandbox()

    with pytest.raises(ValueError):
        SecureExecutor().execute(
            admission,
            plan,
            sandbox,
            now=datetime.now(),
        )


def test_executor_does_not_mutate_plan() -> None:
    """The executor must not modify the execution plan."""
    admission = make_admission()
    plan = make_plan()
    sandbox = make_sandbox()

    before = plan.model_dump(mode="json")

    SecureExecutor().execute(
        admission,
        plan,
        sandbox,
        now=admission.admitted_at,
    )

    assert plan.model_dump(mode="json") == before


def test_executor_does_not_mutate_sandbox() -> None:
    """The executor must not modify sandbox configuration."""
    admission = make_admission()
    plan = make_plan()
    sandbox = make_sandbox()

    before = sandbox.model_dump(mode="json")

    SecureExecutor().execute(
        admission,
        plan,
        sandbox,
        now=admission.admitted_at,
    )

    assert sandbox.model_dump(mode="json") == before


def test_same_inputs_produce_same_substantive_result() -> None:
    """Equal inputs should produce the same substantive outcome."""
    admission = make_admission()
    plan = make_plan()
    sandbox = make_sandbox()

    executor = SecureExecutor()

    first = executor.execute(
        admission,
        plan,
        sandbox,
        now=admission.admitted_at,
    )
    second = executor.execute(
        admission,
        plan,
        sandbox,
        now=admission.admitted_at,
    )

    assert first.status is second.status
    assert first.execution_id == second.execution_id
    assert first.request_id == second.request_id
    assert first.exit_code == second.exit_code


def test_checkpoint_failure_is_not_silently_ignored() -> None:
    """Checkpoint creation errors must surface to the caller."""
    admission = make_admission()
    execution_id = admission.execution_request.execution_id

    plan = make_plan(
        checkpoint_required=True,
        execution_id=execution_id,
    )
    sandbox = make_sandbox()

    checkpoint_manager = CheckpointManager()

    checkpoint_id = f"checkpoint:{execution_id}"

    checkpoint_manager.create(
        checkpoint_id=checkpoint_id,
        execution_id=execution_id,
        revision=1,
        state_ref="existing",
        metadata={},
        created_at=admission.admitted_at,
    )

    with pytest.raises(ValueError):
        SecureExecutor(
            checkpoint_manager=checkpoint_manager,
        ).execute(
            admission,
            plan,
            sandbox,
            now=admission.admitted_at,
        )


def test_expired_request_is_denied() -> None:
    """Execution must be rejected after request expiry."""
    now = datetime.now(UTC)

    admission = make_admission(
        requested_at=now - timedelta(minutes=5),
        expires_at=now - timedelta(seconds=1),
    )
    plan = make_plan(
        execution_id=admission.execution_request.execution_id,
    )
    sandbox = make_sandbox()

    result = SecureExecutor().execute(
        admission,
        plan,
        sandbox,
        now=now,
    )

    assert result.status is ExecutionStatus.DENIED
    assert "EXECUTION_REQUEST_EXPIRED" in (
        result.error_message or ""
    )


def test_executor_uses_exact_gateway_execution_request() -> None:
    """Executor must preserve Gateway-produced request identity."""
    admission = make_admission(
        principal_id="principal-001",
        capability_id="development.prepare",
        target_scope="lyrion/project/src",
    )
    plan = make_plan(
        execution_id=admission.execution_request.execution_id,
    )
    sandbox = make_sandbox()

    request = admission.execution_request

    result = SecureExecutor().execute(
        admission,
        plan,
        sandbox,
        now=admission.admitted_at,
    )

    assert result.execution_id == request.execution_id
    assert result.request_id == request.request_id
    assert request.principal_id == "principal-001"
    assert request.capability_id == "development.prepare"
    assert request.target_scope == "lyrion/project/src"


def test_execution_request_operation_is_preserved() -> None:
    """The execution request must retain the CapabilityRequest operation."""
    admission = make_admission(
        operation=CapabilityOperation.EXECUTE,
    )

    assert (
        admission.execution_request.operation
        == CapabilityOperation.EXECUTE.value
    )


def test_execution_request_principal_is_preserved() -> None:
    """The execution request must retain the authorized principal."""
    admission = make_admission(
        principal_id="principal-executor-test",
    )

    assert (
        admission.execution_request.principal_id
        == "principal-executor-test"
    )


def test_execution_request_risk_is_preserved() -> None:
    """The execution request must retain the authorized risk level."""
    admission = make_admission(
        risk_level=RiskLevel.LOW,
    )

    assert (
        admission.execution_request.risk_level
        is RiskLevel.LOW
    )


def test_execution_request_idempotency_is_preserved() -> None:
    """The execution request must retain the original idempotency key."""
    admission = make_admission(
        idempotency_key=IdempotencyKey(
            "idempotency-preserved-001",
        ),
    )

    assert (
        admission.execution_request.idempotency_key
        == IdempotencyKey("idempotency-preserved-001")
    )


def test_executor_remains_dry_run_only() -> None:
    """The current executor emits no external output reference."""
    admission = make_admission()
    plan = make_plan(
        execution_id=admission.execution_request.execution_id,
        command_ref="command-ref-that-must-not-run",
    )
    sandbox = make_sandbox()

    result = SecureExecutor().execute(
        admission,
        plan,
        sandbox,
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.COMPLETED
    assert result.output_ref is None
    assert result.error_code is None
