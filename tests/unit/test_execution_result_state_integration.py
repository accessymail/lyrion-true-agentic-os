"""Real execution-result to state integration tests."""

from datetime import UTC, datetime, timedelta

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
    EventId,
    ExecutionTarget,
    IdempotencyKey,
    RiskLevel,
    TaskId,
)
from lyrion.events.models import EventSensitivity
from lyrion.execution.contracts import (
    ExecutionPlan,
    ExecutionResult,
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
from lyrion.state.execution_feedback import ExecutionFeedback
from lyrion.state.execution_state_projection import (
    ExecutionStateProjectionAdapter,
)
from lyrion.state.models import StateValueType


def make_request(
    *,
    execution_id: str = "execution:feedback:001",
    request_id: str = "request:feedback:001",
    admitted_at: datetime | None = None,
) -> CapabilityRequest:
    """Create a valid capability request."""
    now = admitted_at or datetime.now(UTC)

    return CapabilityRequest(
        request_id=request_id,
        decision_id=DecisionId(
            f"decision:{request_id}",
        ),
        task_id=TaskId(
            f"task:{request_id}",
        ),
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope="lyrion/project/src",
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        autonomy_level=AutonomyLevel.L1,
        risk_level=RiskLevel.LOW,
        policy_version="aegis-policy-v1",
        correlation_id=None,
        idempotency_key=IdempotencyKey(
            f"idem:{request_id}",
        ),
        requested_at=now,
        expires_at=now + timedelta(minutes=5),
        justification="Execution-to-state integration test.",
    )


def make_admission(
    *,
    admitted: bool = True,
    authorization_decision: AuthorizationDecision = (
        AuthorizationDecision.ALLOWED
    ),
    authorization_reason: str = "Authorized.",
    **request_overrides: object,
) -> ExecutionAdmission:
    """Create an execution admission."""
    request = make_request(
        execution_id=str(
            request_overrides.pop(
                "execution_id",
                "execution:feedback:001",
            )
        ),
        request_id=str(
            request_overrides.pop(
                "request_id",
                "request:feedback:001",
            )
        ),
        admitted_at=(
            request_overrides.pop(
                "admitted_at",
                None,
            )
        ),
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


def make_plan(
    request: CapabilityRequest,
    *,
    execution_id: str | None = None,
) -> ExecutionPlan:
    """Create an execution plan for one request."""
    return ExecutionPlan(
        execution_id=(
            execution_id
            or request.execution_id
        ),
        execution_target=ExecutionTarget.REMOTE_SANDBOX,
        command_ref=None,
        input_ref=None,
        output_ref=None,
        resource_limits=ResourceLimits(),
        network_access_allowed=False,
        external_side_effects_allowed=False,
        checkpoint_required=False,
    )


def make_sandbox() -> SandboxConfig:
    """Create a conservative sandbox."""
    return SandboxConfig(
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


def make_feedback(
    result: ExecutionResult,
    *,
    event_id: str,
) -> ExecutionFeedback:
    """Convert a real execution result into evidence feedback."""
    return ExecutionFeedback.from_execution_result(
        result,
        source_event_ids=(
            EventId(event_id),
        ),
    )


def project(
    feedback: ExecutionFeedback,
    *,
    now: datetime,
):
    """Project execution feedback into operational state."""
    return ExecutionStateProjectionAdapter().project(
        feedback,
        subject="lyri",
        now=now,
    )


def state_value(
    state: object,
) -> dict[str, object]:
    """Return the known object payload from a state record."""
    assert isinstance(state, dict)
    return state


def test_real_secure_execution_projects_completed_state() -> None:
    """A real completed execution becomes a state record."""
    now = datetime.now(UTC)

    admission = make_admission(
        execution_id="execution:integration:completed",
        request_id="request:integration:completed",
        admitted_at=now,
    )

    request = admission.execution_request

    result = SecureExecutor().execute(
        admission,
        make_plan(request),
        make_sandbox(),
        now=now,
    )

    assert result.status is ExecutionStatus.COMPLETED
    assert result.execution_id == request.execution_id
    assert result.request_id == request.request_id

    feedback = make_feedback(
        result,
        event_id="event:request:integration:completed",
    )

    state = project(
        feedback,
        now=now,
    )

    assert state.key == "execution_outcome"
    assert state.value_type is StateValueType.OBJECT
    assert state.evidence_refs == (
        EventId(
            "event:request:integration:completed",
        ),
    )

    value = state_value(state.value)

    assert value["execution_id"] == request.execution_id
    assert value["request_id"] == request.request_id
    assert value["status"] == "COMPLETED"


def test_real_denied_execution_projects_denied_state() -> None:
    """A real authorization denial becomes factual state evidence."""
    now = datetime.now(UTC)

    admission = make_admission(
        admitted=False,
        authorization_decision=AuthorizationDecision.DENIED,
        authorization_reason="Policy denied integration test.",
        execution_id="execution:integration:denied",
        request_id="request:integration:denied",
        admitted_at=now,
    )

    request = admission.execution_request

    result = SecureExecutor().execute(
        admission,
        make_plan(request),
        make_sandbox(),
        now=now,
    )

    assert result.status is ExecutionStatus.DENIED
    assert result.execution_id == request.execution_id
    assert result.request_id == request.request_id
    assert result.error_code == "EXECUTION_DENIED"

    feedback = make_feedback(
        result,
        event_id="event:request:integration:denied",
    )

    state = project(
        feedback,
        now=now,
    )

    value = state_value(state.value)

    assert value["status"] == "DENIED"
    assert value["error_code"] == "EXECUTION_DENIED"


def test_real_validation_failure_preserves_detailed_reason() -> None:
    """A validation failure remains distinguishable in feedback."""
    now = datetime.now(UTC)

    admission = make_admission(
        execution_id="execution:integration:mismatch",
        request_id="request:integration:mismatch",
        admitted_at=now,
    )

    request = admission.execution_request

    result = SecureExecutor().execute(
        admission,
        make_plan(
            request,
            execution_id="execution:integration:wrong",
        ),
        make_sandbox(),
        now=now,
    )

    assert result.status is ExecutionStatus.DENIED
    assert result.error_code == "EXECUTION_DENIED"
    assert result.error_message is not None
    assert "EXECUTION_ID_MISMATCH" in (
        result.error_message
    )

    feedback = make_feedback(
        result,
        event_id="event:request:integration:mismatch",
    )

    state = project(
        feedback,
        now=now,
    )

    value = state_value(state.value)

    assert value["status"] == "DENIED"
    assert value["error_code"] == "EXECUTION_DENIED"
    assert value["error_code"] == feedback.error_code


def test_execution_identity_survives_full_feedback_pipeline() -> None:
    """Execution identity survives execution, feedback, and projection."""
    now = datetime.now(UTC)

    admission = make_admission(
        execution_id="execution:integration:identity",
        request_id="request:integration:identity",
        admitted_at=now,
    )

    request = admission.execution_request

    result = SecureExecutor().execute(
        admission,
        make_plan(request),
        make_sandbox(),
        now=now,
    )

    feedback = make_feedback(
        result,
        event_id="event:request:integration:identity",
    )

    state = project(
        feedback,
        now=now,
    )

    value = state_value(state.value)

    assert result.execution_id == feedback.execution_id
    assert feedback.execution_id == value["execution_id"]

    assert result.request_id == feedback.request_id
    assert feedback.request_id == value["request_id"]


def test_state_projection_preserves_event_provenance() -> None:
    """The original event remains the evidence reference."""
    now = datetime.now(UTC)

    admission = make_admission(
        execution_id="execution:integration:provenance",
        request_id="request:integration:provenance",
        admitted_at=now,
    )

    request = admission.execution_request

    result = SecureExecutor().execute(
        admission,
        make_plan(request),
        make_sandbox(),
        now=now,
    )

    source_event_id = EventId(
        "event:integration:provenance",
    )

    feedback = make_feedback(
        result,
        event_id=str(source_event_id),
    )

    state = project(
        feedback,
        now=now,
    )

    assert state.evidence_refs == (
        source_event_id,
    )


def test_projection_cannot_turn_execution_outcome_into_authority() -> None:
    """Projected execution state contains no authorization grant."""
    now = datetime.now(UTC)

    admission = make_admission(
        execution_id="execution:integration:authority",
        request_id="request:integration:authority",
        admitted_at=now,
    )

    request = admission.execution_request

    result = SecureExecutor().execute(
        admission,
        make_plan(request),
        make_sandbox(),
        now=now,
    )

    feedback = make_feedback(
        result,
        event_id="event:integration:authority",
    )

    state = project(
        feedback,
        now=now,
    )

    value = state_value(state.value)

    assert state.key == "execution_outcome"
    assert "authorization" not in value
    assert "granted" not in value
    assert "capability_allowed" not in value
