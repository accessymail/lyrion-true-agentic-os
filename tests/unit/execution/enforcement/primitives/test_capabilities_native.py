"""Native Linux capability reduction qualification tests."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from lyrion.core.types import ExecutionTarget
from lyrion.execution.backends.linux.enforcement.application import (
    EnforcementApplicationContext,
)
from lyrion.execution.backends.linux.enforcement.contracts import (
    LinuxEnforcementPlan,
)
from lyrion.execution.backends.linux.enforcement.planner import (
    LinuxEnforcementPlanner,
)
from lyrion.execution.backends.linux.enforcement.primitives.capabilities import (
    LibcCapabilityOperations,
)
from lyrion.execution.contracts import ResourceLimits
from lyrion.execution.sandbox import SandboxConfig

PROJECT_ROOT = Path(__file__).resolve().parents[5]


def _sandbox() -> SandboxConfig:
    return SandboxConfig(
        execution_target=ExecutionTarget.LOCAL_CPU,
        resource_limits=ResourceLimits(
            max_runtime_seconds=30.0,
            max_memory_mb=256,
            max_output_bytes=65536,
            max_cpu_seconds=30.0,
        ),
    )


def _plan() -> LinuxEnforcementPlan:
    return LinuxEnforcementPlanner().plan(_sandbox())


def _context() -> EnforcementApplicationContext:
    return EnforcementApplicationContext.create(
        execution_id="native-capability-child",
        backend_id="linux-native",
        started_at=datetime.now(UTC),
    )


def _run_native_child() -> subprocess.CompletedProcess[bytes]:
    code = f"""
import sys

sys.path.insert(0, {str(PROJECT_ROOT)!r})

from datetime import UTC, datetime
from pathlib import Path

from lyrion.execution.backends.linux.enforcement.application import (
    EnforcementApplicationContext,
)
from lyrion.execution.backends.linux.enforcement.contracts import (
    EnforcementState,
)
from lyrion.execution.backends.linux.enforcement.planner import (
    LinuxEnforcementPlanner,
)
from lyrion.execution.backends.linux.enforcement.primitives.capabilities import (
    CapabilityAdapter,
    LibcCapabilityOperations,
)
from lyrion.core.types import ExecutionTarget
from lyrion.execution.contracts import ResourceLimits
from lyrion.execution.sandbox import SandboxConfig


def read_proc_capabilities():
    fields = {{
        "CapEff": "effective",
        "CapPrm": "permitted",
        "CapInh": "inheritable",
        "CapBnd": "bounding",
        "CapAmb": "ambient",
    }}

    values = {{}}

    for line in Path("/proc/self/status").read_text(
        encoding="ascii"
    ).splitlines():
        name, separator, value = line.partition(":")
        if separator and name in fields:
            values[fields[name]] = int(value.strip(), 16)

    missing = set(fields.values()) - set(values)
    if missing:
        raise RuntimeError(
            f"missing /proc capability fields: {{sorted(missing)!r}}"
        )

    return values


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
    execution_id="native-capability-child",
    backend_id="linux-native",
    started_at=datetime.now(UTC),
)

operations = LibcCapabilityOperations()
adapter = CapabilityAdapter(operations)

before = read_proc_capabilities()

# The qualification environment is intentionally unprivileged.
# Effective and permitted capabilities are already empty.
if before["effective"] != 0:
    raise RuntimeError(
        f"unexpected initial CapEff={{before['effective']:016x}}"
    )

if before["permitted"] != 0:
    raise RuntimeError(
        f"unexpected initial CapPrm={{before['permitted']:016x}}"
    )

# Bounding must be non-empty so the native PR_CAPBSET_DROP path
# has an actual kernel state transition to qualify.
if before["bounding"] == 0:
    raise RuntimeError("unexpected empty initial bounding set")

applied = adapter.apply(context, plan)

# This VMware qualification process is intentionally unprivileged. Linux
# should reject PR_CAPBSET_DROP with EPERM. LYRION must fail closed.
if applied.success:
    raise RuntimeError(
        "unexpected capability reduction success in unprivileged child"
    )

if applied.state is not EnforcementState.FAILED:
    raise RuntimeError(
        "capability reduction failure did not produce FAILED state: "
        f"{{applied.state.value!r}}"
    )

if "capability reduction failed" not in applied.reason:
    raise RuntimeError(
        "unexpected capability failure reason: "
        f"{{applied.reason!r}}"
    )

# The failed operation must not claim successful verification.
verified = adapter.verify(context, plan)

if verified.success:
    raise RuntimeError(
        "verification unexpectedly succeeded after failed application"
    )

if verified.state is not EnforcementState.FAILED:
    raise RuntimeError(
        "verification did not fail closed: "
        f"{{verified.state.value!r}}"
    )

if verified.evidence:
    raise RuntimeError(
        "failed capability verification emitted security evidence"
    )

after = read_proc_capabilities()

# The failed bounding-set operation must not be represented as a completed
# enforcement transition. The child should retain its original bounding set.
if after["bounding"] != before["bounding"]:
    raise RuntimeError(
        "failed bounding-set operation unexpectedly changed state: "
        f"before={{before['bounding']:016x}} "
        f"after={{after['bounding']:016x}}"
    )

print(
    "PASS: native capability failure was correctly "
    "reported as FAILED",
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


def test_native_capability_bounding_failure_fails_closed() -> None:
    parent_operations = LibcCapabilityOperations()
    parent_before = parent_operations.get_state()

    assert parent_before.bounding

    result = _run_native_child()

    assert result.returncode == 0, (
        "native capability fail-closed qualification failed: "
        f"stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )

    assert (
        b"PASS: native capability failure was correctly "
        b"reported as FAILED"
        in result.stdout
    )

    parent_after = parent_operations.get_state()

    # Native capability operations are process-local. The qualification child
    # must not mutate the parent's capability state.
    assert parent_after.effective == parent_before.effective
    assert parent_after.permitted == parent_before.permitted
    assert parent_after.inheritable == parent_before.inheritable
    assert parent_after.bounding == parent_before.bounding
    assert parent_after.ambient == parent_before.ambient


def test_native_capability_child_starts_with_expected_unprivileged_state() -> None:
    code = """
from pathlib import Path


def read_capability_fields():
    fields = {
        "CapEff",
        "CapPrm",
        "CapInh",
        "CapBnd",
        "CapAmb",
    }

    values = {}

    for line in Path("/proc/self/status").read_text(
        encoding="ascii"
    ).splitlines():
        name, separator, value = line.partition(":")
        if separator and name in fields:
            values[name] = int(value.strip(), 16)

    return values


values = read_capability_fields()

required = {
    "CapEff",
    "CapPrm",
    "CapInh",
    "CapBnd",
    "CapAmb",
}

assert required.issubset(values)

# This qualification runs as an ordinary unprivileged user.
assert values["CapEff"] == 0
assert values["CapPrm"] == 0

# The environment must provide a bounding set for the reduction
# transition to be meaningfully exercised.
assert values["CapBnd"] != 0
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

    assert result.returncode == 0, (
        "native child initial capability state check failed: "
        f"stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
