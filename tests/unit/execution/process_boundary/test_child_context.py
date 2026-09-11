from __future__ import annotations

from pathlib import Path

import pytest

from lyrion.core.types import ExecutionTarget
from lyrion.execution.backends.linux.enforcement.planner import (
    LinuxEnforcementPlanner,
)
from lyrion.execution.contracts import ResourceLimits
from lyrion.execution.process_boundary.bootstrap_contracts import (
    LaunchHandoff,
)
from lyrion.execution.process_boundary.child_context import (
    ChildContextError,
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
        execution_id="exec-child-001",
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
        execution_id="exec-child-001",
        request_id="req-child-001",
        backend_id="linux-native",
        policy_version="policy-v1",
        authorization_reference="auth-child-001",
        launch_spec=launch,
        enforcement_plan=plan,
    )


def test_create_binds_current_process_identity(tmp_path: Path) -> None:
    handoff = _handoff(tmp_path)

    context = ChildExecutionContext.create(handoff)

    assert context.handoff is handoff
    assert context.pid > 0
    assert context.pgid > 0


def test_create_rejects_blank_execution_identity(
    tmp_path: Path,
) -> None:
    handoff = _handoff(tmp_path)

    object.__setattr__(
        handoff,
        "execution_id",
        "   ",
    )

    with pytest.raises(ChildContextError):
        ChildExecutionContext.create(handoff)


def test_verify_current_process_accepts_original_identity(
    tmp_path: Path,
) -> None:
    context = ChildExecutionContext.create(_handoff(tmp_path))

    context.verify_current_process()


def test_verify_current_process_rejects_pid_mismatch(
    tmp_path: Path,
) -> None:
    context = ChildExecutionContext.create(_handoff(tmp_path))

    mismatched = ChildExecutionContext(
        handoff=context.handoff,
        pid=context.pid + 1,
        pgid=context.pgid,
    )

    with pytest.raises(ChildContextError, match="PID mismatch"):
        mismatched.verify_current_process()


def test_verify_current_process_rejects_pgid_mismatch(
    tmp_path: Path,
) -> None:
    context = ChildExecutionContext.create(_handoff(tmp_path))

    mismatched = ChildExecutionContext(
        handoff=context.handoff,
        pid=context.pid,
        pgid=context.pgid + 1,
    )

    with pytest.raises(ChildContextError, match="PGID mismatch"):
        mismatched.verify_current_process()


def test_verify_current_process_rejects_blank_handoff_identity(
    tmp_path: Path,
) -> None:
    context = ChildExecutionContext.create(_handoff(tmp_path))

    object.__setattr__(
        context.handoff,
        "execution_id",
        "   ",
    )

    with pytest.raises(ChildContextError, match="execution_id"):
        context.verify_current_process()


def test_verify_handoff_accepts_valid_integrity(
    tmp_path: Path,
) -> None:
    context = ChildExecutionContext.create(_handoff(tmp_path))

    context.verify_handoff()


def test_verify_handoff_rejects_tampered_integrity(
    tmp_path: Path,
) -> None:
    handoff = _handoff(tmp_path)

    tampered = handoff.model_copy(
        update={
            "integrity_sha256": "0" * 64,
        }
    )

    context = ChildExecutionContext.create(tampered)

    with pytest.raises(
        ChildContextError,
        match="handoff integrity verification failed",
    ):
        context.verify_handoff()


def test_context_is_immutable(tmp_path: Path) -> None:
    context = ChildExecutionContext.create(_handoff(tmp_path))

    with pytest.raises(AttributeError):
        context.pid = context.pid + 1  # type: ignore[misc]


def test_context_uses_authorized_execution_identity(
    tmp_path: Path,
) -> None:
    handoff = _handoff(tmp_path)

    context = ChildExecutionContext.create(handoff)

    assert context.handoff.execution_id == "exec-child-001"
    assert context.handoff.request_id == "req-child-001"
    assert context.handoff.authorization_reference == "auth-child-001"


def test_verify_current_process_revalidates_process_group(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = ChildExecutionContext.create(_handoff(tmp_path))

    original_getpgid = __import__(
        "os",
    ).getpgid

    def mismatched_getpgid(pid: int) -> int:
        if pid == context.pid:
            return context.pgid + 1
        return original_getpgid(pid)

    monkeypatch.setattr(
        "lyrion.execution.process_boundary.child_context.os.getpgid",
        mismatched_getpgid,
    )

    with pytest.raises(ChildContextError, match="PGID mismatch"):
        context.verify_current_process()
