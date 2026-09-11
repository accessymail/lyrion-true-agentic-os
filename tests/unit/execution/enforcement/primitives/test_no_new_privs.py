"""Tests for the NoNewPrivs enforcement adapter."""

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
from lyrion.execution.backends.linux.enforcement.primitives.no_new_privs import (
    NoNewPrivsAdapter,
)
from lyrion.execution.sandbox import (
    ExecutionTarget,
    ResourceLimits,
    SandboxConfig,
)


class FakeNoNewPrivsOperations:
    """Test double that never changes the real process."""

    def __init__(
        self,
        *,
        active: bool = False,
        set_error: Exception | None = None,
        get_error: Exception | None = None,
    ) -> None:
        self.active = active
        self.set_error = set_error
        self.get_error = get_error
        self.set_calls = 0
        self.get_calls = 0

    def set_no_new_privs(self) -> None:
        self.set_calls += 1
        if self.set_error is not None:
            raise self.set_error
        self.active = True

    def get_no_new_privs(self) -> bool:
        self.get_calls += 1
        if self.get_error is not None:
            raise self.get_error
        return self.active


def make_plan():
    sandbox = SandboxConfig(
        execution_target=ExecutionTarget.LOCAL_CPU,
        resource_limits=ResourceLimits(
            max_runtime_seconds=30.0,
            max_memory_mb=256,
            max_output_bytes=65536,
            max_cpu_seconds=30.0,
        ),
    )
    return LinuxEnforcementPlanner().plan(sandbox)


def make_context() -> EnforcementApplicationContext:
    return EnforcementApplicationContext.create(
        execution_id="test-execution",
        backend_id="linux-native",
        started_at=datetime.now(UTC),
    )


def test_owns_no_new_privs() -> None:
    adapter = NoNewPrivsAdapter(FakeNoNewPrivsOperations())
    assert adapter.primitive is EnforcementPrimitive.NO_NEW_PRIVS


def test_validate_does_not_mutate() -> None:
    operations = FakeNoNewPrivsOperations()
    result = NoNewPrivsAdapter(operations).validate(make_plan())

    assert result.state is EnforcementState.SUPPORTED
    assert result.success
    assert operations.set_calls == 0
    assert operations.get_calls == 0


def test_apply_only_reports_applied() -> None:
    operations = FakeNoNewPrivsOperations()
    result = NoNewPrivsAdapter(operations).apply(
        make_context(),
        make_plan(),
    )

    assert result.state is EnforcementState.APPLIED
    assert result.success
    assert not result.evidence
    assert operations.set_calls == 1


def test_verify_fails_when_kernel_state_is_false() -> None:
    operations = FakeNoNewPrivsOperations(active=False)
    result = NoNewPrivsAdapter(operations).verify(
        make_context(),
        make_plan(),
    )

    assert result.state is EnforcementState.FAILED
    assert not result.success
    assert operations.get_calls == 1


def test_verify_requires_positive_state_and_evidence() -> None:
    operations = FakeNoNewPrivsOperations(active=True)
    result = NoNewPrivsAdapter(operations).verify(
        make_context(),
        make_plan(),
    )

    assert result.state is EnforcementState.VERIFIED
    assert result.success
    assert len(result.evidence) == 1
    assert result.evidence[0].primitive is EnforcementPrimitive.NO_NEW_PRIVS
    assert result.evidence[0].observed_state is EnforcementState.VERIFIED


def test_apply_failure_is_fail_closed() -> None:
    operations = FakeNoNewPrivsOperations(
        set_error=PermissionError("denied"),
    )
    result = NoNewPrivsAdapter(operations).apply(
        make_context(),
        make_plan(),
    )

    assert result.state is EnforcementState.FAILED
    assert not result.success
    assert result.required


def test_verify_failure_is_fail_closed() -> None:
    operations = FakeNoNewPrivsOperations(
        get_error=OSError("unavailable"),
    )
    result = NoNewPrivsAdapter(operations).verify(
        make_context(),
        make_plan(),
    )

    assert result.state is EnforcementState.FAILED
    assert not result.success
    assert result.required


def test_evidence_is_empty_without_verification() -> None:
    operations = FakeNoNewPrivsOperations(active=False)
    evidence = NoNewPrivsAdapter(operations).evidence(
        make_context(),
        make_plan(),
    )

    assert evidence == ()


def test_evidence_is_returned_after_verification() -> None:
    operations = FakeNoNewPrivsOperations(active=True)
    evidence = NoNewPrivsAdapter(operations).evidence(
        make_context(),
        make_plan(),
    )

    assert len(evidence) == 1
    assert evidence[0].primitive is EnforcementPrimitive.NO_NEW_PRIVS
    assert evidence[0].observed_state is EnforcementState.VERIFIED


def test_unexpected_apply_exception_fails_closed() -> None:
    class Broken:
        def set_no_new_privs(self) -> None:
            raise RuntimeError("unexpected")

        def get_no_new_privs(self) -> bool:
            return False

    result = NoNewPrivsAdapter(Broken()).apply(
        make_context(),
        make_plan(),
    )

    assert result.state is EnforcementState.FAILED
    assert not result.success


def test_unexpected_verify_exception_fails_closed() -> None:
    class Broken:
        def set_no_new_privs(self) -> None:
            return None

        def get_no_new_privs(self) -> bool:
            raise RuntimeError("unexpected")

    result = NoNewPrivsAdapter(Broken()).verify(
        make_context(),
        make_plan(),
    )

    assert result.state is EnforcementState.FAILED
    assert not result.success


def test_missing_requirement_fails_closed() -> None:
    original = make_plan()
    requirements = tuple(
        item
        for item in original.requirements
        if item.primitive is not EnforcementPrimitive.NO_NEW_PRIVS
    )
    modified = original.model_copy(
        update={"requirements": requirements},
    )

    result = NoNewPrivsAdapter(
        FakeNoNewPrivsOperations(),
    ).validate(modified)

    assert result.state is EnforcementState.FAILED
    assert not result.success
