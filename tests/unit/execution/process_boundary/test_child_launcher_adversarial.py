from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from lyrion.core.types import ExecutionTarget
from lyrion.execution.backends.linux.enforcement.planner import (
    LinuxEnforcementPlanner,
)
from lyrion.execution.contracts import ResourceLimits
from lyrion.execution.process_boundary.bootstrap_contracts import LaunchHandoff
from lyrion.execution.process_boundary.child_entry import (
    ChildEntryError,
    read_handoff,
)
from lyrion.execution.process_boundary.child_launcher import (
    CHILD_ENTRY_MODULE,
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
        execution_id="exec-adversarial-001",
        argv=("python3", "-c", "print('qualification')"),
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
        execution_id="exec-adversarial-001",
        request_id="req-adversarial-001",
        backend_id="linux-native",
        policy_version="policy-v1",
        authorization_reference="auth-adversarial-001",
        launch_spec=launch,
        enforcement_plan=plan,
    )


def _child_command(
    read_fd: int,
    max_bytes: int = 256 * 1024,
) -> tuple[str, ...]:
    return (
        sys.executable,
        "-m",
        CHILD_ENTRY_MODULE,
        "--handoff-fd",
        str(read_fd),
        "--max-handoff-bytes",
        str(max_bytes),
    )


def _run_child(
    payload: bytes,
    *,
    max_bytes: int = 256 * 1024,
) -> subprocess.CompletedProcess[bytes]:
    read_fd, write_fd = os.pipe()

    try:
        child = subprocess.Popen(
            _child_command(read_fd, max_bytes),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            close_fds=True,
            pass_fds=(read_fd,),
            cwd=os.getcwd(),
            env=dict(os.environ),
        )

        os.close(read_fd)
        read_fd = -1

        try:
            os.write(write_fd, payload)
        finally:
            os.close(write_fd)
            write_fd = -1

        try:
            stdout, stderr = child.communicate(
                timeout=5.0,
            )
        except subprocess.TimeoutExpired as exc:
            child.kill()
            stdout, stderr = child.communicate()
            raise AssertionError(
                "child-entry adversarial test timed out"
            ) from exc

        return subprocess.CompletedProcess(
            child.args,
            child.returncode,
            stdout,
            stderr,
        )
    finally:
        if read_fd >= 0:
            os.close(read_fd)

        if write_fd >= 0:
            os.close(write_fd)


def test_valid_handoff_reaches_child_bootstrap(
    tmp_path: Path,
) -> None:
    result = ChildLauncher().qualify(
        _handoff(tmp_path),
    )

    assert result.succeeded
    assert result.parent_pid != result.child_pid


def test_tampered_handoff_is_rejected_by_child(
    tmp_path: Path,
) -> None:
    payload = json.loads(
        _handoff(tmp_path).model_dump_json(),
    )

    payload["execution_id"] = "tampered-execution"

    result = _run_child(
        json.dumps(payload).encode("utf-8"),
    )

    assert result.returncode != 0


def test_malformed_json_is_rejected_by_child() -> None:
    result = _run_child(b"{not-valid-json")

    assert result.returncode != 0


def test_empty_payload_is_rejected_by_child() -> None:
    result = _run_child(b"")

    assert result.returncode != 0


def test_oversized_payload_is_rejected_by_child(
    tmp_path: Path,
) -> None:
    payload = _handoff(tmp_path).model_dump_json().encode("utf-8")

    result = _run_child(
        payload,
        max_bytes=len(payload) - 1,
    )

    assert result.returncode != 0


def test_invalid_fd_is_rejected_by_child() -> None:
    command = (
        sys.executable,
        "-m",
        CHILD_ENTRY_MODULE,
        "--handoff-fd",
        "-1",
        "--max-handoff-bytes",
        "4096",
    )

    result = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        shell=False,
        check=False,
        cwd=os.getcwd(),
        env=dict(os.environ),
    )

    assert result.returncode != 0


def test_nonpositive_read_limit_is_rejected() -> None:
    with pytest.raises(ChildEntryError):
        read_handoff(
            stream=io.BytesIO(b"{}"),
            max_bytes=0,
        )


def test_launcher_timeout_is_reported(
    tmp_path: Path,
) -> None:
    launcher = ChildLauncher(
        timeout_seconds=0.000001,
    )

    with pytest.raises(ChildLaunchError):
        launcher.qualify(_handoff(tmp_path))
