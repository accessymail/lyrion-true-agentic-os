"""Tests for the C2.2-C9 Linux enforcement application orchestrator."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lyrion.execution.backends.linux.enforcement.application import (
    EnforcementApplicationContext,
    EnforcementEvidence,
    EnforcementPrimitiveResult,
    EnforcementState,
)
from lyrion.execution.backends.linux.enforcement.application_runner import (
    LinuxEnforcementApplication,
)
from lyrion.execution.backends.linux.enforcement.contracts import (
    EnforcementPrimitive,
    LinuxEnforcementPlan,
)
from lyrion.execution.backends.linux.enforcement.planner import (
    LinuxEnforcementPlanner,
)
from lyrion.execution.backends.linux.enforcement.registry import (
    PrimitiveAdapterRegistry,
)
from lyrion.execution.sandbox import (
    ExecutionTarget,
    ResourceLimits,
    SandboxConfig,
)


def _plan() -> LinuxEnforcementPlan:
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


def _context() -> EnforcementApplicationContext:
    return EnforcementApplicationContext.create(
        execution_id="c2.2-c9-test",
        backend_id="linux-test",
        started_at=datetime.now(UTC),
    )


def _verified_result(
    primitive: EnforcementPrimitive,
) -> EnforcementPrimitiveResult:
    evidence = EnforcementEvidence.verified(
        primitive=primitive,
        evidence_type="test",
        observation="controlled test verification",
    )

    return EnforcementPrimitiveResult(
        primitive=primitive,
        required=True,
        state=EnforcementState.VERIFIED,
        success=True,
        reason="verified",
        evidence=(evidence,),
    )


class FakeAdapter:
    """Deterministic adapter used only for orchestrator tests."""

    def __init__(
        self,
        primitive: EnforcementPrimitive,
        *,
        supported: bool = True,
        fail_validation: bool = False,
        fail_apply: bool = False,
        fail_verify: bool = False,
    ) -> None:
        self._primitive = primitive
        self._supported = supported
        self._fail_validation = fail_validation
        self._fail_apply = fail_apply
        self._fail_verify = fail_verify
        self.calls: list[str] = []

    @property
    def primitive(self) -> EnforcementPrimitive:
        return self._primitive

    def supports(self, plan: LinuxEnforcementPlan) -> bool:
        del plan
        self.calls.append("supports")
        return self._supported

    def validate(
        self,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        del plan
        self.calls.append("validate")

        if self._fail_validation:
            return EnforcementPrimitiveResult(
                primitive=self._primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason="controlled validation failure",
            )

        return EnforcementPrimitiveResult(
            primitive=self._primitive,
            required=True,
            state=EnforcementState.SUPPORTED,
            success=True,
            reason="supported",
        )

    def apply(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        del context, plan
        self.calls.append("apply")

        if self._fail_apply:
            return EnforcementPrimitiveResult(
                primitive=self._primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason="controlled application failure",
            )

        return EnforcementPrimitiveResult(
            primitive=self._primitive,
            required=True,
            state=EnforcementState.APPLIED,
            success=True,
            reason="applied",
        )

    def verify(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        del context, plan
        self.calls.append("verify")

        if self._fail_verify:
            return EnforcementPrimitiveResult(
                primitive=self._primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason="controlled verification failure",
            )

        return _verified_result(self._primitive)

    def evidence(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> tuple:
        del context, plan
        return ()


def _all_adapters(**kwargs: object) -> tuple[FakeAdapter, ...]:
    return tuple(
        FakeAdapter(primitive, **kwargs)
        for primitive in EnforcementPrimitive
    )


def test_all_required_primitives_are_processed_deterministically() -> None:
    adapters = _all_adapters()
    application = LinuxEnforcementApplication(
        PrimitiveAdapterRegistry(adapters)
    )

    result = application.apply(_plan(), _context())

    assert result.status.value == "verified"
    assert result.execution_permitted is True
    assert tuple(
        item.primitive
        for item in result.primitive_results
    ) == tuple(EnforcementPrimitive)

    for adapter in adapters:
        assert adapter.calls == [
            "supports",
            "validate",
            "apply",
            "verify",
        ]


def test_missing_required_adapter_fails_closed() -> None:
    adapters = tuple(
        FakeAdapter(primitive)
        for primitive in EnforcementPrimitive
        if primitive is not EnforcementPrimitive.APPARMOR
    )

    application = LinuxEnforcementApplication(
        PrimitiveAdapterRegistry(adapters)
    )

    result = application.apply(_plan(), _context())

    assert result.status.value == "failed"
    assert result.execution_permitted is False
    assert "apparmor" in result.failure_reason


def test_unsupported_required_primitive_fails_closed() -> None:
    adapters = tuple(
        FakeAdapter(
            primitive,
            supported=primitive is not EnforcementPrimitive.SECCOMP,
        )
        for primitive in EnforcementPrimitive
    )

    application = LinuxEnforcementApplication(
        PrimitiveAdapterRegistry(adapters)
    )

    result = application.apply(_plan(), _context())

    assert result.status.value == "failed"
    assert result.execution_permitted is False
    assert "seccomp" in result.failure_reason


def test_validation_failure_stops_application() -> None:
    adapters = tuple(
        FakeAdapter(
            primitive,
            fail_validation=primitive is EnforcementPrimitive.CAPABILITIES,
        )
        for primitive in EnforcementPrimitive
    )

    application = LinuxEnforcementApplication(
        PrimitiveAdapterRegistry(adapters)
    )

    result = application.apply(_plan(), _context())

    assert result.status.value == "failed"
    assert result.execution_permitted is False

    capability = next(
        item
        for item in result.primitive_results
        if item.primitive is EnforcementPrimitive.CAPABILITIES
    )
    assert capability.state is EnforcementState.FAILED


def test_application_failure_stops_before_later_primitives() -> None:
    adapters = _all_adapters(
        fail_apply=True,
    )

    application = LinuxEnforcementApplication(
        PrimitiveAdapterRegistry(adapters)
    )

    result = application.apply(_plan(), _context())

    assert result.status.value == "failed"
    assert result.execution_permitted is False
    assert len(result.primitive_results) == 1


def test_verification_failure_cannot_permit_execution() -> None:
    adapters = tuple(
        FakeAdapter(
            primitive,
            fail_verify=primitive is EnforcementPrimitive.LANDLOCK,
        )
        for primitive in EnforcementPrimitive
    )

    application = LinuxEnforcementApplication(
        PrimitiveAdapterRegistry(adapters)
    )

    result = application.apply(_plan(), _context())

    assert result.status.value == "failed"
    assert result.execution_permitted is False
    assert "landlock" in result.failure_reason


def test_apply_cannot_report_verified() -> None:
    class BadApplyAdapter(FakeAdapter):
        def apply(
            self,
            context: EnforcementApplicationContext,
            plan: LinuxEnforcementPlan,
        ) -> EnforcementPrimitiveResult:
            del context, plan
            self.calls.append("apply")
            return _verified_result(self._primitive)

    adapters = tuple(
        BadApplyAdapter(primitive)
        for primitive in EnforcementPrimitive
    )

    application = LinuxEnforcementApplication(
        PrimitiveAdapterRegistry(adapters)
    )

    result = application.apply(_plan(), _context())

    assert result.status.value == "failed"
    assert result.execution_permitted is False


def test_exception_from_adapter_fails_closed() -> None:
    class ExplodingAdapter(FakeAdapter):
        def supports(self, plan: LinuxEnforcementPlan) -> bool:
            del plan
            raise RuntimeError("controlled adapter exception")

    adapters = tuple(
        ExplodingAdapter(primitive)
        for primitive in EnforcementPrimitive
    )

    application = LinuxEnforcementApplication(
        PrimitiveAdapterRegistry(adapters)
    )

    result = application.apply(_plan(), _context())

    assert result.status.value == "failed"
    assert result.execution_permitted is False


def test_rejected_plan_is_aborted() -> None:
    base = _plan()

    rejected = LinuxEnforcementPlan.rejected(
        SandboxConfig(
            execution_target=ExecutionTarget.LOCAL_CPU,
            resource_limits=ResourceLimits(
                max_runtime_seconds=30.0,
                max_memory_mb=256,
                max_output_bytes=65536,
                max_cpu_seconds=30.0,
            ),
        ),
        "controlled rejected plan",
    )

    assert rejected.status.value == "rejected"

    application = LinuxEnforcementApplication(
        PrimitiveAdapterRegistry(_all_adapters())
    )

    result = application.apply(
        rejected,
        _context(),
    )

    assert base.status.value == "ready"
    assert result.status.value == "aborted"
    assert result.execution_permitted is False


def test_duplicate_plan_requirements_are_rejected() -> None:
    base = _plan()

    duplicate = LinuxEnforcementPlan(
        status=base.status,
        isolation_level=base.isolation_level,
        privilege=base.privilege,
        namespaces=base.namespaces,
        cgroups=base.cgroups,
        filesystem=base.filesystem,
        network=base.network,
        environment=base.environment,
        seccomp=base.seccomp,
        landlock=base.landlock,
        apparmor=base.apparmor,
        requirements=base.requirements
        + (base.requirements[0],),
    )

    application = LinuxEnforcementApplication(
        PrimitiveAdapterRegistry(_all_adapters())
    )

    result = application.apply(duplicate, _context())

    assert result.status.value == "aborted"
    assert result.execution_permitted is False


@pytest.mark.parametrize(
    "primitive",
    tuple(EnforcementPrimitive),
)
def test_each_primitive_has_explicit_result(
    primitive: EnforcementPrimitive,
) -> None:
    adapters = _all_adapters()

    application = LinuxEnforcementApplication(
        PrimitiveAdapterRegistry(adapters)
    )

    result = application.apply(_plan(), _context())

    matching = [
        item
        for item in result.primitive_results
        if item.primitive is primitive
    ]

    assert len(matching) == 1
    assert matching[0].state is EnforcementState.VERIFIED


def test_wrong_adapter_identity_fails_closed() -> None:
    class WrongIdentityAdapter(FakeAdapter):
        @property
        def primitive(self) -> EnforcementPrimitive:
            return EnforcementPrimitive.CAPABILITIES

    adapter = WrongIdentityAdapter(
        EnforcementPrimitive.NO_NEW_PRIVS,
    )

    registry = PrimitiveAdapterRegistry(
        tuple(
            FakeAdapter(primitive)
            for primitive in EnforcementPrimitive
            if primitive
            not in {
                EnforcementPrimitive.NO_NEW_PRIVS,
                EnforcementPrimitive.CAPABILITIES,
            }
        )
        + (adapter,)
    )

    application = LinuxEnforcementApplication(registry)

    result = application.apply(_plan(), _context())

    assert result.status.value == "failed"
    assert result.execution_permitted is False
    assert len(result.primitive_results) == 1
    assert result.primitive_results[0].primitive is (
        EnforcementPrimitive.NO_NEW_PRIVS
    )


def test_wrong_required_flag_fails_closed() -> None:
    class WrongRequiredAdapter(FakeAdapter):
        def validate(
            self,
            plan: LinuxEnforcementPlan,
        ) -> EnforcementPrimitiveResult:
            del plan
            self.calls.append("validate")
            return EnforcementPrimitiveResult(
                primitive=self._primitive,
                required=False,
                state=EnforcementState.SUPPORTED,
                success=True,
                reason="incorrect required flag",
            )

    adapters = list(_all_adapters())
    adapters[0] = WrongRequiredAdapter(
        EnforcementPrimitive.NO_NEW_PRIVS,
    )

    application = LinuxEnforcementApplication(
        PrimitiveAdapterRegistry(tuple(adapters))
    )

    result = application.apply(_plan(), _context())

    assert result.status.value == "failed"
    assert result.execution_permitted is False


def test_apply_failed_result_cannot_be_successful() -> None:
    adapters = _all_adapters(
        fail_apply=True,
    )

    application = LinuxEnforcementApplication(
        PrimitiveAdapterRegistry(adapters)
    )

    result = application.apply(_plan(), _context())

    assert result.status.value == "failed"
    assert result.execution_permitted is False

    first = result.primitive_results[0]

    assert first.state is EnforcementState.FAILED
    assert first.success is False


def test_verification_failure_does_not_run_later_primitives() -> None:
    adapters = list(_all_adapters())

    failing_index = list(EnforcementPrimitive).index(
        EnforcementPrimitive.LANDLOCK,
    )

    adapters[failing_index] = FakeAdapter(
        EnforcementPrimitive.LANDLOCK,
        fail_verify=True,
    )

    application = LinuxEnforcementApplication(
        PrimitiveAdapterRegistry(tuple(adapters))
    )

    result = application.apply(_plan(), _context())

    assert result.status.value == "failed"
    assert result.execution_permitted is False

    for index, adapter in enumerate(adapters):
        if index > failing_index:
            assert adapter.calls == []
        else:
            assert "supports" in adapter.calls


def test_adapter_exception_does_not_escape_or_permit_execution() -> None:
    class ExplodingVerifyAdapter(FakeAdapter):
        def verify(
            self,
            context: EnforcementApplicationContext,
            plan: LinuxEnforcementPlan,
        ) -> EnforcementPrimitiveResult:
            del context, plan
            self.calls.append("verify")
            raise OSError("controlled verification exception")

    adapters = list(_all_adapters())
    adapters[0] = ExplodingVerifyAdapter(
        EnforcementPrimitive.NO_NEW_PRIVS,
    )

    application = LinuxEnforcementApplication(
        PrimitiveAdapterRegistry(tuple(adapters))
    )

    result = application.apply(_plan(), _context())

    assert result.status.value == "failed"
    assert result.execution_permitted is False
    assert "exception" in result.failure_reason


def test_empty_execution_id_is_rejected_by_context_contract() -> None:
    context = EnforcementApplicationContext.create(
        execution_id="temporary",
        backend_id="linux-test",
        started_at=datetime.now(UTC),
    )

    context_data = context.model_dump()
    context_data["execution_id"] = ""

    with pytest.raises(ValueError):
        EnforcementApplicationContext.model_validate(
            context_data,
        )


def test_no_required_primitive_plan_is_aborted() -> None:
    base = _plan()

    empty_plan = LinuxEnforcementPlan(
        status=base.status,
        isolation_level=base.isolation_level,
        privilege=base.privilege,
        namespaces=base.namespaces,
        cgroups=base.cgroups,
        filesystem=base.filesystem,
        network=base.network,
        environment=base.environment,
        seccomp=base.seccomp,
        landlock=base.landlock,
        apparmor=base.apparmor,
        requirements=(),
    )

    application = LinuxEnforcementApplication(
        PrimitiveAdapterRegistry(_all_adapters())
    )

    result = application.apply(
        empty_plan,
        _context(),
    )

    assert result.status.value == "aborted"
    assert result.execution_permitted is False
    assert "no required primitives" in result.failure_reason


def test_required_result_must_be_verified_before_execution() -> None:
    class AppliedVerifyAdapter(FakeAdapter):
        def verify(
            self,
            context: EnforcementApplicationContext,
            plan: LinuxEnforcementPlan,
        ) -> EnforcementPrimitiveResult:
            del context, plan
            self.calls.append("verify")
            return EnforcementPrimitiveResult(
                primitive=self._primitive,
                required=True,
                state=EnforcementState.APPLIED,
                success=True,
                reason="still only applied",
            )

    adapters = list(_all_adapters())
    adapters[0] = AppliedVerifyAdapter(
        EnforcementPrimitive.NO_NEW_PRIVS,
    )

    application = LinuxEnforcementApplication(
        PrimitiveAdapterRegistry(tuple(adapters))
    )

    result = application.apply(_plan(), _context())

    assert result.status.value == "failed"
    assert result.execution_permitted is False


def test_failure_reason_is_present_for_failed_result() -> None:
    adapters = _all_adapters(
        fail_verify=True,
    )

    application = LinuxEnforcementApplication(
        PrimitiveAdapterRegistry(adapters)
    )

    result = application.apply(_plan(), _context())

    assert result.status.value == "failed"
    assert result.failure_reason
    assert result.execution_permitted is False


def test_verified_result_contains_only_verified_required_primitives() -> None:
    adapters = _all_adapters()

    application = LinuxEnforcementApplication(
        PrimitiveAdapterRegistry(adapters)
    )

    result = application.apply(_plan(), _context())

    assert result.status.value == "verified"
    assert result.execution_permitted is True

    assert result.primitive_results

    assert all(
        item.required
        and item.success
        and item.state is EnforcementState.VERIFIED
        for item in result.primitive_results
    )

    assert all(
        evidence.observed_state is EnforcementState.VERIFIED
        for item in result.primitive_results
        for evidence in item.evidence
    )
