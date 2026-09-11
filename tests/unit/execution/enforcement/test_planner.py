"""Adversarial tests for Linux enforcement planning."""

import pytest

from lyrion.core.types import ExecutionTarget
from lyrion.execution.backends.linux.enforcement import (
    EnforcementPlanStatus,
    EnforcementPrimitive,
    EnforcementState,
    LinuxEnforcementPlanner,
)
from lyrion.execution.contracts import ResourceLimits
from lyrion.execution.sandbox import (
    EnvironmentMode,
    FilesystemMode,
    IsolationLevel,
    NetworkMode,
    SandboxConfig,
    SandboxPath,
)


def make_sandbox(
    *,
    isolation_level: IsolationLevel = IsolationLevel.STRICT,
    filesystem_mode: FilesystemMode = FilesystemMode.ISOLATED,
    network_mode: NetworkMode = NetworkMode.DISABLED,
) -> SandboxConfig:
    """Build a conservative sandbox configuration."""
    return SandboxConfig(
        execution_target=ExecutionTarget.LOCAL_CPU,
        filesystem_mode=filesystem_mode,
        network_mode=network_mode,
        environment_mode=EnvironmentMode.EMPTY,
        isolation_level=isolation_level,
        resource_limits=ResourceLimits(
            max_runtime_seconds=30.0,
            max_memory_mb=512,
            max_output_bytes=1_048_576,
            max_cpu_seconds=30.0,
        ),
    )


def test_strict_plan_requires_all_strict_controls() -> None:
    """Strict isolation must plan every required security primitive."""
    plan = LinuxEnforcementPlanner().plan(make_sandbox())

    assert plan.status is EnforcementPlanStatus.READY
    assert plan.seccomp.required
    assert plan.landlock.required
    assert plan.apparmor.required

    assert set(plan.required_primitives()) == set(EnforcementPrimitive)
    assert all(
        requirement.state is EnforcementState.PLANNED
        for requirement in plan.requirements
    )


def test_plan_is_immutable() -> None:
    """Security plans must not be mutable after construction."""
    plan = LinuxEnforcementPlanner().plan(make_sandbox())

    with pytest.raises((TypeError, ValueError)):
        plan.status = EnforcementPlanStatus.REJECTED  # type: ignore[misc]


def test_plan_never_claims_applied_or_verified() -> None:
    """C1 must not manufacture evidence of applied controls."""
    plan = LinuxEnforcementPlanner().plan(make_sandbox())

    plan.assert_planning_only()

    assert not any(
        requirement.state
        in {
            EnforcementState.APPLIED,
            EnforcementState.VERIFIED,
        }
        for requirement in plan.requirements
    )


def test_resource_limits_are_preserved() -> None:
    """Resource limits must pass through without weakening."""
    plan = LinuxEnforcementPlanner().plan(make_sandbox())

    assert plan.cgroups.max_runtime_seconds == 30.0
    assert plan.cgroups.max_memory_mb == 512
    assert plan.cgroups.max_output_bytes == 1_048_576
    assert plan.cgroups.max_cpu_seconds == 30.0


def test_filesystem_paths_are_preserved() -> None:
    """Sandbox filesystem boundaries must be represented exactly."""
    sandbox = SandboxConfig(
        execution_target=ExecutionTarget.LOCAL_CPU,
        filesystem_mode=FilesystemMode.ISOLATED,
        network_mode=NetworkMode.DISABLED,
        environment_mode=EnvironmentMode.EMPTY,
        isolation_level=IsolationLevel.STRICT,
        writable_paths=(SandboxPath(path="/tmp/work", read_only=False),),
        read_only_paths=(SandboxPath(path="/usr", read_only=True),),
        resource_limits=ResourceLimits(
            max_runtime_seconds=30.0,
            max_memory_mb=512,
            max_output_bytes=1_048_576,
            max_cpu_seconds=30.0,
        ),
    )

    plan = LinuxEnforcementPlanner().plan(sandbox)

    assert plan.filesystem.writable_paths == ("/tmp/work",)
    assert plan.filesystem.read_only_paths == ("/usr",)


def test_minimal_isolation_does_not_require_strict_controls() -> None:
    """Minimal isolation must not silently acquire strict-only controls."""
    plan = LinuxEnforcementPlanner().plan(
        make_sandbox(
            isolation_level=IsolationLevel.MINIMAL,
            filesystem_mode=FilesystemMode.READ_ONLY,
            network_mode=NetworkMode.DISABLED,
        )
    )

    assert not plan.namespaces.required
    assert not plan.seccomp.required
    assert not plan.landlock.required
    assert not plan.apparmor.required


def test_enabled_network_is_not_planned_as_network_isolation() -> None:
    """An explicitly enabled network must not be falsely represented as isolated."""
    sandbox = make_sandbox(
        isolation_level=IsolationLevel.STANDARD,
        network_mode=NetworkMode.ENABLED,
    )

    plan = LinuxEnforcementPlanner().plan(sandbox)

    assert not plan.network.required
    assert not plan.network.network_access_allowed


def test_invalid_sandbox_is_rejected_before_planning() -> None:
    """Invalid sandbox configurations must never reach enforcement planning."""
    with pytest.raises(ValueError):
        SandboxConfig(
            execution_target=ExecutionTarget.LOCAL_CPU,
            filesystem_mode=FilesystemMode.ISOLATED,
            network_mode=NetworkMode.DISABLED,
            environment_mode=EnvironmentMode.EMPTY,
            isolation_level=IsolationLevel.STRICT,
            resource_limits=ResourceLimits(
                max_runtime_seconds=30.0,
                max_memory_mb=512,
                max_output_bytes=1_048_576,
                max_cpu_seconds=30.0,
            ),
            allow_privileged_operations=True,
        )


def test_rejected_plan_is_explicitly_failed_closed() -> None:
    """Rejected plans must contain explicit failed requirements."""
    plan = LinuxEnforcementPlanner().plan(make_sandbox())
    rejected = plan.rejected(
        make_sandbox(),
        "host enforcement prerequisites unavailable",
    )

    assert rejected.status is EnforcementPlanStatus.REJECTED
    assert rejected.has_failed_requirements()
    assert all(
        requirement.state is EnforcementState.FAILED
        for requirement in rejected.requirements
    )
