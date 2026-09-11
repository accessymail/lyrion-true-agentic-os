from __future__ import annotations

from pathlib import Path

import pytest

from lyrion.core.types import ExecutionTarget
from lyrion.execution.backends.linux.enforcement.planner import (
    LinuxEnforcementPlanner,
)
from lyrion.execution.contracts import ResourceLimits
from lyrion.execution.process_boundary.bootstrap import ChildBootstrap
from lyrion.execution.process_boundary.bootstrap_contracts import (
    BootstrapContractError,
    BootstrapState,
    LaunchHandoff,
)
from lyrion.execution.process_boundary.child_context import (
    ChildExecutionContext,
)
from lyrion.execution.process_boundary.supervisor import ProcessLaunchSpec
from lyrion.execution.sandbox import (
    FilesystemMode,
    NetworkMode,
    SandboxConfig,
)


def _handoff(tmp_path: Path) -> LaunchHandoff:
    launch = ProcessLaunchSpec(
        execution_id="exec-001",
        argv=("python3", "-c", "print('ok')"),
        cwd=tmp_path,
        environment={"PATH": "/usr/bin"},
        timeout_seconds=10.0,
        max_output_bytes=4096,
    )

    plan = LinuxEnforcementPlanner().plan(
        SandboxConfig(
            execution_target=ExecutionTarget.LOCAL_CPU,
            filesystem_mode=FilesystemMode.NONE,
            network_mode=NetworkMode.DISABLED,
            resource_limits=ResourceLimits(
                max_runtime_seconds=30.0,
                max_memory_mb=256,
                max_output_bytes=65536,
                max_cpu_seconds=30.0,
            ),
        )
    )

    return LaunchHandoff.from_components(
        execution_id="exec-001",
        request_id="req-001",
        backend_id="linux-native",
        policy_version="policy-v1",
        authorization_reference="auth-001",
        launch_spec=launch,
        enforcement_plan=plan,
    )


def _bound_bootstrap(tmp_path: Path) -> ChildBootstrap:
    handoff = _handoff(tmp_path)
    bootstrap = ChildBootstrap(handoff)

    bootstrap.bind_identity("exec-001")
    bootstrap.bind_process_context(
        ChildExecutionContext.create(handoff),
    )

    return bootstrap


def test_bootstrap_binds_process_context_and_validates(
    tmp_path: Path,
) -> None:
    bootstrap = _bound_bootstrap(tmp_path)

    context = bootstrap.validate_handoff()

    assert context.state is BootstrapState.HANDOFF_VALIDATED
    assert context.child_context is not None
    assert context.child_context.handoff is bootstrap.handoff
    assert context.child_context.pid > 0
    assert context.child_context.pgid > 0


def test_bootstrap_rejects_identity_mismatch(
    tmp_path: Path,
) -> None:
    bootstrap = ChildBootstrap(_handoff(tmp_path))

    with pytest.raises(BootstrapContractError):
        bootstrap.bind_identity("different-execution")

    assert bootstrap.state is BootstrapState.FAILED


def test_bootstrap_requires_process_context_before_handoff_validation(
    tmp_path: Path,
) -> None:
    bootstrap = ChildBootstrap(_handoff(tmp_path))

    bootstrap.bind_identity("exec-001")

    with pytest.raises(
        BootstrapContractError,
        match="child execution context must be bound",
    ):
        bootstrap.validate_handoff()

    assert bootstrap.state is BootstrapState.FAILED


def test_bootstrap_rejects_process_context_for_wrong_handoff(
    tmp_path: Path,
) -> None:
    first_handoff = _handoff(tmp_path)

    launch = ProcessLaunchSpec(
        execution_id="exec-002",
        argv=("python3", "-c", "print('ok')"),
        cwd=tmp_path,
        environment={"PATH": "/usr/bin"},
        timeout_seconds=10.0,
        max_output_bytes=4096,
    )

    plan = LinuxEnforcementPlanner().plan(
        SandboxConfig(
            execution_target=ExecutionTarget.LOCAL_CPU,
            filesystem_mode=FilesystemMode.NONE,
            network_mode=NetworkMode.DISABLED,
            resource_limits=ResourceLimits(
                max_runtime_seconds=30.0,
                max_memory_mb=256,
                max_output_bytes=65536,
                max_cpu_seconds=30.0,
            ),
        )
    )

    second_handoff = LaunchHandoff.from_components(
        execution_id="exec-002",
        request_id="req-002",
        backend_id="linux-native",
        policy_version="policy-v1",
        authorization_reference="auth-002",
        launch_spec=launch,
        enforcement_plan=plan,
    )

    bootstrap = ChildBootstrap(first_handoff)
    bootstrap.bind_identity("exec-001")

    wrong_context = ChildExecutionContext.create(second_handoff)

    with pytest.raises(
        BootstrapContractError,
        match="handoff does not match",
    ):
        bootstrap.bind_process_context(wrong_context)

    assert bootstrap.state is BootstrapState.FAILED


