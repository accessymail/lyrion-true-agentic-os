"""Real SecureExecutor integration tests for the Linux enforcement gate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

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
from lyrion.execution.backends.linux.enforcement.application import (
    EnforcementApplicationContext,
    EnforcementApplicationResult,
    EnforcementApplicationStatus,
    EnforcementEvidence,
    EnforcementPrimitiveResult,
)
from lyrion.execution.backends.linux.enforcement.contracts import (
    EnforcementPrimitive,
    EnforcementState,
    LinuxEnforcementPlan,
)
from lyrion.execution.backends.linux.enforcement.planner import (
    LinuxEnforcementPlanner,
)
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


def make_admission(
    *,
    execution_id: str = "execution:r33b2:001",
    request_id: str = "request:r33b2:001",
    admitted: bool = True,
    authorization_decision: AuthorizationDecision = (
        AuthorizationDecision.ALLOWED
    ),
    authorization_reason: str = "Authorized.",
    risk_level: RiskLevel = RiskLevel.LOW,
) -> ExecutionAdmission:
    """Create a deterministic execution admission."""
    now = datetime.now(UTC)

    request = CapabilityRequest(
        request_id=request_id,
        decision_id=DecisionId(f"decision:{request_id}"),
        task_id=TaskId(f"task:{request_id}"),
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope="lyrion/project/src",
        operation=CapabilityOperation.EXECUTE,
        data_classification=EventSensitivity.INTERNAL,
        autonomy_level=AutonomyLevel.L1,
        risk_level=risk_level,
        policy_version="aegis-policy-v1",
        correlation_id=None,
        idempotency_key=IdempotencyKey(f"idem:{request_id}"),
        requested_at=now,
        expires_at=now + timedelta(minutes=5),
        justification="R3.3-B.2 SecureExecutor integration test.",
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
        evaluated_at=now,
        expires_at=request.expires_at,
    )

    return ExecutionAdmission.from_authorization(
        request,
        authorization,
        admitted_at=now,
    )


def make_plan(
    admission: ExecutionAdmission,
    *,
    execution_id: str | None = None,
) -> ExecutionPlan:
    """Create a deterministic dry-run execution plan."""
    request = admission.execution_request

    return ExecutionPlan(
        execution_id=execution_id or request.execution_id,
        execution_target=ExecutionTarget.REMOTE_SANDBOX,
        command_ref="r33b2-controlled-command",
        input_ref=None,
        output_ref=None,
        resource_limits=ResourceLimits(),
        network_access_allowed=False,
        external_side_effects_allowed=False,
        checkpoint_required=False,
    )


def make_sandbox(
    **overrides: Any,
) -> SandboxConfig:
    """Create a conservative strict sandbox."""
    sandbox = SandboxConfig(
        execution_target=ExecutionTarget.REMOTE_SANDBOX,
        filesystem_mode=FilesystemMode.ISOLATED,
        network_mode=NetworkMode.DISABLED,
        environment_mode=EnvironmentMode.EMPTY,
        isolation_level=IsolationLevel.STRICT,
        writable_paths=(),
        read_only_paths=(),
        allowed_environment_keys=(),
        resource_limits=ResourceLimits(),
        allow_process_creation=False,
        allow_privileged_operations=False,
    )

    if not overrides:
        return sandbox

    return sandbox.model_copy(update=overrides)


def make_verified_result(
    plan: LinuxEnforcementPlan,
    context: EnforcementApplicationContext,
) -> EnforcementApplicationResult:
    """Create a deterministic aggregate VERIFIED result."""
    results = tuple(
        _verified_primitive(requirement.primitive)
        for requirement in plan.requirements
        if requirement.required
    )

    return EnforcementApplicationResult(
        execution_id=context.execution_id,
        backend_id=context.backend_id,
        status=EnforcementApplicationStatus.VERIFIED,
        primitive_results=results,
    )


def _verified_primitive(
    primitive: EnforcementPrimitive,
) -> EnforcementPrimitiveResult:
    """Build a valid primitive VERIFIED result."""
    evidence = EnforcementEvidence.verified(
        primitive=primitive,
        evidence_type="integration-test",
        observation="Deterministic integration-test verification.",
    )

    return EnforcementPrimitiveResult(
        primitive=primitive,
        required=True,
        state=EnforcementState.VERIFIED,
        success=True,
        reason="Verified by deterministic integration test.",
        evidence=(evidence,),
    )


class RecordingPlanner(LinuxEnforcementPlanner):
    """Planner spy that records the exact sandbox object."""

    def __init__(self) -> None:
        self.sandboxes: list[SandboxConfig] = []

    def plan(
        self,
        sandbox: SandboxConfig,
    ) -> LinuxEnforcementPlan:
        self.sandboxes.append(sandbox)
        return super().plan(sandbox)


class FakeEnforcementApplication:
    """Deterministic enforcement application test double."""

    def __init__(
        self,
        *,
        status: EnforcementApplicationStatus,
        failure_reason: str | None = None,
        raise_error: Exception | None = None,
        backend_id: str = "linux-native",
    ) -> None:
        self.status = status
        self.failure_reason = failure_reason
        self.raise_error = raise_error
        self.backend_id = backend_id
        self.calls: list[
            tuple[LinuxEnforcementPlan, EnforcementApplicationContext]
        ] = []

    def apply(
        self,
        plan: LinuxEnforcementPlan,
        context: EnforcementApplicationContext,
    ) -> EnforcementApplicationResult:
        self.calls.append((plan, context))

        if self.raise_error is not None:
            raise self.raise_error

        if self.status is EnforcementApplicationStatus.VERIFIED:
            result = make_verified_result(plan, context)

            if self.backend_id == context.backend_id:
                return result

            return result.model_copy(
                update={
                    "backend_id": self.backend_id,
                }
            )

        return EnforcementApplicationResult(
            execution_id=context.execution_id,
            backend_id=self.backend_id,
            status=self.status,
            primitive_results=(),
            failure_reason=self.failure_reason
            or f"Enforcement returned {self.status.value}.",
        )


def build_executor(
    application: FakeEnforcementApplication,
    planner: RecordingPlanner | None = None,
) -> tuple[SecureExecutor, RecordingPlanner]:
    """Construct SecureExecutor with deterministic enforcement."""
    resolved_planner = planner or RecordingPlanner()

    return (
        SecureExecutor(
            enforcement_planner=resolved_planner,
            enforcement_application=application,
        ),
        resolved_planner,
    )


def test_verified_enforcement_allows_existing_dry_run() -> None:
    """VERIFIED enforcement permits the existing dry-run runtime path."""
    admission = make_admission()
    application = FakeEnforcementApplication(
        status=EnforcementApplicationStatus.VERIFIED,
    )

    executor, planner = build_executor(application)

    result = executor.execute(
        admission,
        make_plan(admission),
        make_sandbox(),
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.COMPLETED
    assert len(application.calls) == 1
    assert len(planner.sandboxes) == 1


def test_verified_enforcement_receives_exact_sandbox() -> None:
    """The exact SandboxConfig object must reach the planner."""
    admission = make_admission()
    sandbox = make_sandbox(
        writable_paths=(),
        read_only_paths=(),
    )
    application = FakeEnforcementApplication(
        status=EnforcementApplicationStatus.VERIFIED,
    )

    executor, planner = build_executor(application)

    result = executor.execute(
        admission,
        make_plan(admission),
        sandbox,
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.COMPLETED
    assert planner.sandboxes == [sandbox]


def test_enforcement_context_preserves_execution_identity() -> None:
    """Enforcement must receive the Gateway execution identity."""
    admission = make_admission(
        execution_id="execution:r33b2:identity",
        request_id="request:r33b2:identity",
    )
    application = FakeEnforcementApplication(
        status=EnforcementApplicationStatus.VERIFIED,
    )

    executor, _ = build_executor(application)

    result = executor.execute(
        admission,
        make_plan(admission),
        make_sandbox(),
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.COMPLETED
    assert len(application.calls) == 1

    _, context = application.calls[0]

    assert context.execution_id == admission.execution_request.execution_id
    assert context.backend_id == "linux-native"
    assert dict(context.metadata)["request_id"] == (
        admission.execution_request.request_id
    )


@pytest.mark.parametrize(
    "status",
    [
        EnforcementApplicationStatus.FAILED,
        EnforcementApplicationStatus.ABORTED,
    ],
)
def test_failed_or_aborted_enforcement_blocks_runtime(
    status: EnforcementApplicationStatus,
) -> None:
    """Failed or aborted enforcement must prevent runtime entry."""
    admission = make_admission()
    application = FakeEnforcementApplication(
        status=status,
        failure_reason=f"Controlled {status.value} result.",
    )

    executor, _ = build_executor(application)

    result = executor.execute(
        admission,
        make_plan(admission),
        make_sandbox(),
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.FAILED
    assert result.error_code == "ENFORCEMENT_REJECTED"
    assert result.exit_code is None
    assert result.output_ref is None
    assert "Controlled" in (result.error_message or "")


def test_applied_enforcement_is_not_sufficient() -> None:
    """APPLIED without VERIFIED must never cross the execution boundary."""
    admission = make_admission()
    application = FakeEnforcementApplication(
        status=EnforcementApplicationStatus.FAILED,
        failure_reason="Enforcement remains APPLIED and is not verified.",
    )

    executor, _ = build_executor(application)

    result = executor.execute(
        admission,
        make_plan(admission),
        make_sandbox(),
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.FAILED
    assert result.error_code == "ENFORCEMENT_REJECTED"
    assert result.exit_code is None


def test_enforcement_exception_fails_closed() -> None:
    """Unexpected enforcement errors must block execution."""
    admission = make_admission()
    application = FakeEnforcementApplication(
        status=EnforcementApplicationStatus.FAILED,
        raise_error=RuntimeError("controlled enforcement failure"),
    )

    executor, _ = build_executor(application)

    result = executor.execute(
        admission,
        make_plan(admission),
        make_sandbox(),
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.FAILED
    assert result.error_code == "ENFORCEMENT_REJECTED"
    assert "controlled enforcement failure" in (
        result.error_message or ""
    )


def test_enforcement_identity_mismatch_fails_closed() -> None:
    """An enforcement backend identity mismatch must block execution."""
    admission = make_admission()
    application = FakeEnforcementApplication(
        status=EnforcementApplicationStatus.VERIFIED,
        backend_id="unexpected-backend",
    )

    executor, _ = build_executor(application)

    result = executor.execute(
        admission,
        make_plan(admission),
        make_sandbox(),
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.FAILED
    assert result.error_code == "ENFORCEMENT_REJECTED"
    assert "backend identity mismatch" in (
        result.error_message or ""
    )


def test_denied_admission_does_not_invoke_enforcement() -> None:
    """Authorization denial must stop before enforcement."""
    admission = make_admission(
        admitted=False,
        authorization_decision=AuthorizationDecision.DENIED,
        authorization_reason="Denied before enforcement.",
    )
    application = FakeEnforcementApplication(
        status=EnforcementApplicationStatus.VERIFIED,
    )

    executor, planner = build_executor(application)

    result = executor.execute(
        admission,
        make_plan(admission),
        make_sandbox(),
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.DENIED
    assert application.calls == []
    assert planner.sandboxes == []


def test_validation_failure_does_not_invoke_enforcement() -> None:
    """Execution validation failure must stop before enforcement."""
    admission = make_admission()
    application = FakeEnforcementApplication(
        status=EnforcementApplicationStatus.VERIFIED,
    )

    executor, planner = build_executor(application)

    result = executor.execute(
        admission,
        make_plan(
            admission,
            execution_id="execution:r33b2:mismatch",
        ),
        make_sandbox(),
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.DENIED
    assert application.calls == []
    assert planner.sandboxes == []


def test_sandbox_failure_does_not_invoke_enforcement() -> None:
    """Sandbox policy failure must stop before enforcement."""
    admission = make_admission()
    application = FakeEnforcementApplication(
        status=EnforcementApplicationStatus.VERIFIED,
    )

    executor, planner = build_executor(application)

    result = executor.execute(
        admission,
        make_plan(admission),
        make_sandbox(
            execution_target=ExecutionTarget.CLOUD_GPU,
        ),
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.DENIED
    assert application.calls == []
    assert planner.sandboxes == []


def test_enforcement_events_are_audited() -> None:
    """Successful enforcement must leave explicit audit evidence."""
    from lyrion.observability.execution_audit import ExecutionAuditLog

    admission = make_admission()
    application = FakeEnforcementApplication(
        status=EnforcementApplicationStatus.VERIFIED,
    )
    audit = ExecutionAuditLog()

    executor = SecureExecutor(
        audit_log=audit,
        enforcement_planner=RecordingPlanner(),
        enforcement_application=application,
    )

    result = executor.execute(
        admission,
        make_plan(admission),
        make_sandbox(),
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

    assert "ENFORCEMENT_VERIFIED" in event_types
    assert "EXECUTION_STARTED" in event_types
    assert "EXECUTION_COMPLETED" in event_types


def test_enforcement_rejection_is_audited() -> None:
    """Rejected enforcement must leave failure evidence."""
    from lyrion.observability.execution_audit import ExecutionAuditLog

    admission = make_admission()
    application = FakeEnforcementApplication(
        status=EnforcementApplicationStatus.FAILED,
        failure_reason="Controlled enforcement rejection.",
    )
    audit = ExecutionAuditLog()

    executor = SecureExecutor(
        audit_log=audit,
        enforcement_planner=RecordingPlanner(),
        enforcement_application=application,
    )

    result = executor.execute(
        admission,
        make_plan(admission),
        make_sandbox(),
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.FAILED

    events = audit.events_for(
        admission.execution_request.execution_id,
    )

    event_types = [
        event.event_type
        for event in events
    ]

    assert "ENFORCEMENT_REJECTED" in event_types
    assert "EXECUTION_STARTED" not in event_types
    assert "EXECUTION_COMPLETED" not in event_types


def test_enforcement_is_not_an_authorization_interface() -> None:
    """The injected enforcement object exposes no authorization API."""
    application = FakeEnforcementApplication(
        status=EnforcementApplicationStatus.VERIFIED,
    )

    assert not hasattr(application, "authorize")
    assert not hasattr(application, "grant")
    assert not hasattr(application, "admit")


def test_existing_no_enforcement_compatibility_path_remains_dry_run() -> None:
    """Existing construction remains the controlled dry-run path."""
    admission = make_admission()

    result = SecureExecutor().execute(
        admission,
        make_plan(admission),
        make_sandbox(),
        now=admission.admitted_at,
    )

    assert result.status is ExecutionStatus.COMPLETED
    assert result.exit_code == 0
    assert result.output_ref is None
