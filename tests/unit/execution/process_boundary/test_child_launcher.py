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
from lyrion.execution.process_boundary.child_launcher import (
    ChildLauncher,
    ChildLaunchError,
)
from lyrion.execution.process_boundary.supervisor import ProcessLaunchSpec
from lyrion.execution.sandbox import (
    FilesystemMode,
    NetworkMode,
    SandboxConfig,
)


def _handoff(tmp_path: Path) -> LaunchHandoff:
    launch = ProcessLaunchSpec(
        execution_id="exec-child-launch-001",
        argv=("python3", "-c", "print('qualified')"),
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
        execution_id="exec-child-launch-001",
        request_id="req-child-launch-001",
        backend_id="linux-native",
        policy_version="policy-v1",
        authorization_reference="auth-child-launch-001",
        launch_spec=launch,
        enforcement_plan=plan,
    )


def test_qualify_uses_a_real_separate_child_process(
    tmp_path: Path,
) -> None:
    launcher = ChildLauncher()
    result = launcher.qualify(_handoff(tmp_path))

    assert result.succeeded
    assert result.parent_pid > 0
    assert result.child_pid > 0
    assert result.parent_pid != result.child_pid
    assert result.child_returncode == 0
    assert result.handoff_bytes > 0


def test_qualify_transfers_integrity_bound_handoff(
    tmp_path: Path,
) -> None:
    handoff = _handoff(tmp_path)

    result = ChildLauncher().qualify(handoff)

    assert result.succeeded
    assert result.handoff_bytes == len(
        handoff.model_dump_json().encode("utf-8")
    )


def test_qualify_rejects_oversized_handoff(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ChildLaunchError,
        match="serialized handoff exceeds configured maximum",
    ):
        ChildLauncher(max_handoff_bytes=1).qualify(
            _handoff(tmp_path),
        )


def test_launcher_rejects_invalid_limits() -> None:
    with pytest.raises(ValueError):
        ChildLauncher(max_handoff_bytes=0)

    with pytest.raises(ValueError):
        ChildLauncher(timeout_seconds=0)


def test_child_entry_module_is_fixed() -> None:
    launcher = ChildLauncher()

    assert launcher.max_handoff_bytes > 0
    assert launcher.timeout_seconds > 0