def test_bootstrap_rejects_tampered_process_context(
    tmp_path: Path,
) -> None:
    handoff = _handoff(tmp_path)
    bootstrap = ChildBootstrap(handoff)

    bootstrap.bind_identity("exec-001")

    tampered = handoff.model_copy(
        update={
            "integrity_sha256": "0" * 64,
        }
    )
    context = ChildExecutionContext.create(tampered)

    with pytest.raises(
        BootstrapContractError,
        match="handoff integrity verification failed",
    ):
        bootstrap.bind_process_context(context)

    assert bootstrap.state is BootstrapState.FAILED


def test_bootstrap_rejects_pid_mismatch_in_process_context(
    tmp_path: Path,
) -> None:
    handoff = _handoff(tmp_path)
    bootstrap = ChildBootstrap(handoff)

    bootstrap.bind_identity("exec-001")

    context = ChildExecutionContext.create(handoff)

    mismatched = ChildExecutionContext(
        handoff=context.handoff,
        pid=context.pid + 1,
        pgid=context.pgid,
    )

    with pytest.raises(
        BootstrapContractError,
        match="PID mismatch",
    ):
        bootstrap.bind_process_context(mismatched)

    assert bootstrap.state is BootstrapState.FAILED


def test_bootstrap_rejects_pgid_mismatch_in_process_context(
    tmp_path: Path,
) -> None:
    handoff = _handoff(tmp_path)
    bootstrap = ChildBootstrap(handoff)

    bootstrap.bind_identity("exec-001")

    context = ChildExecutionContext.create(handoff)

    mismatched = ChildExecutionContext(
        handoff=context.handoff,
        pid=context.pid,
        pgid=context.pgid + 1,
    )

    with pytest.raises(
        BootstrapContractError,
        match="PGID mismatch",
    ):
        bootstrap.bind_process_context(mismatched)

    assert bootstrap.state is BootstrapState.FAILED


def test_bootstrap_cannot_skip_states(tmp_path: Path) -> None:
    bootstrap = _bound_bootstrap(tmp_path)

    bootstrap.validate_handoff()

    with pytest.raises(BootstrapContractError):
        bootstrap.transition(BootstrapState.EXEC_READY)


def test_bootstrap_requires_verified_state_before_exec(
    tmp_path: Path,
) -> None:
    bootstrap = ChildBootstrap(_handoff(tmp_path))

    with pytest.raises(BootstrapContractError):
        bootstrap.require_exec_ready()


def test_bootstrap_rejects_identity_binding_after_failure(
    tmp_path: Path,
) -> None:
    bootstrap = ChildBootstrap(_handoff(tmp_path))

    bootstrap.fail("adversarial failure")

    with pytest.raises(BootstrapContractError):
        bootstrap.bind_identity("exec-001")

    assert bootstrap.state is BootstrapState.FAILED


def test_bootstrap_cannot_mark_exec_ready_without_full_sequence(
    tmp_path: Path,
) -> None:
    bootstrap = _bound_bootstrap(tmp_path)

    bootstrap.validate_handoff()

    required_sequence = [
        BootstrapState.RESOURCES_PREPARED,
        BootstrapState.NAMESPACES_PREPARED,
        BootstrapState.FILESYSTEM_NETWORK_PREPARED,
        BootstrapState.NO_NEW_PRIVS_APPLIED,
        BootstrapState.CAPABILITIES_REDUCED,
        BootstrapState.LANDLOCK_APPLIED,
        BootstrapState.SECCOMP_APPLIED,
        BootstrapState.ENFORCEMENT_VERIFIED,
    ]

    for state in required_sequence:
        bootstrap.transition(state)

    with pytest.raises(BootstrapContractError):
        bootstrap.require_exec_ready()

    assert bootstrap.state is BootstrapState.ENFORCEMENT_VERIFIED


def test_bootstrap_exec_ready_is_reached_only_after_verified_enforcement(
    tmp_path: Path,
) -> None:
    bootstrap = _bound_bootstrap(tmp_path)

    bootstrap.validate_handoff()

    for state in (
        BootstrapState.RESOURCES_PREPARED,
        BootstrapState.NAMESPACES_PREPARED,
        BootstrapState.FILESYSTEM_NETWORK_PREPARED,
        BootstrapState.NO_NEW_PRIVS_APPLIED,
        BootstrapState.CAPABILITIES_REDUCED,
        BootstrapState.LANDLOCK_APPLIED,
        BootstrapState.SECCOMP_APPLIED,
        BootstrapState.ENFORCEMENT_VERIFIED,
        BootstrapState.EXEC_READY,
    ):
        bootstrap.transition(state)

    bootstrap.require_exec_ready()

    assert bootstrap.state is BootstrapState.EXEC_READY
