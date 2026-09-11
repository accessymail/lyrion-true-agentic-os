"""Deterministic tests for the C2.2-C6-R2 Seccomp adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from lyrion.execution.backends.linux.enforcement.application import (
    EnforcementApplicationContext,
)
from lyrion.execution.backends.linux.enforcement.contracts import (
    EnforcementPrimitive,
    EnforcementState,
    LinuxEnforcementPlan,
)
from lyrion.execution.backends.linux.enforcement.primitives.seccomp import (
    SeccompAdapter,
    SeccompState,
)
from lyrion.execution.backends.linux.enforcement.seccomp_policy import (
    SeccompArchitecture,
    SeccompDefaultAction,
    SeccompPolicy,
)


@dataclass
class FakeSeccompOperations:
    """Deterministic non-host-mutating Seccomp operation double."""

    state: SeccompState = field(
        default_factory=lambda: SeccompState(
            architecture=None,
            installed=False,
            seccomp_mode=0,
            filter_count=0,
        )
    )
    install_calls: list[SeccompPolicy] = field(default_factory=list)

    def install_policy(self, policy: SeccompPolicy) -> None:
        self.install_calls.append(policy)
        self.state = SeccompState(
            architecture=policy.architecture.value,
            installed=True,
            seccomp_mode=2,
            filter_count=1,
        )

    def get_state(self) -> SeccompState:
        return self.state


def _policy() -> SeccompPolicy:
    return SeccompPolicy(
        policy_id="LYRION-TEST-SECCOMP",
        policy_version="1.0.0",
        architecture=SeccompArchitecture.X86_64,
        default_action=SeccompDefaultAction.KILL_PROCESS,
        allowed_syscalls=("read", "write", "close", "exit_group"),
    )


def _context() -> EnforcementApplicationContext:
    return EnforcementApplicationContext.create(
        execution_id="test-execution",
        backend_id="linux",
        started_at=datetime.now(UTC),
    )


def _plan(required: bool = True) -> LinuxEnforcementPlan:
    from lyrion.execution.backends.linux.enforcement.contracts import (
        AppArmorPlan,
        CgroupPlan,
        EnforcementPlanStatus,
        EnforcementRequirement,
        EnforcementState,
        EnvironmentPlan,
        FilesystemPlan,
        LandlockPlan,
        NamespacePlan,
        NetworkPlan,
        PrivilegePlan,
        SeccompPlan,
    )
    from lyrion.execution.sandbox import (
        EnvironmentMode,
        FilesystemMode,
        IsolationLevel,
        NetworkMode,
    )

    requirements = (
        EnforcementRequirement(
            primitive=EnforcementPrimitive.SECCOMP,
            required=required,
            state=EnforcementState.PLANNED,
            reason="test",
        ),
    )

    return LinuxEnforcementPlan(
        status=EnforcementPlanStatus.READY,
        isolation_level=IsolationLevel.STRICT,
        privilege=PrivilegePlan(
            no_new_privs_required=False,
            capability_reduction_required=False,
        ),
        namespaces=NamespacePlan(
            required=False,
            process_isolation=False,
            mount_isolation=False,
            network_isolation=False,
        ),
        cgroups=CgroupPlan(
            required=False,
            max_runtime_seconds=1.0,
            max_memory_mb=16,
            max_output_bytes=1024,
            max_cpu_seconds=1.0,
        ),
        filesystem=FilesystemPlan(
            required=False,
            mode=FilesystemMode.NONE,
            writable_paths=(),
            read_only_paths=(),
        ),
        network=NetworkPlan(
            required=False,
            mode=NetworkMode.ENABLED,
            network_access_allowed=True,
        ),
        environment=EnvironmentPlan(
            mode=EnvironmentMode.INHERITED,
            allowed_keys=(),
        ),
        seccomp=SeccompPlan(required=required),
        landlock=LandlockPlan(required=False),
        apparmor=AppArmorPlan(required=False),
        requirements=requirements,
    )


def test_primitive_identity() -> None:
    adapter = SeccompAdapter(
        policy=_policy(),
        operations=FakeSeccompOperations(),
    )

    assert adapter.primitive is EnforcementPrimitive.SECCOMP


def test_supports_present_requirement() -> None:
    adapter = SeccompAdapter(
        policy=_policy(),
        operations=FakeSeccompOperations(),
    )

    assert adapter.supports(_plan()) is True


def test_validate_required_policy() -> None:
    adapter = SeccompAdapter(
        policy=_policy(),
        operations=FakeSeccompOperations(),
    )

    result = adapter.validate(_plan())

    assert result.state is EnforcementState.SUPPORTED
    assert result.success is True


def test_apply_reports_applied_not_verified() -> None:
    operations = FakeSeccompOperations()
    adapter = SeccompAdapter(
        policy=_policy(),
        operations=operations,
    )

    result = adapter.apply(_context(), _plan())

    assert result.state is EnforcementState.APPLIED
    assert result.success is True
    assert operations.install_calls == [_policy()]


def test_verify_independently_reports_verified() -> None:
    operations = FakeSeccompOperations()
    adapter = SeccompAdapter(
        policy=_policy(),
        operations=operations,
    )

    adapter.apply(_context(), _plan())
    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.VERIFIED
    assert result.success is True
    assert len(result.evidence) == 2
    assert all(
        evidence.primitive is EnforcementPrimitive.SECCOMP
        for evidence in result.evidence
    )
    assert {
        evidence.evidence_type
        for evidence in result.evidence
    } == {
        "seccomp_kernel_state",
        "seccomp_policy_attestation",
    }


def test_verify_fails_when_filter_is_not_installed() -> None:
    adapter = SeccompAdapter(
        policy=_policy(),
        operations=FakeSeccompOperations(),
    )

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "Seccomp mode verification failed" in result.reason
    assert "expected 2, observed 0" in result.reason


def test_verify_rejects_tampered_policy_attestation() -> None:
    policy = _policy()

    from lyrion.execution.backends.linux.enforcement.seccomp_attestation import (
        SeccompPolicyAttestation,
        attest_policy,
    )

    valid = attest_policy(policy)

    tampered = SeccompPolicyAttestation(
        policy_id="OTHER-POLICY",
        policy_version=valid.policy_version,
        policy_digest=valid.policy_digest,
        architecture=valid.architecture,
    )

    operations = FakeSeccompOperations(
        state=SeccompState(
            architecture="x86_64",
            installed=True,
            seccomp_mode=2,
            filter_count=1,
        )
    )

    adapter = SeccompAdapter(
        policy=policy,
        operations=operations,
        attestation=tampered,
    )

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert "attestation" in result.reason.lower()


def test_verify_rejects_tampered_policy_version_attestation() -> None:
    policy = _policy()

    from lyrion.execution.backends.linux.enforcement.seccomp_attestation import (
        SeccompPolicyAttestation,
        attest_policy,
    )

    valid = attest_policy(policy)

    tampered = SeccompPolicyAttestation(
        policy_id=valid.policy_id,
        policy_version="9.9.9",
        policy_digest=valid.policy_digest,
        architecture=valid.architecture,
    )

    operations = FakeSeccompOperations(
        state=SeccompState(
            architecture="x86_64",
            installed=True,
            seccomp_mode=2,
            filter_count=1,
        )
    )

    adapter = SeccompAdapter(
        policy=policy,
        operations=operations,
        attestation=tampered,
    )

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert "attestation" in result.reason.lower()


def test_verify_rejects_wrong_architecture() -> None:
    operations = FakeSeccompOperations(
        state=SeccompState(
            architecture="aarch64",
            installed=True,
            seccomp_mode=2,
            filter_count=1,
        )
    )

    adapter = SeccompAdapter(
        policy=_policy(),
        operations=operations,
    )

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert "architecture" in result.reason


def test_evidence_delegates_to_independent_verification() -> None:
    operations = FakeSeccompOperations()
    adapter = SeccompAdapter(
        policy=_policy(),
        operations=operations,
    )

    adapter.apply(_context(), _plan())

    evidence = adapter.evidence(
        _context(),
        _plan(),
    )

    assert len(evidence) == 2
    assert all(
        item.observed_state is EnforcementState.VERIFIED
        for item in evidence
    )


def test_required_plan_cannot_have_mismatched_requirement() -> None:
    plan = _plan(required=True)

    requirements = tuple(
        requirement
        if requirement.primitive is not EnforcementPrimitive.SECCOMP
        else requirement.model_copy(update={"required": False})
        for requirement in plan.requirements
    )

    mismatched = plan.model_copy(
        update={"requirements": requirements},
    )

    adapter = SeccompAdapter(
        policy=_policy(),
        operations=FakeSeccompOperations(),
    )

    result = adapter.validate(mismatched)

    assert result.state is EnforcementState.FAILED
    assert "inconsistent" in result.reason


def test_non_required_seccomp_is_planned() -> None:
    adapter = SeccompAdapter(
        policy=_policy(),
        operations=FakeSeccompOperations(),
    )

    result = adapter.validate(_plan(required=False))

    assert result.state is EnforcementState.PLANNED
    assert result.success is True


def test_non_required_seccomp_does_not_install() -> None:
    operations = FakeSeccompOperations()
    adapter = SeccompAdapter(
        policy=_policy(),
        operations=operations,
    )

    result = adapter.apply(
        _context(),
        _plan(required=False),
    )

    assert result.state is EnforcementState.APPLIED
    assert operations.install_calls == []
