from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from lyrion.execution.backends.linux.enforcement.primitives.no_new_privs import (
    LibcNoNewPrivsOperations,
)

PROJECT_ROOT = Path(__file__).resolve().parents[5]


def _run_native_child() -> subprocess.CompletedProcess[bytes]:
    code = f"""
import sys
from datetime import UTC, datetime

sys.path.insert(0, {str(PROJECT_ROOT)!r})

from lyrion.execution.backends.linux.enforcement.application import (
    EnforcementApplicationContext,
)
from lyrion.execution.backends.linux.enforcement.contracts import (
    EnforcementState,
)
from lyrion.execution.backends.linux.enforcement.planner import (
    LinuxEnforcementPlanner,
)
from lyrion.execution.backends.linux.enforcement.primitives.no_new_privs import (
    LibcNoNewPrivsOperations,
    NoNewPrivsAdapter,
)
from lyrion.execution.sandbox import (
    ExecutionTarget,
    ResourceLimits,
    SandboxConfig,
)


sandbox = SandboxConfig(
    execution_target=ExecutionTarget.LOCAL_CPU,
    resource_limits=ResourceLimits(
        max_runtime_seconds=30.0,
        max_memory_mb=256,
        max_output_bytes=65536,
        max_cpu_seconds=30.0,
    ),
)

plan = LinuxEnforcementPlanner().plan(sandbox)

context = EnforcementApplicationContext.create(
    execution_id="native-no-new-privs-child",
    backend_id="linux-native",
    started_at=datetime.now(UTC),
)

operations = LibcNoNewPrivsOperations()
adapter = NoNewPrivsAdapter(operations)

before = operations.get_no_new_privs()

if before:
    raise RuntimeError(
        "child unexpectedly started with no_new_privs=1"
    )

applied = adapter.apply(context, plan)

if not applied.success:
    raise RuntimeError(
        f"apply failed: {{applied.reason}}"
    )

if applied.state is not EnforcementState.APPLIED:
    raise RuntimeError(
        f"apply state={{applied.state.value!r}}"
    )

verified = adapter.verify(context, plan)

if not verified.success:
    raise RuntimeError(
        f"verification failed: {{verified.reason}}"
    )

if verified.state is not EnforcementState.VERIFIED:
    raise RuntimeError(
        f"verification state={{verified.state.value!r}}"
    )

if not operations.get_no_new_privs():
    raise RuntimeError(
        "kernel state is not no_new_privs=1"
    )

if len(verified.evidence) != 1:
    raise RuntimeError(
        "expected exactly one verification evidence record"
    )

print(
    "PASS: native no_new_privs applied and independently verified",
    flush=True,
)
"""

    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        shell=False,
        check=False,
        env=dict(os.environ),
        timeout=10.0,
    )


def test_native_no_new_privs_is_applied_inside_child_only() -> None:
    parent_operations = LibcNoNewPrivsOperations()

    assert parent_operations.get_no_new_privs() is False

    result = _run_native_child()

    assert result.returncode == 0, (
        "native child qualification failed: "
        f"stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )

    assert (
        b"PASS: native no_new_privs applied and independently verified"
        in result.stdout
    )

    assert parent_operations.get_no_new_privs() is False


def test_native_no_new_privs_child_starts_unmodified() -> None:
    code = """
from lyrion.execution.backends.linux.enforcement.primitives.no_new_privs import (
    LibcNoNewPrivsOperations,
)

operations = LibcNoNewPrivsOperations()

assert operations.get_no_new_privs() is False
"""

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        shell=False,
        check=False,
        env=dict(os.environ),
        timeout=10.0,
    )

    assert result.returncode == 0
