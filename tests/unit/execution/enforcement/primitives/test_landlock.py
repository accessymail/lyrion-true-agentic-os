"""Deterministic tests for the C2.2-C7-R2 Landlock adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from lyrion.execution.backends.linux.enforcement.application import (
    EnforcementApplicationContext,
)
from lyrion.execution.backends.linux.enforcement.contracts import (
    AppArmorPlan,
    CgroupPlan,
    EnforcementPlanStatus,
    EnforcementPrimitive,
    EnforcementRequirement,
    EnforcementState,
    EnvironmentPlan,
    FilesystemPlan,
    LandlockPlan,
    LinuxEnforcementPlan,
    NamespacePlan,
    NetworkPlan,
    PrivilegePlan,
    SeccompPlan,
)
from lyrion.execution.backends.linux.enforcement.landlock_policy import (
    LandlockAbiCapabilities,
    LandlockFilesystemAccess,
    LandlockPolicy,
)
from lyrion.execution.backends.linux.enforcement.primitives.landlock import (
    LandlockAdapter,
    LandlockState,
)
from lyrion.execution.sandbox import (
    EnvironmentMode,
    FilesystemMode,
    IsolationLevel,
    NetworkMode,
)


@dataclass
class FakeLandlockOperations:
    """Deterministic non-host-mutating Landlock operation double."""

    abi_version: int = 7
    state: LandlockState = field(
        default_factory=lambda: LandlockState(
            installed=False,
            abi_version=None,
            policy_id=None,
            policy_version=None,
            filesystem_paths=(),
        )
    )
    install_calls: list[tuple[LandlockPolicy, FilesystemPlan]] = field(
        default_factory=list
    )

    @property
    def capabilities(self) -> LandlockAbiCapabilities:
        return LandlockAbiCapabilities(
            abi_version=self.abi_version,
            filesystem_access=(
                LandlockFilesystemAccess.EXECUTE
                | LandlockFilesystemAccess.WRITE_FILE
                | LandlockFilesystemAccess.READ_FILE
                | LandlockFilesystemAccess.READ_DIR
                | LandlockFilesystemAccess.REMOVE_DIR
                | LandlockFilesystemAccess.REMOVE_FILE
                | LandlockFilesystemAccess.MAKE_DIR
                | LandlockFilesystemAccess.MAKE_REG
                | LandlockFilesystemAccess.MAKE_SOCK
                | LandlockFilesystemAccess.MAKE_FIFO
                | LandlockFilesystemAccess.MAKE_SYM
                | LandlockFilesystemAccess.REFER
                | LandlockFilesystemAccess.TRUNCATE
                | LandlockFilesystemAccess.IOCTL_DEV
            ),
        )

    def get_capabilities(self) -> LandlockAbiCapabilities:
        return self.capabilities

    def install_policy(
        self,
        policy: LandlockPolicy,
        filesystem: FilesystemPlan,
    ) -> None:
        self.install_calls.append((policy, filesystem))
        self.state = LandlockState(
            installed=True,
            abi_version=self.abi_version,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            filesystem_paths=(
                *filesystem.writable_paths,
                *filesystem.read_only_paths,
            ),
        )

    def get_state(self) -> LandlockState:
        return self.state


def _policy() -> LandlockPolicy:
    return LandlockPolicy(
        policy_id="LYRION-TEST-LANDLOCK",
        policy_version="1.0.0",
        minimum_abi=1,
        handled_access_fs=(
            LandlockFilesystemAccess.READ_FILE
            | LandlockFilesystemAccess.READ_DIR
            | LandlockFilesystemAccess.WRITE_FILE
            | LandlockFilesystemAccess.MAKE_DIR
            | LandlockFilesystemAccess.MAKE_REG
        ),
        default_allowed_access_fs=(
            LandlockFilesystemAccess.READ_FILE
            | LandlockFilesystemAccess.READ_DIR
        ),
    )


def _context() -> EnforcementApplicationContext:
    return EnforcementApplicationContext.create(
        execution_id="test-execution",
        backend_id="linux",
        started_at=datetime.now(UTC),
    )


def _plan(required: bool = True) -> LinuxEnforcementPlan:
    requirements = (
        EnforcementRequirement(
            primitive=EnforcementPrimitive.LANDLOCK,
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
            required=required,
            mode=(
                FilesystemMode.ISOLATED
                if required
                else FilesystemMode.NONE
            ),
            writable_paths=("/workspace",) if required else (),
            read_only_paths=("/usr",) if required else (),
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
        seccomp=SeccompPlan(required=False),
        landlock=LandlockPlan(required=required),
        apparmor=AppArmorPlan(required=False),
        requirements=requirements,
    )


def test_primitive_identity() -> None:
    adapter = LandlockAdapter(
        policy=_policy(),
        operations=FakeLandlockOperations(),
    )

    assert adapter.primitive is EnforcementPrimitive.LANDLOCK


def test_supports_present_requirement() -> None:
    adapter = LandlockAdapter(
        policy=_policy(),
        operations=FakeLandlockOperations(),
    )

    assert adapter.supports(_plan()) is True


def test_validate_required_policy() -> None:
    adapter = LandlockAdapter(
        policy=_policy(),
        operations=FakeLandlockOperations(),
    )

    result = adapter.validate(_plan())

    assert result.state is EnforcementState.SUPPORTED
    assert result.success is True


def test_apply_reports_applied_not_verified() -> None:
    operations = FakeLandlockOperations()
    adapter = LandlockAdapter(
        policy=_policy(),
        operations=operations,
    )

    result = adapter.apply(_context(), _plan())

    assert result.state is EnforcementState.APPLIED
    assert result.success is True
    assert operations.install_calls == [
        (
            _policy(),
            _plan().filesystem,
        )
    ]


def test_verify_independently_reports_verified() -> None:
    operations = FakeLandlockOperations()
    adapter = LandlockAdapter(
        policy=_policy(),
        operations=operations,
    )

    adapter.apply(_context(), _plan())

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.VERIFIED
    assert result.success is True
    assert len(result.evidence) == 2
    assert all(
        evidence.primitive is EnforcementPrimitive.LANDLOCK
        for evidence in result.evidence
    )
    assert {
        evidence.evidence_type
        for evidence in result.evidence
    } == {
        "landlock_runtime_state",
        "landlock_policy_attestation",
    }


def test_verify_fails_when_ruleset_is_not_installed() -> None:
    adapter = LandlockAdapter(
        policy=_policy(),
        operations=FakeLandlockOperations(),
    )

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "not installed" in result.reason


def test_verify_fails_when_abi_is_below_requirement() -> None:
    operations = FakeLandlockOperations(
        abi_version=0,
        state=LandlockState(
            installed=True,
            abi_version=0,
            policy_id=_policy().policy_id,
            policy_version=_policy().policy_version,
        ),
    )

    adapter = LandlockAdapter(
        policy=_policy(),
        operations=operations,
    )

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert "ABI requirement is unsupported" in result.reason


def test_verify_rejects_policy_identity_mismatch() -> None:
    operations = FakeLandlockOperations(
        state=LandlockState(
            installed=True,
            abi_version=7,
            policy_id="OTHER-POLICY",
            policy_version="1.0.0",
        )
    )

    adapter = LandlockAdapter(
        policy=_policy(),
        operations=operations,
    )

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert "policy identity mismatch" in result.reason


def test_verify_rejects_policy_version_mismatch() -> None:
    operations = FakeLandlockOperations(
        state=LandlockState(
            installed=True,
            abi_version=7,
            policy_id=_policy().policy_id,
            policy_version="9.9.9",
        )
    )

    adapter = LandlockAdapter(
        policy=_policy(),
        operations=operations,
    )

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert "policy version mismatch" in result.reason


def test_evidence_is_empty_when_verification_fails() -> None:
    adapter = LandlockAdapter(
        policy=_policy(),
        operations=FakeLandlockOperations(),
    )

    assert adapter.evidence(_context(), _plan()) == ()


def test_non_required_landlock_does_not_install_control() -> None:
    operations = FakeLandlockOperations()
    adapter = LandlockAdapter(
        policy=_policy(),
        operations=operations,
    )

    result = adapter.apply(_context(), _plan(required=False))

    assert result.state is EnforcementState.APPLIED
    assert result.success is True
    assert operations.install_calls == []


def test_non_required_landlock_verifies_without_control() -> None:
    operations = FakeLandlockOperations()
    adapter = LandlockAdapter(
        policy=_policy(),
        operations=operations,
    )

    result = adapter.verify(_context(), _plan(required=False))

    assert result.state is EnforcementState.VERIFIED
    assert result.success is True
    assert len(result.evidence) == 1
    assert result.evidence[0].evidence_type == "landlock_not_required"


def test_missing_requirement_fails_closed() -> None:
    adapter = LandlockAdapter(
        policy=_policy(),
        operations=FakeLandlockOperations(),
    )

    plan = _plan().model_copy(update={"requirements": ()})

    result = adapter.validate(plan)

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "requirement is missing" in result.reason


def test_requirement_mismatch_fails_closed() -> None:
    adapter = LandlockAdapter(
        policy=_policy(),
        operations=FakeLandlockOperations(),
    )

    plan = _plan().model_copy(
        update={
            "requirements": (
                EnforcementRequirement(
                    primitive=EnforcementPrimitive.LANDLOCK,
                    required=False,
                    state=EnforcementState.PLANNED,
                    reason="inconsistent test",
                ),
            )
        }
    )

    result = adapter.validate(plan)

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "inconsistent" in result.reason


def test_missing_filesystem_boundary_fails_closed() -> None:
    adapter = LandlockAdapter(
        policy=_policy(),
        operations=FakeLandlockOperations(),
    )

    plan = _plan().model_copy(
        update={
            "filesystem": FilesystemPlan(
                required=False,
                mode=FilesystemMode.NONE,
                writable_paths=(),
                read_only_paths=(),
            ),
            "landlock": LandlockPlan(required=True),
            "requirements": (
                EnforcementRequirement(
                    primitive=EnforcementPrimitive.LANDLOCK,
                    required=True,
                    state=EnforcementState.PLANNED,
                    reason="test",
                ),
            ),
        }
    )

    result = adapter.validate(plan)

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "filesystem enforcement boundary" in result.reason


def test_operations_failure_is_fail_closed() -> None:
    class FailingOperations(FakeLandlockOperations):
        def install_policy(
            self,
            policy: LandlockPolicy,
            filesystem: FilesystemPlan,
        ) -> None:
            raise RuntimeError("injected failure")

    adapter = LandlockAdapter(
        policy=_policy(),
        operations=FailingOperations(),
    )

    result = adapter.apply(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "application failed" in result.reason
