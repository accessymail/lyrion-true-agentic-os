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
from lyrion.execution.backends.linux.enforcement.primitives.no_new_privs import (
    NoNewPrivsAdapter,
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
        execution_id="native-no-new-privs-adversarial",
        backend_id="linux-native",
        started_at=datetime.now(UTC),
    )


class FailingSetOperations:
    def set_no_new_privs(self) -> None:
        raise OSError("synthetic PR_SET_NO_NEW_PRIVS failure")

    def get_no_new_privs(self) -> bool:
        return False


class UnexpectedSetOperations:
    def set_no_new_privs(self) -> None:
        raise RuntimeError("synthetic unexpected set failure")

    def get_no_new_privs(self) -> bool:
        return False


class FailingGetOperations:
    def set_no_new_privs(self) -> None:
        return None

    def get_no_new_privs(self) -> bool:
        raise OSError("synthetic PR_GET_NO_NEW_PRIVS failure")


class UnexpectedGetOperations:
    def set_no_new_privs(self) -> None:
        return None

    def get_no_new_privs(self) -> bool:
        raise RuntimeError("synthetic unexpected get failure")


class InactiveGetOperations:
    def set_no_new_privs(self) -> None:
        return None

    def get_no_new_privs(self) -> bool:
        return False


class ActiveGetOperations:
    def set_no_new_privs(self) -> None:
        return None

    def get_no_new_privs(self) -> bool:
        return True


def _remove_no_new_privs_requirement(
    plan: LinuxEnforcementPlan,
) -> LinuxEnforcementPlan:
    requirements = tuple(
        item
        for item in plan.requirements
        if item.primitive is not EnforcementPrimitive.NO_NEW_PRIVS
    )

    return plan.model_copy(
        update={"requirements": requirements},
    )


def _fail_no_new_privs_requirement(
    plan: LinuxEnforcementPlan,
) -> LinuxEnforcementPlan:
    requirements = tuple(
        item.model_copy(
            update={
                "state": EnforcementState.FAILED,
                "reason": "synthetic requirement failure",
            }
        )
        if item.primitive is EnforcementPrimitive.NO_NEW_PRIVS
        else item
        for item in plan.requirements
    )

    return plan.model_copy(
        update={"requirements": requirements},
    )


def test_apply_native_os_error_is_fail_closed() -> None:
    result = NoNewPrivsAdapter(
        FailingSetOperations(),
    ).apply(
        _context(),
        _plan(),
    )

    assert result.success is False
    assert result.state is EnforcementState.FAILED
    assert result.required is True
    assert "Unable to apply no_new_privs" in result.reason
    assert result.evidence == ()


def test_apply_unexpected_exception_is_fail_closed() -> None:
    result = NoNewPrivsAdapter(
        UnexpectedSetOperations(),
    ).apply(
        _context(),
        _plan(),
    )

    assert result.success is False
    assert result.state is EnforcementState.FAILED
    assert result.required is True
    assert "Unexpected no_new_privs application failure" in result.reason
    assert result.evidence == ()


def test_verify_native_os_error_is_fail_closed() -> None:
    result = NoNewPrivsAdapter(
        FailingGetOperations(),
    ).verify(
        _context(),
        _plan(),
    )

    assert result.success is False
    assert result.state is EnforcementState.FAILED
    assert result.required is True
    assert "Unable to verify no_new_privs" in result.reason
    assert result.evidence == ()


def test_verify_unexpected_exception_is_fail_closed() -> None:
    result = NoNewPrivsAdapter(
        UnexpectedGetOperations(),
    ).verify(
        _context(),
        _plan(),
    )

    assert result.success is False
    assert result.state is EnforcementState.FAILED
    assert result.required is True
    assert "Unexpected no_new_privs verification failure" in result.reason
    assert result.evidence == ()


def test_verify_inactive_kernel_state_fails_closed() -> None:
    result = NoNewPrivsAdapter(
        InactiveGetOperations(),
    ).verify(
        _context(),
        _plan(),
    )

    assert result.success is False
    assert result.state is EnforcementState.FAILED
    assert result.required is True
    assert "no_new_privs=0" in result.reason
    assert result.evidence == ()


def test_missing_requirement_is_rejected() -> None:
    plan = _remove_no_new_privs_requirement(_plan())

    adapter = NoNewPrivsAdapter(
        ActiveGetOperations(),
    )

    validation = adapter.validate(plan)
    applied = adapter.apply(_context(), plan)
    verified = adapter.verify(_context(), plan)

    assert validation.success is False
    assert validation.state is EnforcementState.FAILED

    assert applied.success is False
    assert applied.state is EnforcementState.FAILED

    assert verified.success is False
    assert verified.state is EnforcementState.FAILED


def test_failed_requirement_is_rejected() -> None:
    plan = _fail_no_new_privs_requirement(_plan())

    adapter = NoNewPrivsAdapter(
        ActiveGetOperations(),
    )

    validation = adapter.validate(plan)
    applied = adapter.apply(_context(), plan)
    verified = adapter.verify(_context(), plan)

    assert validation.success is False
    assert validation.state is EnforcementState.FAILED
    assert "synthetic requirement failure" in validation.reason

    assert applied.success is False
    assert applied.state is EnforcementState.FAILED

    assert verified.success is False
    assert verified.state is EnforcementState.FAILED


def test_successful_verification_produces_exactly_one_evidence_record() -> None:
    result = NoNewPrivsAdapter(
        ActiveGetOperations(),
    ).verify(
        _context(),
        _plan(),
    )

    assert result.success is True
    assert result.state is EnforcementState.VERIFIED
    assert len(result.evidence) == 1
    assert result.evidence[0].primitive is EnforcementPrimitive.NO_NEW_PRIVS


def test_evidence_is_empty_when_verification_fails() -> None:
    adapter = NoNewPrivsAdapter(
        InactiveGetOperations(),
    )

    evidence = adapter.evidence(
        _context(),
        _plan(),
    )

    assert evidence == ()


def test_apply_does_not_claim_verification() -> None:
    result = NoNewPrivsAdapter(
        ActiveGetOperations(),
    ).apply(
        _context(),
        _plan(),
    )

    assert result.success is True
    assert result.state is EnforcementState.APPLIED
    assert result.evidence == ()


def test_repeated_apply_remains_applied_without_verification_claim() -> None:
    adapter = NoNewPrivsAdapter(
        ActiveGetOperations(),
    )

    first = adapter.apply(_context(), _plan())
    second = adapter.apply(_context(), _plan())

    assert first.success is True
    assert second.success is True

    assert first.state is EnforcementState.APPLIED
    assert second.state is EnforcementState.APPLIED

