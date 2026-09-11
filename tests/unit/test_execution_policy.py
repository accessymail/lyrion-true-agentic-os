"""Adversarial tests for the execution policy boundary."""

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
from lyrion.execution.policy import (
    ExecutionPolicy,
    ExecutionPolicyEvaluator,
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
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)

    values: dict[str, object] = {
        "execution_id": "exec_policy_001",
        "request_id": "request_policy_001",
        "task_id": TaskId("task_policy_001"),
        "capability_id": "development.prepare",
        "target_scope": "lyrion/project/src",
        "operation": "READ",
        "authorization_reference": "auth_policy_001",
        "policy_version": "aegis-policy-v1",
        "principal_id": "lyrion-piae",
        "autonomy_level": AutonomyLevel.L1,
        "risk_level": RiskLevel.LOW,
        "resource_limits": make_limits(),
        "network_access_allowed": False,
        "external_side_effects_allowed": False,
        "checkpoint_ref": None,
        "idempotency_key": IdempotencyKey(
            "idem_policy_001",
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
        "execution_id": "exec_policy_001",
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


def test_default_policy_is_conservative() -> None:
    """The default policy must restrict execution privileges."""
    policy = ExecutionPolicy()

    assert ExecutionTarget.LOCAL_CPU in policy.allowed_targets
    assert ExecutionTarget.REMOTE_SANDBOX in policy.allowed_targets
    assert ExecutionTarget.CLOUD_GPU not in policy.allowed_targets
    assert policy.allow_network_access is False
    assert policy.allow_external_side_effects is False
    assert policy.max_risk_level is RiskLevel.LOW


def test_valid_request_and_plan_are_allowed() -> None:
    """Requests within platform limits should be allowed."""
    request = make_request()
    plan = make_plan()

    assert ExecutionPolicyEvaluator().is_allowed(
        request,
        plan,
        ExecutionPolicy(),
    )


def test_runtime_limit_is_enforced() -> None:
    """Requests above the runtime ceiling must be rejected."""
    request = make_request(
        resource_limits=make_limits(
            max_runtime_seconds=31.0,
        ),
    )
    plan = make_plan(
        resource_limits=make_limits(
            max_runtime_seconds=31.0,
        ),
    )

    reasons = ExecutionPolicyEvaluator().failure_reasons(
        request,
        plan,
        ExecutionPolicy(
            max_runtime_seconds=30.0,
        ),
    )

    assert "MAX_RUNTIME_EXCEEDED" in reasons


def test_memory_limit_is_enforced() -> None:
    """Requests above the memory ceiling must be rejected."""
    request = make_request(
        resource_limits=make_limits(
            max_memory_mb=513,
        ),
    )
    plan = make_plan(
        resource_limits=make_limits(
            max_memory_mb=513,
        ),
    )

    reasons = ExecutionPolicyEvaluator().failure_reasons(
        request,
        plan,
        ExecutionPolicy(
            max_memory_mb=512,
        ),
    )

    assert "MAX_MEMORY_EXCEEDED" in reasons


def test_output_limit_is_enforced() -> None:
    """Requests above the output ceiling must be rejected."""
    request = make_request(
        resource_limits=make_limits(
            max_output_bytes=1_048_577,
        ),
    )
    plan = make_plan(
        resource_limits=make_limits(
            max_output_bytes=1_048_577,
        ),
    )

    reasons = ExecutionPolicyEvaluator().failure_reasons(
        request,
        plan,
        ExecutionPolicy(
            max_output_bytes=1_048_576,
        ),
    )

    assert "MAX_OUTPUT_EXCEEDED" in reasons


def test_cpu_limit_is_enforced() -> None:
    """Requests above the CPU ceiling must be rejected."""
    request = make_request(
        resource_limits=make_limits(
            max_cpu_seconds=31.0,
        ),
    )
    plan = make_plan(
        resource_limits=make_limits(
            max_cpu_seconds=31.0,
        ),
    )

    reasons = ExecutionPolicyEvaluator().failure_reasons(
        request,
        plan,
        ExecutionPolicy(
            max_cpu_seconds=30.0,
        ),
    )

    assert "MAX_CPU_EXCEEDED" in reasons


def test_network_is_denied_by_default() -> None:
    """Network permission is denied unless explicitly enabled."""
    request = make_request(
        network_access_allowed=True,
    )
    plan = make_plan(
        network_access_allowed=True,
    )

    reasons = ExecutionPolicyEvaluator().failure_reasons(
        request,
        plan,
        ExecutionPolicy(),
    )

    assert "NETWORK_ACCESS_NOT_PERMITTED" in reasons


def test_network_can_be_enabled_by_platform_policy() -> None:
    """Network access is allowed when platform policy permits it."""
    request = make_request(
        network_access_allowed=True,
    )
    plan = make_plan(
        network_access_allowed=True,
    )

    policy = ExecutionPolicy(
        allow_network_access=True,
    )

    assert ExecutionPolicyEvaluator().is_allowed(
        request,
        plan,
        policy,
    )


def test_external_side_effects_are_denied_by_default() -> None:
    """External side effects remain disabled by default."""
    request = make_request(
        external_side_effects_allowed=True,
    )
    plan = make_plan(
        external_side_effects_allowed=True,
    )

    reasons = ExecutionPolicyEvaluator().failure_reasons(
        request,
        plan,
        ExecutionPolicy(),
    )

    assert "EXTERNAL_SIDE_EFFECTS_NOT_PERMITTED" in reasons


def test_external_side_effects_can_be_enabled_by_policy() -> None:
    """Platform policy may explicitly authorize side effects."""
    request = make_request(
        external_side_effects_allowed=True,
    )
    plan = make_plan(
        external_side_effects_allowed=True,
    )

    policy = ExecutionPolicy(
        allow_external_side_effects=True,
    )

    assert ExecutionPolicyEvaluator().is_allowed(
        request,
        plan,
        policy,
    )


def test_risk_ceiling_is_enforced() -> None:
    """Requests above the platform risk ceiling are rejected."""
    request = make_request(
        risk_level=RiskLevel.MEDIUM,
    )
    plan = make_plan()

    reasons = ExecutionPolicyEvaluator().failure_reasons(
        request,
        plan,
        ExecutionPolicy(
            max_risk_level=RiskLevel.LOW,
        ),
    )

    assert "RISK_LEVEL_NOT_PERMITTED" in reasons


def test_equal_risk_ceiling_is_allowed() -> None:
    """A request at the configured risk ceiling should pass."""
    request = make_request(
        risk_level=RiskLevel.MEDIUM,
    )
    plan = make_plan()

    policy = ExecutionPolicy(
        max_risk_level=RiskLevel.MEDIUM,
    )

    assert ExecutionPolicyEvaluator().is_allowed(
        request,
        plan,
        policy,
    )


def test_execution_target_is_enforced() -> None:
    """Targets outside the platform allowlist are rejected."""
    request = make_request()
    plan = make_plan(
        execution_target=ExecutionTarget.CLOUD_GPU,
    )

    reasons = ExecutionPolicyEvaluator().failure_reasons(
        request,
        plan,
        ExecutionPolicy(),
    )

    assert "EXECUTION_TARGET_NOT_PERMITTED" in reasons


def test_local_cpu_target_is_allowed() -> None:
    """An explicitly allowed target should pass."""
    request = make_request()
    plan = make_plan(
        execution_target=ExecutionTarget.LOCAL_CPU,
    )

    assert ExecutionPolicyEvaluator().is_allowed(
        request,
        plan,
        ExecutionPolicy(),
    )


def test_remote_sandbox_target_is_allowed() -> None:
    """The initial remote sandbox target is explicitly allowed."""
    request = make_request()
    plan = make_plan(
        execution_target=ExecutionTarget.REMOTE_SANDBOX,
    )

    assert ExecutionPolicyEvaluator().is_allowed(
        request,
        plan,
        ExecutionPolicy(),
    )


def test_plan_policy_is_checked_independently() -> None:
    """Plan privileges cannot bypass the platform policy."""
    request = make_request()

    plan = ExecutionPlan(
        execution_id=request.execution_id,
        execution_target=ExecutionTarget.LOCAL_CPU,
        resource_limits=make_limits(),
        network_access_allowed=True,
        external_side_effects_allowed=False,
    )

    policy = ExecutionPolicy(
        allow_network_access=False,
    )

    reasons = ExecutionPolicyEvaluator().evaluate_plan(
        plan,
        policy,
    )

    assert "NETWORK_ACCESS_NOT_PERMITTED" in reasons


def test_require_allowed_fails_closed() -> None:
    """Rejected policy evaluation must raise PermissionError."""
    request = make_request(
        risk_level=RiskLevel.HIGH,
    )
    plan = make_plan()

    with pytest.raises(
        PermissionError,
        match="execution policy rejected",
    ):
        ExecutionPolicyEvaluator().require_allowed(
            request,
            plan,
            ExecutionPolicy(),
        )


def test_failure_reasons_are_deterministic() -> None:
    """Equivalent inputs should produce identical violations."""
    request = make_request(
        resource_limits=make_limits(
            max_runtime_seconds=60.0,
        ),
        network_access_allowed=True,
    )

    plan = make_plan(
        resource_limits=make_limits(
            max_runtime_seconds=60.0,
        ),
        network_access_allowed=True,
        execution_target=ExecutionTarget.CLOUD_GPU,
    )

    evaluator = ExecutionPolicyEvaluator()
    policy = ExecutionPolicy()

    first = evaluator.failure_reasons(
        request,
        plan,
        policy,
    )
    second = evaluator.failure_reasons(
        request,
        plan,
        policy,
    )

    assert first == second


def test_policy_does_not_modify_request_or_plan() -> None:
    """Policy evaluation must remain observational."""
    request = make_request()
    plan = make_plan()

    before_request = request.model_dump(mode="json")
    before_plan = plan.model_dump(mode="json")

    ExecutionPolicyEvaluator().is_allowed(
        request,
        plan,
        ExecutionPolicy(),
    )

    assert request.model_dump(mode="json") == before_request
    assert plan.model_dump(mode="json") == before_plan
