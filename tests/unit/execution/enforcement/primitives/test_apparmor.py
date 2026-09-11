"""Tests for the AppArmor primitive adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from lyrion.execution.backends.linux.enforcement.apparmor_policy import (
    AppArmorPolicy,
)
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
    EnvironmentMode,
    EnvironmentPlan,
    FilesystemMode,
    FilesystemPlan,
    IsolationLevel,
    LandlockPlan,
    LinuxEnforcementPlan,
    NamespacePlan,
    NetworkMode,
    NetworkPlan,
    PrivilegePlan,
    SeccompPlan,
)
from lyrion.execution.backends.linux.enforcement.primitives.apparmor import (
    AppArmorAdapter,
    AppArmorState,
    NativeAppArmorOperations,
)


class FakeAppArmorOperations:
    """Deterministic host-operation test double."""

    def __init__(
        self,
        *,
        supported: bool = True,
        loaded: bool = False,
        enforcing: bool = False,
        profile_name: str | None = None,
        profile_version: str | None = None,
    ) -> None:
        self.supported = supported
        self.loaded = loaded
        self.enforcing = enforcing
        self.profile_name = profile_name
        self.profile_version = profile_version
        self.load_count = 0

    def supports(self) -> bool:
        return self.supported

    def load_profile(self, policy: AppArmorPolicy) -> None:
        self.load_count += 1
        self.loaded = True
        self.enforcing = True
        self.profile_name = policy.profile_name
        self.profile_version = policy.policy_version

    def get_state(self, profile_name: str) -> AppArmorState:
        return AppArmorState(
            loaded=self.loaded,
            enforcing=self.enforcing,
            profile_name=self.profile_name,
            profile_version=self.profile_version,
        )


def make_policy() -> AppArmorPolicy:
    return AppArmorPolicy(
        profile_name="lyrion-test",
        policy_version="1.0.0",
        profile_text="""profile lyrion-test {
    /usr/bin/python3 rix,
}
""",
    )


def make_plan(*, required: bool = True) -> LinuxEnforcementPlan:
    requirements = tuple(
        EnforcementRequirement(
            primitive=primitive,
            state=EnforcementState.PLANNED,
            required=required if primitive is EnforcementPrimitive.APPARMOR
            else True,
            reason="test requirement",
        )
        for primitive in EnforcementPrimitive
    )

    return LinuxEnforcementPlan(
        status=EnforcementPlanStatus.READY,
        isolation_level=IsolationLevel.STRICT,
        privilege=PrivilegePlan(
            no_new_privs_required=True,
            capability_reduction_required=True,
        ),
        namespaces=NamespacePlan(
            required=True,
            process_isolation=True,
            mount_isolation=True,
            network_isolation=True,
        ),
        cgroups=CgroupPlan(
            required=True,
            max_runtime_seconds=30.0,
            max_memory_mb=512,
            max_output_bytes=1_048_576,
            max_cpu_seconds=30.0,
        ),
        filesystem=FilesystemPlan(
            required=True,
            mode=FilesystemMode.ISOLATED,
            writable_paths=(),
            read_only_paths=(),
        ),
        network=NetworkPlan(
            required=True,
            mode=NetworkMode.DISABLED,
            network_access_allowed=False,
        ),
        environment=EnvironmentPlan(
            mode=EnvironmentMode.EMPTY,
            allowed_keys=(),
        ),
        seccomp=SeccompPlan(required=True),
        landlock=LandlockPlan(required=True),
        apparmor=AppArmorPlan(required=required),
        requirements=requirements,
    )


def make_context() -> EnforcementApplicationContext:
    return EnforcementApplicationContext.create(
        execution_id="test-execution",
        backend_id="linux",
        started_at=datetime.now(UTC),
    )


def test_supports_required_apparmor() -> None:
    operations = FakeAppArmorOperations()
    adapter = AppArmorAdapter(
        policy=make_policy(),
        operations=operations,
    )

    assert adapter.supports(make_plan())


def test_required_apparmor_fails_when_unsupported() -> None:
    operations = FakeAppArmorOperations(supported=False)
    adapter = AppArmorAdapter(
        policy=make_policy(),
        operations=operations,
    )

    result = adapter.validate(make_plan())

    assert not result.success
    assert result.state is EnforcementState.FAILED


def test_apply_reports_applied_not_verified() -> None:
    operations = FakeAppArmorOperations()
    adapter = AppArmorAdapter(
        policy=make_policy(),
        operations=operations,
    )

    result = adapter.apply(
        make_context(),
        make_plan(),
    )

    assert result.success
    assert result.state is EnforcementState.APPLIED
    assert operations.load_count == 1


def test_verify_requires_loaded_profile() -> None:
    operations = FakeAppArmorOperations()
    adapter = AppArmorAdapter(
        policy=make_policy(),
        operations=operations,
    )

    result = adapter.verify(
        make_context(),
        make_plan(),
    )

    assert not result.success
    assert result.state is EnforcementState.FAILED


def test_verify_requires_enforcing_profile() -> None:
    operations = FakeAppArmorOperations(
        loaded=True,
        enforcing=False,
        profile_name="lyrion-test",
        profile_version="1.0.0",
    )
    adapter = AppArmorAdapter(
        policy=make_policy(),
        operations=operations,
    )

    result = adapter.verify(
        make_context(),
        make_plan(),
    )

    assert not result.success


def test_verify_requires_matching_profile_identity() -> None:
    operations = FakeAppArmorOperations(
        loaded=True,
        enforcing=True,
        profile_name="different-profile",
        profile_version="1.0.0",
    )
    adapter = AppArmorAdapter(
        policy=make_policy(),
        operations=operations,
    )

    result = adapter.verify(
        make_context(),
        make_plan(),
    )

    assert not result.success


def test_successful_verification_provides_positive_evidence() -> None:
    operations = FakeAppArmorOperations(
        loaded=True,
        enforcing=True,
        profile_name="lyrion-test",
        profile_version="1.0.0",
    )
    adapter = AppArmorAdapter(
        policy=make_policy(),
        operations=operations,
    )

    result = adapter.verify(
        make_context(),
        make_plan(),
    )

    assert result.success
    assert result.state is EnforcementState.VERIFIED
    assert len(result.evidence) == 2
    assert all(
        item.primitive is EnforcementPrimitive.APPARMOR
        for item in result.evidence
    )


def test_evidence_is_empty_when_verification_fails() -> None:
    operations = FakeAppArmorOperations()
    adapter = AppArmorAdapter(
        policy=make_policy(),
        operations=operations,
    )

    assert adapter.evidence(
        make_context(),
        make_plan(),
    ) == ()


def test_optional_apparmor_can_apply_without_host_mutation() -> None:
    operations = FakeAppArmorOperations(supported=False)
    adapter = AppArmorAdapter(
        policy=make_policy(),
        operations=operations,
    )

    plan = make_plan(required=False)

    result = adapter.apply(
        make_context(),
        plan,
    )

    assert result.success
    assert result.state is EnforcementState.APPLIED
    assert operations.load_count == 0


def test_optional_apparmor_verifies_without_profile() -> None:
    operations = FakeAppArmorOperations(supported=False)
    adapter = AppArmorAdapter(
        policy=make_policy(),
        operations=operations,
    )

    result = adapter.verify(
        make_context(),
        make_plan(required=False),
    )

    assert result.success
    assert result.state is EnforcementState.VERIFIED


def test_missing_requirement_fails_closed() -> None:
    operations = FakeAppArmorOperations()
    adapter = AppArmorAdapter(
        policy=make_policy(),
        operations=operations,
    )

    plan = make_plan()
    plan = plan.model_copy(update={"requirements": ()})

    result = adapter.validate(plan)

    assert not result.success
    assert result.state is EnforcementState.FAILED


def test_native_loader_fails_closed_when_unsupported() -> None:
    operations = AppArmorAdapter(
        policy=make_policy(),
        operations=NativeAppArmorOperations(),
    )

    plan = make_plan()

    result = operations.apply(
        make_context(),
        plan,
    )

    assert not result.success
    assert result.state is EnforcementState.FAILED



def test_native_loader_invokes_parser_add_only() -> None:
    policy = make_policy()
    operations = NativeAppArmorOperations()

    class SupportedOperations(NativeAppArmorOperations):
        def supports(self) -> bool:
            return True

    operations = SupportedOperations()

    completed = type(
        "Completed",
        (),
        {
            "returncode": 0,
            "stdout": "",
            "stderr": "",
        },
    )()

    with patch(
        "lyrion.execution.backends.linux.enforcement.primitives.apparmor.subprocess.run",
        return_value=completed,
    ) as run:
        operations.load_profile(policy)

    run.assert_called_once()

    command = run.call_args.args[0]

    assert command[0] == operations._PARSER
    assert command[1] == "--add"
    assert command[2].endswith(".profile")
    assert "--replace" not in command
    assert run.call_args.kwargs.get("shell", False) is False


def test_native_loader_fails_closed_on_parser_failure() -> None:
    policy = make_policy()

    class SupportedOperations(NativeAppArmorOperations):
        def supports(self) -> bool:
            return True

    operations = SupportedOperations()

    completed = type(
        "Completed",
        (),
        {
            "returncode": 1,
            "stdout": "",
            "stderr": "controlled parser failure",
        },
    )()

    with patch(
        "lyrion.execution.backends.linux.enforcement.primitives.apparmor.subprocess.run",
        return_value=completed,
    ):
        try:
            operations.load_profile(policy)
        except RuntimeError as exc:
            assert "controlled parser failure" in str(exc)
        else:
            raise AssertionError(
                "Parser failure must fail closed."
            )
