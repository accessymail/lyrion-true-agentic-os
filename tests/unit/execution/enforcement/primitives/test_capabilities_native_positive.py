"""Controlled positive native Linux capability qualification.

The positive transition is executed only when the current process already
possesses CAP_SETPCAP (capability 8) in its effective set.

This test never:
- acquires privileges
- invokes sudo
- modifies persistent host configuration
- adds capabilities
- changes another process
- weakens the LYRION capability policy

The child process performs the capability reduction against its own process
state and independently verifies the resulting kernel state.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]


def _run_authorized_child() -> subprocess.CompletedProcess[str]:
    """Run the native transition in a separate child process."""
    child_code = textwrap.dedent(
        """
        from datetime import UTC, datetime

        from lyrion.core.types import ExecutionTarget
        from lyrion.execution.backends.linux.enforcement.application import (
            EnforcementApplicationContext,
        )
        from lyrion.execution.backends.linux.enforcement.planner import (
            LinuxEnforcementPlanner,
        )
        from lyrion.execution.backends.linux.enforcement.primitives.capabilities import (
            CapabilityAdapter,
            LibcCapabilityOperations,
        )
        from lyrion.execution.contracts import ResourceLimits
        from lyrion.execution.sandbox import SandboxConfig

        def read_proc_capabilities() -> dict[str, str]:
            required = {
                "CapInh",
                "CapPrm",
                "CapEff",
                "CapBnd",
                "CapAmb",
            }

            fields: dict[str, str] = {}

            with open("/proc/self/status", encoding="utf-8") as status:
                for line in status:
                    key, separator, value = line.partition(":")
                    if separator and key in required:
                        fields[key] = value.strip()

            if set(fields) != required:
                raise RuntimeError(
                    "incomplete /proc capability state: "
                    f"{fields}"
                )

            return fields

        def mask(value: str) -> int:
            return int(value, 16)

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

        if not plan.privilege.capability_reduction_required:
            raise RuntimeError(
                "qualification plan does not require capability reduction"
            )

        operations = LibcCapabilityOperations()
        before = operations.get_state()

        if not before.bounding:
            print(
                "SKIP: child has no bounding capabilities",
                flush=True,
            )
            raise SystemExit(77)

        # PR_CAPBSET_DROP requires CAP_SETPCAP in the effective set.
        if 8 not in before.effective:
            print(
                "SKIP: CAP_SETPCAP is not effective in qualification child",
                flush=True,
            )
            raise SystemExit(77)

        context = EnforcementApplicationContext.create(
            execution_id="native-capability-positive-qualification",
            backend_id="linux-native-qualification",
            started_at=datetime.now(UTC),
        )

        adapter = CapabilityAdapter(operations=operations)

        result = adapter.apply(context, plan)

        print(f"APPLY_STATE={result.state.value}", flush=True)
        print(f"APPLY_SUCCESS={result.success}", flush=True)

        if not result.success:
            raise RuntimeError(
                "authorized native capability reduction failed: "
                f"{result.reason}"
            )

        if result.state.value != "APPLIED":
            raise RuntimeError(
                "native apply returned unexpected state: "
                f"{result.state.value}"
            )

        after_apply = operations.get_state()

        if after_apply.effective:
            raise RuntimeError(
                "effective capabilities remain after reduction"
            )

        if after_apply.permitted:
            raise RuntimeError(
                "permitted capabilities remain after reduction"
            )

        if after_apply.inheritable:
            raise RuntimeError(
                "inheritable capabilities remain after reduction"
            )

        if after_apply.bounding:
            raise RuntimeError(
                "bounding capabilities remain after reduction"
            )

        if after_apply.ambient:
            raise RuntimeError(
                "ambient capabilities remain after reduction"
            )

        verification = adapter.verify(context, plan)

        print(
            f"VERIFY_STATE={verification.state.value}",
            flush=True,
        )
        print(
            f"VERIFY_SUCCESS={verification.success}",
            flush=True,
        )

        if not verification.success:
            raise RuntimeError(
                "native capability verification failed: "
                f"{verification.reason}"
            )

        if verification.state.value != "VERIFIED":
            raise RuntimeError(
                "native verification returned unexpected state: "
                f"{verification.state.value}"
            )

        # Independent kernel verification. This intentionally bypasses the
        # adapter's state-reading implementation.
        fields = read_proc_capabilities()

        for key, value in fields.items():
            if mask(value) != 0:
                raise RuntimeError(
                    f"independent kernel verification found "
                    f"{key}={value}"
                )

        print(
            "PASS: positive native capability reduction qualified",
            flush=True,
        )
        """
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")

    return subprocess.run(
        [sys.executable, "-c", child_code],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_authorized_positive_native_capability_transition() -> None:
    """Qualify the native transition only in an already-authorized context."""
    if os.environ.get("LYRION_NATIVE_CAPABILITY_POSITIVE") != "1":
        pytest.skip(
            "positive native capability qualification is not explicitly enabled"
        )

    result = _run_authorized_child()

    if result.returncode == 77:
        pytest.skip(result.stdout.strip() or "authorized capability context unavailable")

    assert result.returncode == 0, (
        "positive native capability qualification failed\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    assert "APPLY_STATE=APPLIED" in result.stdout
    assert "APPLY_SUCCESS=True" in result.stdout
    assert "VERIFY_STATE=VERIFIED" in result.stdout
    assert "VERIFY_SUCCESS=True" in result.stdout
    assert "PASS: positive native capability reduction qualified" in (
        result.stdout
    )
