"""Adversarial validation tests for the PB-DOC-005 Agent Harness."""

from datetime import UTC, datetime, timedelta

from lyrion.agent_harness import AgentHarness, AgentIdentity
from lyrion.capabilities.contracts import (
    AuthorizationDecision,
    CapabilityOperation,
    CapabilityRequest,
)
from lyrion.capabilities.gateway import CapabilityGateway, ExecutionAdmission
from lyrion.core.types import AutonomyLevel, DecisionId, IdempotencyKey, RiskLevel, TaskId
from lyrion.events.models import EventSensitivity
from lyrion.execution.executor import SecureExecutor
from lyrion.security.authorization import AegisAuthorizationService
from lyrion.security.guards import AuthorizationGuard
from lyrion.security.policy import AegisPolicyEvaluator
from lyrion.security.replay import ReplayGuard
from lyrion.security.rules import default_aegis_policy
from lyrion.tasks.models import Task, TaskStatus


def make_context() -> tuple[AgentHarness, Task, CapabilityRequest, ExecutionAdmission]:
    now = datetime.now(UTC)
    task_id = TaskId("task:agent-harness:validation")
    request = CapabilityRequest(
        request_id="request:agent-harness:validation",
        decision_id=DecisionId("decision:agent-harness:validation"),
        task_id=task_id,
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope="lyrion/project/src",
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        autonomy_level=AutonomyLevel.L1,
        risk_level=RiskLevel.LOW,
        policy_version="aegis-policy-v1",
        idempotency_key=IdempotencyKey("idem:agent-harness:validation"),
        requested_at=now,
        expires_at=now + timedelta(minutes=5),
        justification="PB-DOC-005 validation.",
    )
    policy = default_aegis_policy()
    gateway = CapabilityGateway(
        AegisAuthorizationService(
            AegisPolicyEvaluator(policy),
            AuthorizationGuard(policy.policy_version),
            ReplayGuard(),
        )
    )
    authority = gateway.authorization_service.authorize(request, now=now)
    admission = ExecutionAdmission.from_authorization(
        request,
        authority,
        admitted_at=now,
    )
    task = Task(
        task_id=task_id,
        objective="PB-DOC-005 validation",
        status=TaskStatus.RUNNING,
        autonomy_level=AutonomyLevel.L2,
        risk_level=RiskLevel.LOW,
        created_at=now,
        updated_at=now,
    )
    return AgentHarness(secure_executor=SecureExecutor()), task, request, admission


def make_binding(
    harness: AgentHarness,
    task: Task,
    request: CapabilityRequest,
    admission: ExecutionAdmission,
):
    authority = harness.secure_executor  # keep fixture ownership explicit
    del authority
    # The admission's identity dimensions are already authoritative for this fixture.
    from lyrion.capabilities.contracts import AuthorizationResult

    execution_request = admission.execution_request
    now = execution_request.requested_at
    result = AuthorizationResult(
        request_id=request.request_id,
        decision=AuthorizationDecision.ALLOWED,
        granted=True,
        principal_id=request.principal_id,
        capability_id=request.capability_id,
        target_scope=request.target_scope,
        policy_version=request.policy_version,
        reason="fixture authorization",
        evaluated_at=now,
        expires_at=now + timedelta(minutes=5),
    )
    return harness.bind(
        identity=AgentIdentity(
            agent_id="agent:validation",
            identity_provenance_ref="registry:agent:validation:v1",
        ),
        task=task,
        authority_context=result,
        capability_context=request,
        execution_admission=admission,
        provenance_context="test:pb-doc-005:validation",
    )


def test_task_mismatch_fails_closed() -> None:
    harness, task, request, admission = make_context()
    binding = make_binding(harness, task, request, admission)
    other_task = task.model_copy(update={"task_id": TaskId("task:other")})

    result = harness.validate(binding, task=other_task, now=request.requested_at)

    assert result.valid is False
    assert result.failure_reason == "TASK_MISMATCH"


def test_denied_authority_fails_closed() -> None:
    harness, task, request, admission = make_context()
    binding = make_binding(harness, task, request, admission)
    denied = binding.model_copy(
        update={
            "authority_context": binding.authority_context.model_copy(
                update={
                    "decision": AuthorizationDecision.DENIED,
                    "granted": False,
                }
            )
        }
    )

    result = harness.validate(denied, task=task, now=request.requested_at)

    assert result.valid is False
    assert result.failure_reason == "AUTHORITY_MISSING"


def test_expired_authority_fails_closed() -> None:
    harness, task, request, admission = make_context()
    binding = make_binding(harness, task, request, admission)
    expired = binding.authority_context.model_copy(
        update={"expires_at": request.requested_at - timedelta(seconds=1)}
    )
    binding = binding.model_copy(update={"authority_context": expired})

    result = harness.validate(binding, task=task, now=request.requested_at)

    assert result.valid is False
    assert result.failure_reason == "AUTHORITY_EXPIRED"


def test_capability_mismatch_fails_closed() -> None:
    harness, task, request, admission = make_context()
    binding = make_binding(harness, task, request, admission)
    mismatched = binding.model_copy(
        update={
            "capability_context": request.model_copy(
                update={"capability_id": "development.other"}
            )
        }
    )

    result = harness.validate(mismatched, task=task, now=request.requested_at)

    assert result.valid is False
    assert result.failure_reason == "AUTHORITY_INVALID"


def test_isolation_mismatch_fails_closed() -> None:
    harness, task, request, admission = make_context()
    binding = make_binding(harness, task, request, admission)

    isolated = binding.model_copy(
        update={
            "isolation_contract": binding.isolation_contract.model_copy(
                update={"task_id": "task:other"},
            ),
        }
    )

    result = harness.validate(
        isolated,
        task=task,
        now=request.requested_at,
    )

    assert result.valid is False
    assert result.failure_reason == "ISOLATION_INVALID"


def test_isolation_boundary_cannot_be_disabled() -> None:
    harness, task, request, admission = make_context()
    binding = make_binding(harness, task, request, admission)

    isolated = binding.model_copy(
        update={
            "isolation_contract": binding.isolation_contract.model_copy(
                update={"sandbox_isolated": False},
            ),
        }
    )

    result = harness.validate(
        isolated,
        task=task,
        now=request.requested_at,
    )

    assert result.valid is False
    assert result.failure_reason == "ISOLATION_INVALID"


def test_non_running_task_fails_closed() -> None:
    harness, task, request, admission = make_context()
    binding = make_binding(harness, task, request, admission)
    paused = task.model_copy(update={"status": TaskStatus.PAUSED})

    result = harness.validate(binding, task=paused, now=request.requested_at)

    assert result.valid is False
    assert result.failure_reason == "LIFECYCLE_INVALID"


def test_harness_has_no_authority_creation_api() -> None:
    harness, _, _, _ = make_context()

    forbidden = {
        "authorize",
        "grant_capability",
        "create_admission",
        "execute_privileged",
        "bypass_security",
    }

    assert forbidden.isdisjoint(dir(harness))
