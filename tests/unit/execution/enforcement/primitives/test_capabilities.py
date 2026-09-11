"""Unit tests for the Linux capability-reduction adapter."""

from __future__ import annotations

from datetime import UTC, datetime

from lyrion.core.types import ExecutionTarget
from lyrion.execution.backends.linux.enforcement.application import (
    EnforcementApplicationContext,
)
from lyrion.execution.backends.linux.enforcement.contracts import (
    EnforcementPrimitive,
    EnforcementState,
    LinuxEnforcementPlan,
)
from lyrion.execution.backends.linux.enforcement.planner import (
    LinuxEnforcementPlanner,
)
from lyrion.execution.backends.linux.enforcement.primitives.capabilities import (
    CapabilityAdapter,
    CapabilityState,
)
from lyrion.execution.contracts import ResourceLimits
from lyrion.execution.sandbox import SandboxConfig


class FakeCapabilityOperations:
    """Deterministic operation boundary; never mutates the real host."""

    def __init__(
        self,
        *,
        effective: frozenset[int] = frozenset({1, 2, 3}),
        permitted: frozenset[int] = frozenset({1, 2, 3, 4}),
        inheritable: frozenset[int] = frozenset({1, 2}),
    ) -> None:
        self.state = CapabilityState(
            effective=effective,
            permitted=permitted,
            inheritable=inheritable,
            bounding=frozenset({1, 2, 3, 4, 5}),
            ambient=frozenset(),
        )
        self.set_calls = 0

    def get_state(self) -> CapabilityState:
        return self.state

    def set_capabilities(
        self,
        *,
        effective: frozenset[int],
        permitted: frozenset[int],
        inheritable: frozenset[int],
    ) -> None:
        self.set_calls += 1
        self.state = CapabilityState(
            effective=effective,
            permitted=permitted,
            inheritable=inheritable,
            bounding=self.state.bounding,
            ambient=self.state.ambient,
        )

    def drop_bounding(self, capability: int) -> None:
        self.state = CapabilityState(
            effective=self.state.effective,
            permitted=self.state.permitted,
            inheritable=self.state.inheritable,
            bounding=self.state.bounding - {capability},
            ambient=self.state.ambient,
        )

    def get_bounding(self, capability: int) -> bool:
        return capability in self.state.bounding

    def get_ambient(self, capability: int) -> bool:
        return capability in self.state.ambient

    def clear_ambient(self) -> None:
        self.state = CapabilityState(
            effective=self.state.effective,
            permitted=self.state.permitted,
            inheritable=self.state.inheritable,
            bounding=self.state.bounding,
            ambient=frozenset(),
        )


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
        execution_id="test-capability-reduction",
        backend_id="linux-native",
        started_at=datetime.now(UTC),
    )


def test_validate_accepts_authoritative_capability_requirement() -> None:
    adapter = CapabilityAdapter(FakeCapabilityOperations())

    result = adapter.validate(_plan())

    assert result.primitive is EnforcementPrimitive.CAPABILITIES
    assert result.required is True
    assert result.success is True
    assert result.state is EnforcementState.SUPPORTED


def test_apply_only_reduces_capabilities() -> None:
    operations = FakeCapabilityOperations()
    adapter = CapabilityAdapter(operations)

    result = adapter.apply(_context(), _plan())

    assert result.state is EnforcementState.APPLIED
    assert result.success is True
    assert operations.set_calls == 1
    assert operations.state.effective == frozenset()
    assert operations.state.permitted == frozenset()
    assert operations.state.inheritable == frozenset()
    assert operations.state.bounding == frozenset()
    assert operations.state.ambient == frozenset()


def test_verify_independently_confirms_reduction() -> None:
    operations = FakeCapabilityOperations()
    adapter = CapabilityAdapter(operations)
    plan = _plan()

    applied = adapter.apply(_context(), plan)
    assert applied.state is EnforcementState.APPLIED

    verified = adapter.verify(_context(), plan)

    assert verified.state is EnforcementState.VERIFIED
    assert verified.success is True
    assert len(verified.evidence) == 1
    assert verified.evidence[0].evidence_type == "capability_state"


def test_verify_fails_when_capabilities_remain() -> None:
    adapter = CapabilityAdapter(FakeCapabilityOperations())

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert result.success is False


