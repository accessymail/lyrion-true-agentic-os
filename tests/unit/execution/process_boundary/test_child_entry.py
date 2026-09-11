from __future__ import annotations

import io
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
from lyrion.execution.process_boundary.child_entry import (
    ChildEntryError,
    establish_child_bootstrap,
    read_handoff,
)
from lyrion.execution.process_boundary.supervisor import ProcessLaunchSpec
from lyrion.execution.sandbox import (
    FilesystemMode,
    NetworkMode,
    SandboxConfig,
)


def _handoff(tmp_path: Path) -> LaunchHandoff:
    launch = ProcessLaunchSpec(
        execution_id="exec-entry-001",
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
        execution_id="exec-entry-001",
        request_id="req-entry-001",
        backend_id="linux-native",
        policy_version="policy-v1",
        authorization_reference="auth-entry-001",
        launch_spec=launch,
        enforcement_plan=plan,
    )


def test_read_handoff_accepts_valid_serialized_contract(
    tmp_path: Path,
) -> None:
    handoff = _handoff(tmp_path)

    result = read_handoff(
        io.BytesIO(handoff.model_dump_json().encode()),
    )

    assert result == handoff
    result.verify_integrity()


def test_read_handoff_rejects_empty_input() -> None:
    with pytest.raises(
        ChildEntryError,
        match="handoff is empty",
    ):
        read_handoff(io.BytesIO(b""))


def test_read_handoff_rejects_oversized_input(
    tmp_path: Path,
) -> None:
    handoff = _handoff(tmp_path)
    payload = handoff.model_dump_json().encode()

    with pytest.raises(
        ChildEntryError,
        match="exceeds maximum",
    ):
        read_handoff(
            io.BytesIO(payload),
            max_bytes=len(payload) - 1,
        )


def test_read_handoff_rejects_invalid_json() -> None:
    with pytest.raises(
        ChildEntryError,
        match="deserialization failed",
    ):
        read_handoff(io.BytesIO(b"{invalid-json"))


def test_read_handoff_rejects_tampered_integrity(
    tmp_path: Path,
) -> None:
    handoff = _handoff(tmp_path)

    tampered = handoff.model_copy(
        update={
            "integrity_sha256": "0" * 64,
        }
    )

    with pytest.raises(
        ChildEntryError,
        match="integrity verification failed",
    ):
        read_handoff(
            io.BytesIO(tampered.model_dump_json().encode()),
        )


def test_read_handoff_rejects_non_positive_limit(
    tmp_path: Path,
) -> None:
    handoff = _handoff(tmp_path)

    with pytest.raises(
        ChildEntryError,
        match="maximum handoff size",
    ):
        read_handoff(
            io.BytesIO(handoff.model_dump_json().encode()),
            max_bytes=0,
        )


def test_establish_child_bootstrap_creates_child_context(
    tmp_path: Path,
) -> None:
    handoff = _handoff(tmp_path)

    bootstrap = establish_child_bootstrap(handoff)

    assert bootstrap.state.value == "handoff_validated"
    assert bootstrap.child_context is not None
    assert bootstrap.child_context.handoff is handoff
    assert bootstrap.child_context.pid > 0
    assert bootstrap.child_context.pgid > 0


def test_establish_child_bootstrap_revalidates_context(
    tmp_path: Path,
) -> None:
    handoff = _handoff(tmp_path)

    bootstrap = establish_child_bootstrap(handoff)

    context = bootstrap.child_context
    assert context is not None

    context.verify_current_process()
    context.verify_handoff()


def test_child_context_is_created_from_same_handoff(
    tmp_path: Path,
) -> None:
    handoff = _handoff(tmp_path)

    bootstrap = establish_child_bootstrap(handoff)

    assert bootstrap.handoff is handoff
    assert bootstrap.child_context is not None
    assert bootstrap.child_context.handoff is handoff


def test_read_handoff_preserves_authorization_identity(
    tmp_path: Path,
) -> None:
    handoff = _handoff(tmp_path)

    result = read_handoff(
        io.BytesIO(handoff.model_dump_json().encode()),
    )

    assert result.execution_id == "exec-entry-001"
    assert result.request_id == "req-entry-001"
    assert result.authorization_reference == "auth-entry-001"
