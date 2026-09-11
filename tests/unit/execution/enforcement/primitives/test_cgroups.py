"""Unit tests for the Linux cgroup-v2 resource adapter."""

from __future__ import annotations

from datetime import UTC, datetime

from lyrion.execution.backends.linux.enforcement.application import (
    EnforcementApplicationContext,
)
from lyrion.execution.backends.linux.enforcement.contracts import (
    EnforcementPrimitive,
    EnforcementState,
)
from lyrion.execution.backends.linux.enforcement.planner import (
    LinuxEnforcementPlanner,
)
from lyrion.execution.backends.linux.enforcement.primitives.cgroups import (
    CgroupV2Adapter,
    CgroupV2State,
)
from lyrion.execution.sandbox import (
    ExecutionTarget,
    IsolationLevel,
    ResourceLimits,
    SandboxConfig,
)


class FakeCgroupV2Operations:
    """Deterministic cgroup-v2 operation boundary."""

    def __init__(
        self,
        *,
        controllers: frozenset[str] | None = None,
        memory_max_bytes: int | None = None,
    ) -> None:
        self.controllers = controllers or frozenset({"cpu", "memory", "pids"})
        self.memory_max_bytes = memory_max_bytes
        self.created_execution_ids: list[str] = []

    def get_state(self) -> CgroupV2State:
        return CgroupV2State(
            controllers=self.controllers,
            memory_max_bytes=self.memory_max_bytes,
            cpu_max=None,
        )

    def create_execution_cgroup(self, execution_id: str) -> None:
        self.created_execution_ids.append(execution_id)

    def configure_memory_max(self, memory_max_bytes: int) -> None:
        self.memory_max_bytes = memory_max_bytes


def _sandbox() -> SandboxConfig:
    return SandboxConfig(
        execution_target=ExecutionTarget.LOCAL_CPU,
        isolation_level=IsolationLevel.STRICT,
        resource_limits=ResourceLimits(
            max_runtime_seconds=30.0,
            max_memory_mb=256,
            max_output_bytes=65536,
            max_cpu_seconds=30.0,
        ),
    )


def _plan():
    return LinuxEnforcementPlanner().plan(_sandbox())


def _context() -> EnforcementApplicationContext:
    return EnforcementApplicationContext.create(
        execution_id="test-cgroup-v2",
        backend_id="linux-native",
        started_at=datetime.now(UTC),
    )


def test_validate_accepts_authoritative_cgroup_requirement() -> None:
    adapter = CgroupV2Adapter(FakeCgroupV2Operations())

    result = adapter.validate(_plan())

    assert result.primitive is EnforcementPrimitive.CGROUPS_V2
    assert result.required is True
    assert result.success is True
    assert result.state is EnforcementState.SUPPORTED


def test_apply_creates_execution_cgroup_and_sets_memory_limit() -> None:
    operations = FakeCgroupV2Operations()
    adapter = CgroupV2Adapter(operations)

    result = adapter.apply(_context(), _plan())

    assert result.state is EnforcementState.APPLIED
    assert result.success is True
    assert result.state is not EnforcementState.VERIFIED
    assert operations.created_execution_ids == ["test-cgroup-v2"]
    assert operations.memory_max_bytes == 256 * 1024 * 1024


def test_verify_independently_confirms_memory_limit() -> None:
    operations = FakeCgroupV2Operations()
    adapter = CgroupV2Adapter(operations)
    plan = _plan()

    applied = adapter.apply(_context(), plan)
    assert applied.state is EnforcementState.APPLIED

    verified = adapter.verify(_context(), plan)

    assert verified.state is EnforcementState.VERIFIED
    assert verified.success is True
    assert len(verified.evidence) == 1
    assert verified.evidence[0].evidence_type == "cgroup_state"


def test_verify_fails_when_memory_controller_is_missing() -> None:
    operations = FakeCgroupV2Operations(
        controllers=frozenset({"cpu", "pids"}),
        memory_max_bytes=256 * 1024 * 1024,
    )
    adapter = CgroupV2Adapter(operations)

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "memory" in result.reason


def test_verify_fails_when_memory_limit_is_wrong() -> None:
    operations = FakeCgroupV2Operations(
        memory_max_bytes=128 * 1024 * 1024,
    )
    adapter = CgroupV2Adapter(operations)

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "memory.max" in result.reason


def test_apply_fails_closed_on_operation_error() -> None:
    class FailingOperations(FakeCgroupV2Operations):
        def create_execution_cgroup(self, execution_id: str) -> None:
            del execution_id
            raise OSError("cgroup creation unavailable")

    adapter = CgroupV2Adapter(FailingOperations())

    result = adapter.apply(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "cgroup creation unavailable" in result.reason


def test_verify_fails_closed_on_operation_error() -> None:
    class FailingOperations(FakeCgroupV2Operations):
        def get_state(self) -> CgroupV2State:
            raise OSError("cgroup verification unavailable")

    adapter = CgroupV2Adapter(FailingOperations())

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "cgroup verification unavailable" in result.reason


def test_evidence_returns_tuple() -> None:
    operations = FakeCgroupV2Operations(
        memory_max_bytes=256 * 1024 * 1024,
    )
    adapter = CgroupV2Adapter(operations)

    evidence = adapter.evidence(_context(), _plan())

    assert isinstance(evidence, tuple)
    assert len(evidence) == 1
    assert evidence[0].primitive is EnforcementPrimitive.CGROUPS_V2
    assert evidence[0].observed_state is EnforcementState.VERIFIED


def test_native_operations_are_not_used_by_unit_tests() -> None:
    adapter = CgroupV2Adapter(
        FakeCgroupV2Operations(
            memory_max_bytes=256 * 1024 * 1024,
        )
    )

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.VERIFIED
    assert result.success is True


def test_cgroup_plan_preserves_all_execution_resource_limits() -> None:
    plan = _plan()

    assert plan.cgroups.max_runtime_seconds == 30.0
    assert plan.cgroups.max_memory_mb == 256
    assert plan.cgroups.max_output_bytes == 65536
    assert plan.cgroups.max_cpu_seconds == 30.0
