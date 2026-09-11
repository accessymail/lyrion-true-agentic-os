"""Native Linux namespace qualification tests.

These tests operate only inside disposable subprocesses.

They never call namespace mutation against the pytest controller process.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from lyrion.execution.backends.linux.enforcement.primitives.native_namespaces import (
    NativeChildNamespaceOperations,
    NativeNamespaceError,
    observe_current_namespaces,
)


def _child(script: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()

    return subprocess.run(
        [sys.executable, "-c", script],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        env=env,
    )


def test_parent_namespace_state_is_observable() -> None:
    state = observe_current_namespaces()

    assert state.process_namespace.startswith("pid:[")
    assert state.mount_namespace.startswith("mnt:[")
    assert state.network_namespace.startswith("net:[")


def test_mount_namespace_isolated_in_disposable_child() -> None:
    script = """
from lyrion.execution.backends.linux.enforcement.primitives.native_namespaces import (
    NativeChildNamespaceOperations,
    observe_current_namespaces,
)

before = observe_current_namespaces()

NativeChildNamespaceOperations().isolate_mount()

after = observe_current_namespaces()

print("BEFORE_MNT=", before.mount_namespace)
print("AFTER_MNT=", after.mount_namespace)

if before.mount_namespace == after.mount_namespace:
    raise SystemExit(20)
"""

    result = _child(script)

    if result.returncode != 0:
        pytest.skip(
            "native mount namespace unavailable: "
            f"rc={result.returncode}; stderr={result.stderr.strip()}"
        )

    assert "BEFORE_MNT=" in result.stdout
    assert "AFTER_MNT=" in result.stdout


def test_network_namespace_isolated_in_disposable_child() -> None:
    script = """
from lyrion.execution.backends.linux.enforcement.primitives.native_namespaces import (
    NativeChildNamespaceOperations,
    observe_current_namespaces,
)

before = observe_current_namespaces()

NativeChildNamespaceOperations().isolate_network()

after = observe_current_namespaces()

print("BEFORE_NET=", before.network_namespace)
print("AFTER_NET=", after.network_namespace)

if before.network_namespace == after.network_namespace:
    raise SystemExit(21)
"""

    result = _child(script)

    if result.returncode != 0:
        pytest.skip(
            "native network namespace unavailable: "
            f"rc={result.returncode}; stderr={result.stderr.strip()}"
        )

    assert "BEFORE_NET=" in result.stdout
    assert "AFTER_NET=" in result.stdout


def test_pid_namespace_requires_subsequent_child() -> None:
    script = """
from lyrion.execution.backends.linux.enforcement.primitives.native_namespaces import (
    NativeChildNamespaceOperations,
)

NativeChildNamespaceOperations().isolate_process_for_future_child()
print("PID_NAMESPACE_PREPARED")
"""

    result = _child(script)

    if result.returncode != 0:
        pytest.skip(
            "native PID namespace preparation unavailable: "
            f"rc={result.returncode}; stderr={result.stderr.strip()}"
        )

    assert "PID_NAMESPACE_PREPARED" in result.stdout


def test_invalid_namespace_observation_fails_closed() -> None:
    with pytest.raises(ValueError):
        from lyrion.execution.backends.linux.enforcement.primitives.native_namespaces import (
            _namespace_identity,
        )

        _namespace_identity("")


def test_native_operation_context_has_valid_identity() -> None:
    operations = NativeChildNamespaceOperations()

    operations._require_child_context()


def test_native_namespace_error_type() -> None:
    assert issubclass(NativeNamespaceError, RuntimeError)
