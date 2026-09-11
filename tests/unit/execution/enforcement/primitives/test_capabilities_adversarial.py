"""Adversarial qualification tests for Linux capability enforcement."""

from __future__ import annotations

from datetime import UTC, datetime

from lyrion.core.types import ExecutionTarget
from lyrion.execution.backends.linux.enforcement.application import (
    EnforcementApplicationContext,
    EnforcementPrimitiveResult,
)
from lyrion.execution.backends.linux.enforcement.contracts import (
    EnforcementState,
    LinuxEnforcementPlan,
)
from lyrion.execution.backends.linux.enforcement.planner import (
    LinuxEnforcementPlanner,
)
from lyrion.execution.backends.linux.enforcement.primitives.capabilities import (
    CapabilityAdapter,
    CapabilityOperations,
    CapabilityState,
    LibcCapabilityOperations,
)
from lyrion.execution.contracts import ResourceLimits
from lyrion.execution.sandbox import SandboxConfig


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
        execution_id="capability-adversarial",
        backend_id="linux-test",
        started_at=datetime.now(UTC),
    )


class RecordingCapabilityOperations:
    """Deterministic capability backend used to verify operation ordering."""

    def __init__(
        self,
        *,
        state: CapabilityState | None = None,
    ) -> None:
        self.state = state or CapabilityState(
            effective=frozenset({1}),
            permitted=frozenset({1}),
            inheritable=frozenset({2}),
            bounding=frozenset({3, 4}),
            ambient=frozenset({5}),
        )
        self.calls: list[tuple[str, object]] = []

    def get_state(self) -> CapabilityState:
        self.calls.append(("get_state", None))
        return self.state

    def set_capabilities(
        self,
        *,
        effective: frozenset[int],
        permitted: frozenset[int],
        inheritable: frozenset[int],
    ) -> None:
        self.calls.append(
            (
                "set_capabilities",
                (effective, permitted, inheritable),
            )
        )
        self.state = CapabilityState(
            effective=effective,
            permitted=permitted,
            inheritable=inheritable,
            bounding=self.state.bounding,
            ambient=self.state.ambient,
        )

    def drop_bounding(self, capability: int) -> None:
        self.calls.append(("drop_bounding", capability))
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
        self.calls.append(("clear_ambient", None))
        self.state = CapabilityState(
            effective=self.state.effective,
            permitted=self.state.permitted,
            inheritable=self.state.inheritable,
            bounding=self.state.bounding,
            ambient=frozenset(),
        )


class BoundingFailureOperations(RecordingCapabilityOperations):
    """Backend that refuses the first bounding-set mutation."""

    def drop_bounding(self, capability: int) -> None:
        self.calls.append(("drop_bounding", capability))
        raise OSError(1, "permission denied")


class AmbientFailureOperations(RecordingCapabilityOperations):
    """Backend that refuses ambient clearing."""

    def clear_ambient(self) -> None:
        self.calls.append(("clear_ambient", None))
        raise OSError(1, "permission denied")


class CapabilitySetFailureOperations(RecordingCapabilityOperations):
    """Backend that fails during the final capability reduction."""

    def set_capabilities(
        self,
        *,
        effective: frozenset[int],
        permitted: frozenset[int],
        inheritable: frozenset[int],
    ) -> None:
        self.calls.append(
            (
                "set_capabilities",
                (effective, permitted, inheritable),
            )
        )
        raise OSError(1, "permission denied")


def _apply(
    operations: CapabilityOperations,
) -> EnforcementPrimitiveResult:
    adapter = CapabilityAdapter(operations)
    return adapter.apply(_context(), _plan())


def test_apply_performs_privileged_transitions_before_final_capset() -> None:
    operations = RecordingCapabilityOperations()

    result = _apply(operations)

    assert result.success
    assert result.state is EnforcementState.APPLIED

    call_names = [name for name, _ in operations.calls]

    assert call_names.index("drop_bounding") < call_names.index(
        "clear_ambient"
    )
    assert call_names.index("clear_ambient") < call_names.index(
        "set_capabilities"
    )

    assert operations.state.effective == frozenset()
    assert operations.state.permitted == frozenset()
    assert operations.state.inheritable == frozenset()
    assert operations.state.bounding == frozenset()
    assert operations.state.ambient == frozenset()


def test_bounding_failure_fails_closed_before_later_mutations() -> None:
    operations = BoundingFailureOperations()

    result = _apply(operations)

    assert not result.success
    assert result.state is EnforcementState.FAILED

    call_names = [name for name, _ in operations.calls]

    assert "drop_bounding" in call_names
    assert "clear_ambient" not in call_names
    assert "set_capabilities" not in call_names


