from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lyrion.core.types import ExecutionTarget
from lyrion.execution.backends.linux.enforcement import (
    EnforcementApplicationContext,
    EnforcementEvidence,
    EnforcementPrimitive,
    EnforcementPrimitiveResult,
    EnforcementState,
    LinuxEnforcementPlan,
    LinuxEnforcementPlanner,
    PrimitiveAdapter,
    PrimitiveAdapterRegistry,
)
from lyrion.execution.sandbox import SandboxConfig


class FakePrimitiveAdapter:
    def __init__(self, primitive: EnforcementPrimitive) -> None:
        self._primitive = primitive

    @property
    def primitive(self) -> EnforcementPrimitive:
        return self._primitive

    def supports(self, plan: LinuxEnforcementPlan) -> bool:
        return self._primitive in plan.required_primitives()

    def validate(
        self,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        return EnforcementPrimitiveResult(
            primitive=self._primitive,
            required=True,
            state=EnforcementState.PLANNED,
            success=True,
            reason="deterministic test validation",
        )

    def apply(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        return EnforcementPrimitiveResult(
            primitive=self._primitive,
            required=True,
            state=EnforcementState.APPLIED,
            success=True,
            reason="deterministic test application",
        )

    def verify(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        evidence = EnforcementEvidence.verified(
            primitive=self._primitive,
            evidence_type="test-verification",
            evidence_ref=f"test:{context.execution_id}",
            observation="verified by deterministic test adapter",
        )
        return EnforcementPrimitiveResult(
            primitive=self._primitive,
            required=True,
            state=EnforcementState.VERIFIED,
            success=True,
            reason="deterministic test verification succeeded",
            evidence=(evidence,),
        )

    def evidence(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> tuple[EnforcementEvidence, ...]:
        return (
            EnforcementEvidence.verified(
                primitive=self._primitive,
                evidence_type="test-evidence",
                evidence_ref=f"test:{context.execution_id}",
                observation="deterministic test evidence",
            ),
        )


def _context() -> EnforcementApplicationContext:
    return EnforcementApplicationContext.create(
        execution_id="exec-c22b",
        backend_id="linux-native",
        started_at=datetime.now(UTC),
    )


def _sandbox() -> SandboxConfig:
    return SandboxConfig(
        execution_target=ExecutionTarget.LOCAL_CPU,
        resource_limits={
            "max_runtime_seconds": 30.0,
            "max_memory_mb": 512,
            "max_output_bytes": 1_048_576,
            "max_cpu_seconds": 30.0,
        },
    )


def _plan() -> LinuxEnforcementPlan:
    return LinuxEnforcementPlan.rejected(
        sandbox=_sandbox(),
        reason="contract-test plan",
    )


def _valid_plan() -> LinuxEnforcementPlan:
    return LinuxEnforcementPlanner().plan(_sandbox())


def test_adapter_protocol_can_be_implemented() -> None:
    adapter: PrimitiveAdapter = FakePrimitiveAdapter(
        EnforcementPrimitive.NO_NEW_PRIVS
    )

    assert adapter.primitive is EnforcementPrimitive.NO_NEW_PRIVS
    assert adapter.supports(_valid_plan()) is True


def test_adapter_lifecycle_preserves_state_boundaries() -> None:
    adapter = FakePrimitiveAdapter(EnforcementPrimitive.NO_NEW_PRIVS)
    plan = _valid_plan()
    context = _context()

    validation = adapter.validate(plan)
    applied = adapter.apply(context, plan)
    verified = adapter.verify(context, plan)

    assert validation.state is EnforcementState.PLANNED
    assert applied.state is EnforcementState.APPLIED
    assert verified.state is EnforcementState.VERIFIED
    assert validation.success
    assert applied.success
    assert verified.success
    assert verified.evidence


def test_registry_resolves_registered_adapter() -> None:
    adapter = FakePrimitiveAdapter(EnforcementPrimitive.NO_NEW_PRIVS)
    registry = PrimitiveAdapterRegistry([adapter])

    assert len(registry) == 1
    assert registry.contains(EnforcementPrimitive.NO_NEW_PRIVS)
    assert registry.resolve(EnforcementPrimitive.NO_NEW_PRIVS) is adapter


def test_registry_identifiers_are_deterministic() -> None:
    adapters = [
        FakePrimitiveAdapter(EnforcementPrimitive.SECCOMP),
        FakePrimitiveAdapter(EnforcementPrimitive.CGROUPS_V2),
        FakePrimitiveAdapter(EnforcementPrimitive.NO_NEW_PRIVS),
    ]
    registry = PrimitiveAdapterRegistry(adapters)

    assert registry.identifiers() == (
        EnforcementPrimitive.NO_NEW_PRIVS,
        EnforcementPrimitive.CGROUPS_V2,
        EnforcementPrimitive.SECCOMP,
    )


def test_registry_rejects_duplicate_primitive() -> None:
    primitive = EnforcementPrimitive.NO_NEW_PRIVS

    with pytest.raises(ValueError, match="Duplicate primitive"):
        PrimitiveAdapterRegistry(
            [
                FakePrimitiveAdapter(primitive),
                FakePrimitiveAdapter(primitive),
            ]
        )


def test_registry_rejects_unregistered_primitive() -> None:
    registry = PrimitiveAdapterRegistry(
        [FakePrimitiveAdapter(EnforcementPrimitive.NO_NEW_PRIVS)]
    )

    with pytest.raises(KeyError, match="No adapter registered"):
        registry.resolve(EnforcementPrimitive.SECCOMP)


def test_registry_isolated_from_external_mutation() -> None:
    adapters = [
        FakePrimitiveAdapter(EnforcementPrimitive.NO_NEW_PRIVS),
    ]
    registry = PrimitiveAdapterRegistry(adapters)

    adapters.clear()

    assert registry.contains(EnforcementPrimitive.NO_NEW_PRIVS)
    assert len(registry) == 1


def test_evidence_collection_is_separate_from_apply() -> None:
    adapter = FakePrimitiveAdapter(EnforcementPrimitive.NO_NEW_PRIVS)
    context = _context()
    plan = _valid_plan()

    applied = adapter.apply(context, plan)
    evidence = adapter.evidence(context, plan)

    assert applied.state is EnforcementState.APPLIED
    assert applied.evidence == ()
    assert evidence
    assert evidence[0].observed_state is EnforcementState.VERIFIED