def test_apply_fails_closed_on_operation_error() -> None:
    class FailingOperations(FakeCapabilityOperations):
        def get_state(self) -> CapabilityState:
            raise OSError("operation unavailable")

    adapter = CapabilityAdapter(FailingOperations())

    result = adapter.apply(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "operation unavailable" in result.reason


def test_verify_fails_closed_on_operation_error() -> None:
    class FailingOperations(FakeCapabilityOperations):
        def get_state(self) -> CapabilityState:
            raise OSError("verification unavailable")

    adapter = CapabilityAdapter(FailingOperations())

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "verification unavailable" in result.reason


def test_evidence_returns_tuple() -> None:
    operations = FakeCapabilityOperations(
        effective=frozenset(),
        permitted=frozenset(),
        inheritable=frozenset(),
    )
    operations.state = CapabilityState(
        effective=frozenset(),
        permitted=frozenset(),
        inheritable=frozenset(),
        bounding=frozenset(),
        ambient=frozenset(),
    )

    adapter = CapabilityAdapter(operations)

    evidence = adapter.evidence(_context(), _plan())

    assert isinstance(evidence, tuple)
    assert len(evidence) == 1
    assert evidence[0].primitive is EnforcementPrimitive.CAPABILITIES
    assert evidence[0].observed_state is EnforcementState.VERIFIED


def test_native_operations_are_not_used_by_unit_tests() -> None:
    operations = FakeCapabilityOperations(
        effective=frozenset(),
        permitted=frozenset(),
        inheritable=frozenset(),
    )
    operations.state = CapabilityState(
        effective=frozenset(),
        permitted=frozenset(),
        inheritable=frozenset(),
        bounding=frozenset(),
        ambient=frozenset(),
    )

    adapter = CapabilityAdapter(operations)

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.VERIFIED
    assert result.success is True


def test_apply_drops_entire_bounding_set_and_clears_ambient() -> None:
    operations = FakeCapabilityOperations()

    operations.state = CapabilityState(
        effective=frozenset({1, 2}),
        permitted=frozenset({1, 2, 3}),
        inheritable=frozenset({1}),
        bounding=frozenset({1, 2, 3, 4, 5}),
        ambient=frozenset({1, 2}),
    )

    adapter = CapabilityAdapter(operations)

    result = adapter.apply(_context(), _plan())

    assert result.state is EnforcementState.APPLIED
    assert result.success is True
    assert operations.state.bounding == frozenset()
    assert operations.state.ambient == frozenset()


def test_verify_fails_when_bounding_capability_remains() -> None:
    operations = FakeCapabilityOperations(
        effective=frozenset(),
        permitted=frozenset(),
        inheritable=frozenset(),
    )

    operations.state = CapabilityState(
        effective=frozenset(),
        permitted=frozenset(),
        inheritable=frozenset(),
        bounding=frozenset({5}),
        ambient=frozenset(),
    )

    result = CapabilityAdapter(operations).verify(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "bounding" in result.reason


def test_verify_fails_when_ambient_capability_remains() -> None:
    operations = FakeCapabilityOperations(
        effective=frozenset(),
        permitted=frozenset(),
        inheritable=frozenset(),
    )

    operations.state = CapabilityState(
        effective=frozenset(),
        permitted=frozenset(),
        inheritable=frozenset(),
        bounding=frozenset(),
        ambient=frozenset({5}),
    )

    result = CapabilityAdapter(operations).verify(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "ambient" in result.reason


def test_apply_fails_closed_when_bounding_drop_fails() -> None:
    class FailingBoundingOperations(FakeCapabilityOperations):
        def drop_bounding(self, capability: int) -> None:
            raise OSError(f"cannot drop capability {capability}")

    operations = FailingBoundingOperations()
    adapter = CapabilityAdapter(operations)

    result = adapter.apply(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "cannot drop capability" in result.reason


def test_apply_fails_closed_when_ambient_clear_fails() -> None:
    class FailingAmbientOperations(FakeCapabilityOperations):
        def clear_ambient(self) -> None:
            raise OSError("cannot clear ambient capabilities")

    operations = FailingAmbientOperations()
    adapter = CapabilityAdapter(operations)

    result = adapter.apply(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "cannot clear ambient capabilities" in result.reason


def test_evidence_requires_all_capability_sets_empty() -> None:
    operations = FakeCapabilityOperations(
        effective=frozenset(),
        permitted=frozenset(),
        inheritable=frozenset(),
    )

    operations.state = CapabilityState(
        effective=frozenset(),
        permitted=frozenset(),
        inheritable=frozenset(),
        bounding=frozenset(),
        ambient=frozenset(),
    )

    evidence = CapabilityAdapter(operations).evidence(
        _context(),
        _plan(),
    )

    assert len(evidence) == 1
    assert evidence[0].observed_state is EnforcementState.VERIFIED
    assert "bounding" in evidence[0].observation
    assert "ambient" in evidence[0].observation
