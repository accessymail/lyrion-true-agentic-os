"""Unit tests for the Linux namespace-isolation adapter."""

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
from lyrion.execution.backends.linux.enforcement.primitives.namespaces import (
    NamespaceAdapter,
    NamespaceState,
)
from lyrion.execution.sandbox import (
    ExecutionTarget,
    IsolationLevel,
    NetworkMode,
    ResourceLimits,
    SandboxConfig,
)


class FakeNamespaceOperations:
    """Deterministic namespace operation boundary."""

    def __init__(
        self,
        *,
        process_isolated: bool = False,
        mount_isolated: bool = False,
        network_isolated: bool = False,
    ) -> None:
        self.state = NamespaceState(
            process_isolated=process_isolated,
            mount_isolated=mount_isolated,
            network_isolated=network_isolated,
        )
        self.process_calls = 0
        self.mount_calls = 0
        self.network_calls = 0

    def get_state(self) -> NamespaceState:
        return self.state

    def isolate_process(self) -> None:
        self.process_calls += 1
        self.state = NamespaceState(
            process_isolated=True,
            mount_isolated=self.state.mount_isolated,
            network_isolated=self.state.network_isolated,
        )

    def isolate_mount(self) -> None:
        self.mount_calls += 1
        self.state = NamespaceState(
            process_isolated=self.state.process_isolated,
            mount_isolated=True,
            network_isolated=self.state.network_isolated,
        )

    def isolate_network(self) -> None:
        self.network_calls += 1
        self.state = NamespaceState(
            process_isolated=self.state.process_isolated,
            mount_isolated=self.state.mount_isolated,
            network_isolated=True,
        )


def _sandbox() -> SandboxConfig:
    return SandboxConfig(
        execution_target=ExecutionTarget.LOCAL_CPU,
        isolation_level=IsolationLevel.STRICT,
        network_mode=NetworkMode.DISABLED,
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
        execution_id="test-namespace-isolation",
        backend_id="linux-native",
        started_at=datetime.now(UTC),
    )


def test_validate_accepts_authoritative_namespace_requirement() -> None:
    adapter = NamespaceAdapter(FakeNamespaceOperations())

    result = adapter.validate(_plan())

    assert result.primitive is EnforcementPrimitive.NAMESPACES
    assert result.required is True
    assert result.success is True
    assert result.state is EnforcementState.SUPPORTED


def test_apply_requests_all_required_namespace_boundaries() -> None:
    operations = FakeNamespaceOperations()
    adapter = NamespaceAdapter(operations)

    result = adapter.apply(_context(), _plan())

    assert result.state is EnforcementState.APPLIED
    assert result.success is True
    assert result.state is not EnforcementState.VERIFIED
    assert operations.process_calls == 1
    assert operations.mount_calls == 1
    assert operations.network_calls == 1


def test_verify_independently_confirms_namespace_isolation() -> None:
    operations = FakeNamespaceOperations()
    adapter = NamespaceAdapter(operations)
    plan = _plan()

    applied = adapter.apply(_context(), plan)
    assert applied.state is EnforcementState.APPLIED

    verified = adapter.verify(_context(), plan)

    assert verified.state is EnforcementState.VERIFIED
    assert verified.success is True
    assert len(verified.evidence) == 1
    assert verified.evidence[0].evidence_type == "namespace_state"


def test_verify_fails_when_required_namespace_is_missing() -> None:
    operations = FakeNamespaceOperations(
        process_isolated=True,
        mount_isolated=True,
        network_isolated=False,
    )
    adapter = NamespaceAdapter(operations)

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert result.success is False


def test_apply_fails_closed_on_operation_error() -> None:
    class FailingOperations(FakeNamespaceOperations):
        def isolate_process(self) -> None:
            raise OSError("namespace operation unavailable")

    adapter = NamespaceAdapter(FailingOperations())

    result = adapter.apply(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "namespace operation unavailable" in result.reason


def test_verify_fails_closed_on_operation_error() -> None:
    class FailingOperations(FakeNamespaceOperations):
        def get_state(self) -> NamespaceState:
            raise OSError("namespace verification unavailable")

    adapter = NamespaceAdapter(FailingOperations())

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "namespace verification unavailable" in result.reason


def test_evidence_returns_tuple() -> None:
    operations = FakeNamespaceOperations(
        process_isolated=True,
        mount_isolated=True,
        network_isolated=True,
    )
    adapter = NamespaceAdapter(operations)

    evidence = adapter.evidence(_context(), _plan())

    assert isinstance(evidence, tuple)
    assert len(evidence) == 1
    assert evidence[0].primitive is EnforcementPrimitive.NAMESPACES
    assert evidence[0].observed_state is EnforcementState.VERIFIED


def test_native_operations_are_not_used_by_unit_tests() -> None:
    adapter = NamespaceAdapter(
        operations=FakeNamespaceOperations(
            process_isolated=True,
            mount_isolated=True,
            network_isolated=True,
        )
    )

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.VERIFIED
    assert result.success is True


def test_minimal_plan_does_not_require_namespace_isolation() -> None:
    sandbox = SandboxConfig(
        execution_target=ExecutionTarget.LOCAL_CPU,
        isolation_level=IsolationLevel.MINIMAL,
        resource_limits=ResourceLimits(
            max_runtime_seconds=30.0,
            max_memory_mb=256,
            max_output_bytes=65536,
            max_cpu_seconds=30.0,
        ),
    )
    plan = LinuxEnforcementPlanner().plan(sandbox)
    adapter = NamespaceAdapter(FakeNamespaceOperations())

    result = adapter.validate(plan)

    assert plan.namespaces.required is False
    assert result.state is EnforcementState.PLANNED
    assert result.success is True