def test_ambient_failure_fails_closed_before_final_capset() -> None:
    operations = AmbientFailureOperations()

    result = _apply(operations)

    assert not result.success
    assert result.state is EnforcementState.FAILED

    call_names = [name for name, _ in operations.calls]

    assert "drop_bounding" in call_names
    assert "clear_ambient" in call_names
    assert "set_capabilities" not in call_names


def test_final_capset_failure_returns_failed_after_prior_transitions() -> None:
    operations = CapabilitySetFailureOperations()

    result = _apply(operations)

    assert not result.success
    assert result.state is EnforcementState.FAILED

    call_names = [name for name, _ in operations.calls]

    assert "drop_bounding" in call_names
    assert "clear_ambient" in call_names
    assert "set_capabilities" in call_names


def test_apply_never_claims_verified() -> None:
    operations = RecordingCapabilityOperations()

    result = _apply(operations)

    assert result.state is EnforcementState.APPLIED
    assert result.evidence == ()


def test_verification_rejects_nonempty_bounding_set() -> None:
    operations = RecordingCapabilityOperations(
        state=CapabilityState(
            effective=frozenset(),
            permitted=frozenset(),
            inheritable=frozenset(),
            bounding=frozenset({7}),
            ambient=frozenset(),
        )
    )

    adapter = CapabilityAdapter(operations)
    result = adapter.verify(_context(), _plan())

    assert not result.success
    assert result.state is EnforcementState.FAILED
    assert result.evidence == ()


def test_verification_rejects_nonempty_ambient_set() -> None:
    operations = RecordingCapabilityOperations(
        state=CapabilityState(
            effective=frozenset(),
            permitted=frozenset(),
            inheritable=frozenset(),
            bounding=frozenset(),
            ambient=frozenset({7}),
        )
    )

    adapter = CapabilityAdapter(operations)
    result = adapter.verify(_context(), _plan())

    assert not result.success
    assert result.state is EnforcementState.FAILED
    assert result.evidence == ()


def test_successful_verification_emits_exactly_one_evidence_record() -> None:
    operations = RecordingCapabilityOperations(
        state=CapabilityState(
            effective=frozenset(),
            permitted=frozenset(),
            inheritable=frozenset(),
            bounding=frozenset(),
            ambient=frozenset(),
        )
    )

    adapter = CapabilityAdapter(operations)
    result = adapter.verify(_context(), _plan())

    assert result.success
    assert result.state is EnforcementState.VERIFIED
    assert len(result.evidence) == 1


def test_repeated_verification_remains_deterministic() -> None:
    operations = RecordingCapabilityOperations(
        state=CapabilityState(
            effective=frozenset(),
            permitted=frozenset(),
            inheritable=frozenset(),
            bounding=frozenset(),
            ambient=frozenset(),
        )
    )

    adapter = CapabilityAdapter(operations)

    first = adapter.verify(_context(), _plan())
    second = adapter.verify(_context(), _plan())

    assert first.success
    assert second.success
    assert first.state is EnforcementState.VERIFIED
    assert second.state is EnforcementState.VERIFIED
    assert len(first.evidence) == 1
    assert len(second.evidence) == 1



def test_native_capability_number_rejects_negative_value() -> None:
    operations = LibcCapabilityOperations()

    operations_to_test = (
        lambda: operations.drop_bounding(-1),
        lambda: operations.get_bounding(-1),
        lambda: operations.get_ambient(-1),
        lambda: operations.set_capabilities(
            effective=frozenset({-1}),
            permitted=frozenset(),
            inheritable=frozenset(),
        ),
    )

    for operation in operations_to_test:
        try:
            operation()
        except ValueError as exc:
            assert "capability number" in str(exc)
        else:
            raise AssertionError(
                "negative capability number was unexpectedly accepted"
            )


def test_native_capability_number_boundary_is_not_rejected_by_adapter() -> None:
    operations = LibcCapabilityOperations()

    # Capability 64 is intentionally not rejected by the adapter merely
    # because the current ctypes representation uses two 32-bit words.
    # Kernel support remains authoritative for native capability IDs.
    try:
        operations.get_bounding(64)
    except ValueError as exc:
        raise AssertionError(
            "adapter incorrectly imposed an artificial capability maximum"
        ) from exc
    except OSError:
        # The kernel may legitimately reject an unsupported capability ID.
        pass


def test_native_capability_number_zero_reaches_kernel_validation() -> None:
    operations = LibcCapabilityOperations()

    try:
        operations.get_bounding(0)
    except ValueError as exc:
        raise AssertionError(
            "valid non-negative capability number was rejected"
        ) from exc
    except OSError:
        # An unprivileged process may encounter a native kernel error;
        # the important property here is that adapter-side validation did
        # not reject the capability number.
        pass

