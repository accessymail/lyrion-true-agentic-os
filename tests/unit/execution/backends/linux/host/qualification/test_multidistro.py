from __future__ import annotations

import pytest

from lyrion.execution.backends.linux.host.contracts import (
    CapabilityState,
    HostPrimitive,
    HostPrimitiveCapability,
    LinuxHostAbstractionSnapshot,
    LinuxHostFingerprint,
    LinuxHostIdentity,
)
from lyrion.execution.backends.linux.host.negotiation.contracts import (
    CapabilityNegotiationStatus,
    CapabilityRequirement,
    CapabilityRequirementMode,
    CapabilityRequirementSet,
)
from lyrion.execution.backends.linux.host.profiles.contracts import (
    LinuxArchitecture,
    LinuxDistribution,
    LinuxDistributionFamily,
)
from lyrion.execution.backends.linux.host.qualification import (
    MultiDistributionQualificationEngine,
    MultiDistributionQualificationError,
)


def _snapshot(
    *,
    os_name: str = "Ubuntu",
    os_version: str = "26.04",
    architecture: str = "x86_64",
    capabilities: tuple[HostPrimitiveCapability, ...] = (),
) -> LinuxHostAbstractionSnapshot:
    identity = LinuxHostIdentity(
        os_name=os_name,
        os_version=os_version,
        kernel="6.18.0-test",
        architecture=architecture,
        virtualization="vmware",
        init_system="systemd",
    )

    return LinuxHostAbstractionSnapshot(
        identity=identity,
        fingerprint=LinuxHostFingerprint(
            identity=identity,
            primitives=tuple(
                sorted(
                    capabilities,
                    key=lambda item: item.primitive.value,
                )
            ),
        ),
        user_id=1000,
        effective_capabilities=(),
        namespaces=(),
        notes=(),
    )


def _requirements(
    *,
    mode: CapabilityRequirementMode = CapabilityRequirementMode.REQUIRED,
) -> CapabilityRequirementSet:
    return CapabilityRequirementSet(
        requirements=(
            CapabilityRequirement(
                requirement_id="qualification-landlock",
                primitive=HostPrimitive.LANDLOCK,
                mode=mode,
                acceptable_states=(CapabilityState.AVAILABLE,),
                rationale="Native host qualification requirement.",
            ),
        ),
    )


def _available_landlock() -> HostPrimitiveCapability:
    return HostPrimitiveCapability(
        primitive=HostPrimitive.LANDLOCK,
        state=CapabilityState.AVAILABLE,
        evidence=("runtime_abi=7",),
    )


@pytest.mark.parametrize(
    ("os_name", "expected"),
    [
        ("Ubuntu", LinuxDistribution.UBUNTU),
        ("Debian", LinuxDistribution.DEBIAN),
        ("Linux Mint", LinuxDistribution.LINUX_MINT),
        ("Kali", LinuxDistribution.KALI),
        ("Parrot", LinuxDistribution.PARROT),
        ("MX", LinuxDistribution.MX),
        ("Raspios", LinuxDistribution.RASPBERRY_PI_OS),
    ],
)
def test_known_debian_family_hosts_are_profiled(
    os_name: str,
    expected: LinuxDistribution,
) -> None:
    result = MultiDistributionQualificationEngine().qualify(
        host_snapshot=_snapshot(
            os_name=os_name,
            capabilities=(_available_landlock(),),
        ),
        requirements=_requirements(),
    )

    assert result.profile.distribution.distribution is expected
    assert (
        result.profile.distribution.family
        is LinuxDistributionFamily.DEBIAN
    )
    assert result.status is CapabilityNegotiationStatus.QUALIFIED
    assert result.qualified is True


def test_architecture_is_part_of_profile_identity() -> None:
    result = MultiDistributionQualificationEngine().qualify(
        host_snapshot=_snapshot(
            architecture="aarch64",
            capabilities=(_available_landlock(),),
        ),
        requirements=_requirements(),
    )

    assert (
        result.profile.architecture.architecture
        is LinuxArchitecture.AARCH64
    )
    assert result.profile.architecture.raw_value == "aarch64"


def test_unknown_distribution_is_not_automatically_blocked() -> None:
    result = MultiDistributionQualificationEngine().qualify(
        host_snapshot=_snapshot(
            os_name="Example Linux",
            capabilities=(_available_landlock(),),
        ),
        requirements=_requirements(),
    )

    assert (
        result.profile.distribution.distribution
        is LinuxDistribution.OTHER
    )
    assert (
        result.profile.distribution.family
        is LinuxDistributionFamily.OTHER
    )
    assert result.status is CapabilityNegotiationStatus.QUALIFIED


def test_distribution_name_does_not_create_capability() -> None:
    result = MultiDistributionQualificationEngine().qualify(
        host_snapshot=_snapshot(os_name="Ubuntu"),
        requirements=_requirements(),
    )

    assert result.status is CapabilityNegotiationStatus.BLOCKED
    assert result.blocked is True


def test_missing_required_capability_blocks_all_distributions() -> None:
    engine = MultiDistributionQualificationEngine()

    for os_name in (
        "Ubuntu",
        "Debian",
        "Linux Mint",
        "Kali",
        "Parrot",
        "MX",
        "Raspios",
    ):
        result = engine.qualify(
            host_snapshot=_snapshot(os_name=os_name),
            requirements=_requirements(),
        )

        assert result.status is CapabilityNegotiationStatus.BLOCKED


def test_optional_missing_capability_degrades_all_distributions() -> None:
    engine = MultiDistributionQualificationEngine()

    for os_name in ("Ubuntu", "Debian", "Kali", "Parrot"):
        result = engine.qualify(
            host_snapshot=_snapshot(os_name=os_name),
            requirements=_requirements(
                mode=CapabilityRequirementMode.OPTIONAL,
            ),
        )

        assert result.status is CapabilityNegotiationStatus.DEGRADED


def test_supported_capability_is_not_implicitly_qualified() -> None:
    result = MultiDistributionQualificationEngine().qualify(
        host_snapshot=_snapshot(
            capabilities=(
                HostPrimitiveCapability(
                    primitive=HostPrimitive.LANDLOCK,
                    state=CapabilityState.SUPPORTED,
                    evidence=("kernel_supported=True",),
                ),
            ),
        ),
        requirements=_requirements(),
    )

    assert result.blocked is True


def test_profile_and_adaptive_evidence_are_preserved() -> None:
    result = MultiDistributionQualificationEngine().qualify(
        host_snapshot=_snapshot(
            capabilities=(_available_landlock(),),
        ),
        requirements=_requirements(),
    )

    assert result.profile.tier.value == "candidate"
    assert result.profile.status.value == "discovered"
    assert len(result.profile_id) == 64
    assert len(result.evidence_digest) == 64


def test_qualification_is_deterministic() -> None:
    snapshot = _snapshot(
        os_name="Debian",
        os_version="13",
        architecture="x86_64",
        capabilities=(_available_landlock(),),
    )
    requirements = _requirements()

    engine = MultiDistributionQualificationEngine()

    first = engine.qualify(
        host_snapshot=snapshot,
        requirements=requirements,
    )
    second = engine.qualify(
        host_snapshot=snapshot,
        requirements=requirements,
    )

    assert first == second


def test_snapshot_is_not_mutated() -> None:
    snapshot = _snapshot(
        capabilities=(_available_landlock(),),
    )
    before = snapshot

    MultiDistributionQualificationEngine().qualify(
        host_snapshot=snapshot,
        requirements=_requirements(),
    )

    assert snapshot == before


def _policy(
    *,
    distribution: LinuxDistribution | None = None,
    distribution_family: LinuxDistributionFamily | None = None,
    architecture: LinuxArchitecture | None = None,
    requirement_id: str,
    primitive: HostPrimitive = HostPrimitive.LANDLOCK,
):
    from lyrion.execution.backends.linux.host.policy.contracts import (
        LinuxHostPolicyKey,
        LinuxHostQualificationPolicy,
    )

    key = LinuxHostPolicyKey(
        distribution=distribution,
        distribution_family=distribution_family,
        architecture=architecture,
    )

    requirements = CapabilityRequirementSet(
        requirements=(
            CapabilityRequirement(
                requirement_id=requirement_id,
                primitive=primitive,
                mode=CapabilityRequirementMode.REQUIRED,
                acceptable_states=(CapabilityState.AVAILABLE,),
                rationale="Policy-specific qualification requirement.",
            ),
        ),
    )

    return LinuxHostQualificationPolicy(
        key=key,
        requirements=requirements,
        policy_id=key.policy_id,
    )


def test_selected_policy_requirements_control_qualification() -> None:
    from lyrion.execution.backends.linux.host.policy import (
        LinuxHostQualificationPolicyRegistry,
    )

    policy = _policy(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
        requirement_id="policy-cgroups",
        primitive=HostPrimitive.CGROUPS_V2,
    )

    engine = MultiDistributionQualificationEngine(
        policy_registry=LinuxHostQualificationPolicyRegistry((policy,)),
    )

    result = engine.qualify(
        host_snapshot=_snapshot(
            os_name="Ubuntu",
            architecture="x86_64",
            capabilities=(
                HostPrimitiveCapability(
                    primitive=HostPrimitive.CGROUPS_V2,
                    state=CapabilityState.AVAILABLE,
                    evidence=("cgroups_v2=True",),
                ),
            ),
        ),
    )

    assert result.qualified is True
    assert result.selected_policy_id == policy.policy_id
    assert result.adaptive.negotiation.requirements.requirement_ids == (
        "policy-cgroups",
    )


def test_selected_policy_requirement_failure_blocks_qualification() -> None:
    from lyrion.execution.backends.linux.host.policy import (
        LinuxHostQualificationPolicyRegistry,
    )

    policy = _policy(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
        requirement_id="policy-cgroups",
        primitive=HostPrimitive.CGROUPS_V2,
    )

    engine = MultiDistributionQualificationEngine(
        policy_registry=LinuxHostQualificationPolicyRegistry((policy,)),
    )

    result = engine.qualify(
        host_snapshot=_snapshot(
            os_name="Ubuntu",
            architecture="x86_64",
            capabilities=(_available_landlock(),),
        ),
    )

    assert result.selected_policy_id == policy.policy_id
    assert result.blocked is True
    assert result.execution_authorized is False
    assert result.enforcement_verified is False


def test_policy_selection_does_not_infer_missing_capability_from_distribution() -> None:
    from lyrion.execution.backends.linux.host.policy import (
        LinuxHostQualificationPolicyRegistry,
    )

    policy = _policy(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
        requirement_id="policy-landlock",
        primitive=HostPrimitive.LANDLOCK,
    )

    engine = MultiDistributionQualificationEngine(
        policy_registry=LinuxHostQualificationPolicyRegistry((policy,)),
    )

    result = engine.qualify(
        host_snapshot=_snapshot(
            os_name="Ubuntu",
            architecture="x86_64",
        ),
    )

    assert result.selected_policy_id == policy.policy_id
    assert result.blocked is True


def test_policy_qualification_preserves_snapshot_identity() -> None:
    from lyrion.execution.backends.linux.host.policy import (
        LinuxHostQualificationPolicyRegistry,
    )

    policy = _policy(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
        requirement_id="policy-landlock",
    )

    registry = LinuxHostQualificationPolicyRegistry((policy,))
    engine = MultiDistributionQualificationEngine(
        policy_registry=registry,
    )

    snapshot = _snapshot(
        os_name="Ubuntu",
        architecture="x86_64",
        capabilities=(_available_landlock(),),
    )

    result = engine.qualify(host_snapshot=snapshot)

    assert result.adaptive.negotiation.host_snapshot == snapshot
    assert result.profile.distribution.raw_id == snapshot.identity.os_name
    assert result.profile.architecture.raw_value == snapshot.identity.architecture
    assert result.profile.kernel == snapshot.identity.kernel


def test_policy_registry_drives_qualification() -> None:
    from lyrion.execution.backends.linux.host.policy import (
        LinuxHostQualificationPolicyRegistry,
    )

    policy = _policy(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
        requirement_id="policy-landlock",
    )

    engine = MultiDistributionQualificationEngine(
        policy_registry=LinuxHostQualificationPolicyRegistry((policy,)),
    )

    result = engine.qualify(
        host_snapshot=_snapshot(
            os_name="Ubuntu",
            architecture="x86_64",
            capabilities=(_available_landlock(),),
        ),
    )

    assert result.qualified is True
    assert result.selected_policy_id == policy.policy_id
    assert result.profile.distribution.distribution is LinuxDistribution.UBUNTU
    assert result.profile.architecture.architecture is LinuxArchitecture.X86_64


def test_exact_policy_is_selected_before_fallbacks() -> None:
    from lyrion.execution.backends.linux.host.policy import (
        LinuxHostQualificationPolicyRegistry,
    )

    exact = _policy(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
        requirement_id="exact",
    )
    distro = _policy(
        distribution=LinuxDistribution.UBUNTU,
        requirement_id="distro",
    )
    family = _policy(
        distribution_family=LinuxDistributionFamily.DEBIAN,
        architecture=LinuxArchitecture.X86_64,
        requirement_id="family",
    )
    generic = _policy(
        architecture=LinuxArchitecture.X86_64,
        requirement_id="generic",
    )

    engine = MultiDistributionQualificationEngine(
        policy_registry=LinuxHostQualificationPolicyRegistry(
            (generic, family, distro, exact),
        ),
    )

    result = engine.qualify(
        host_snapshot=_snapshot(
            os_name="Ubuntu",
            architecture="x86_64",
            capabilities=(_available_landlock(),),
        ),
    )

    assert result.selected_policy_id == exact.policy_id


def test_distribution_policy_fallback_is_integrated() -> None:
    from lyrion.execution.backends.linux.host.policy import (
        LinuxHostQualificationPolicyRegistry,
    )

    policy = _policy(
        distribution=LinuxDistribution.UBUNTU,
        requirement_id="ubuntu-fallback",
    )

    engine = MultiDistributionQualificationEngine(
        policy_registry=LinuxHostQualificationPolicyRegistry((policy,)),
    )

    result = engine.qualify(
        host_snapshot=_snapshot(
            os_name="Ubuntu",
            architecture="aarch64",
            capabilities=(_available_landlock(),),
        ),
    )

    assert result.qualified is True
    assert result.selected_policy_id == policy.policy_id


def test_family_architecture_policy_fallback_is_integrated() -> None:
    from lyrion.execution.backends.linux.host.policy import (
        LinuxHostQualificationPolicyRegistry,
    )

    policy = _policy(
        distribution_family=LinuxDistributionFamily.DEBIAN,
        architecture=LinuxArchitecture.AARCH64,
        requirement_id="debian-arm64",
    )

    engine = MultiDistributionQualificationEngine(
        policy_registry=LinuxHostQualificationPolicyRegistry((policy,)),
    )

    result = engine.qualify(
        host_snapshot=_snapshot(
            os_name="Kali",
            architecture="aarch64",
            capabilities=(_available_landlock(),),
        ),
    )

    assert result.qualified is True
    assert result.selected_policy_id == policy.policy_id


def test_generic_architecture_policy_fallback_is_integrated() -> None:
    from lyrion.execution.backends.linux.host.policy import (
        LinuxHostQualificationPolicyRegistry,
    )

    policy = _policy(
        architecture=LinuxArchitecture.X86_64,
        requirement_id="generic-x86",
    )

    engine = MultiDistributionQualificationEngine(
        policy_registry=LinuxHostQualificationPolicyRegistry((policy,)),
    )

    result = engine.qualify(
        host_snapshot=_snapshot(
            os_name="Example Linux",
            architecture="x86_64",
            capabilities=(_available_landlock(),),
        ),
    )

    assert result.qualified is True
    assert result.selected_policy_id == policy.policy_id


def test_policy_registry_without_match_fails_closed() -> None:
    from lyrion.execution.backends.linux.host.policy import (
        LinuxHostQualificationPolicyRegistry,
    )

    policy = _policy(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
        requirement_id="ubuntu-x86",
    )

    engine = MultiDistributionQualificationEngine(
        policy_registry=LinuxHostQualificationPolicyRegistry((policy,)),
    )

    with pytest.raises(MultiDistributionQualificationError):
        engine.qualify(
            host_snapshot=_snapshot(
                os_name="Debian",
                architecture="aarch64",
                capabilities=(_available_landlock(),),
            ),
        )


def test_explicit_requirements_and_policy_registry_are_rejected_together() -> None:
    from lyrion.execution.backends.linux.host.policy import (
        LinuxHostQualificationPolicyRegistry,
    )

    policy = _policy(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
        requirement_id="ubuntu-x86",
    )

    engine = MultiDistributionQualificationEngine(
        policy_registry=LinuxHostQualificationPolicyRegistry((policy,)),
    )

    with pytest.raises(MultiDistributionQualificationError):
        engine.qualify(
            host_snapshot=_snapshot(
                os_name="Ubuntu",
                architecture="x86_64",
                capabilities=(_available_landlock(),),
            ),
            requirements=_requirements(),
        )


def test_policy_registry_without_explicit_requirements_is_required() -> None:
    engine = MultiDistributionQualificationEngine()

    with pytest.raises(MultiDistributionQualificationError):
        engine.qualify(
            host_snapshot=_snapshot(
                capabilities=(_available_landlock(),),
            ),
        )


def test_policy_selected_qualification_remains_non_authorizing() -> None:
    from lyrion.execution.backends.linux.host.policy import (
        LinuxHostQualificationPolicyRegistry,
    )

    policy = _policy(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
        requirement_id="ubuntu-x86",
    )

    engine = MultiDistributionQualificationEngine(
        policy_registry=LinuxHostQualificationPolicyRegistry((policy,)),
    )

    result = engine.qualify(
        host_snapshot=_snapshot(
            os_name="Ubuntu",
            architecture="x86_64",
            capabilities=(_available_landlock(),),
        ),
    )

    assert result.execution_authorized is False
    assert result.enforcement_verified is False


def test_policy_selected_qualification_is_deterministic() -> None:
    from lyrion.execution.backends.linux.host.policy import (
        LinuxHostQualificationPolicyRegistry,
    )

    policy = _policy(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
        requirement_id="ubuntu-x86",
    )

    registry = LinuxHostQualificationPolicyRegistry((policy,))
    engine = MultiDistributionQualificationEngine(
        policy_registry=registry,
    )

    snapshot = _snapshot(
        os_name="Ubuntu",
        architecture="x86_64",
        capabilities=(_available_landlock(),),
    )

    first = engine.qualify(host_snapshot=snapshot)
    second = engine.qualify(host_snapshot=snapshot)

    assert first == second
    assert first.selected_policy_id == policy.policy_id


def test_execution_authorization_is_always_false() -> None:
    result = MultiDistributionQualificationEngine().qualify(
        host_snapshot=_snapshot(
            capabilities=(_available_landlock(),),
        ),
        requirements=_requirements(),
    )

    assert result.execution_authorized is False
    assert result.enforcement_verified is False


def test_inconsistent_profile_is_rejected() -> None:
    class TamperingProfileEngine:
        def build(self, snapshot: LinuxHostAbstractionSnapshot):
            from lyrion.execution.backends.linux.host.profiles.engine import (
                LinuxHostQualificationProfileEngine,
            )

            profile = LinuxHostQualificationProfileEngine().build(snapshot)

            object.__setattr__(
                profile.distribution,
                "raw_id",
                "tampered",
            )
            return profile

    with pytest.raises(
        (RuntimeError, TypeError, MultiDistributionQualificationError),
    ):
        MultiDistributionQualificationEngine(
            profile_engine=TamperingProfileEngine(),
        ).qualify(
            host_snapshot=_snapshot(
                capabilities=(_available_landlock(),),
            ),
            requirements=_requirements(),
        )


def test_policy_qualification_produces_immutable_evidence() -> None:
    from lyrion.execution.backends.linux.host.policy import (
        LinuxHostQualificationPolicyRegistry,
    )
    from lyrion.execution.backends.linux.host.qualification import (
        QualificationEvidence,
    )

    policy = _policy(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
        requirement_id="policy-landlock",
    )

    engine = MultiDistributionQualificationEngine(
        policy_registry=LinuxHostQualificationPolicyRegistry((policy,)),
    )

    snapshot = _snapshot(
        os_name="Ubuntu",
        architecture="x86_64",
        capabilities=(_available_landlock(),),
    )

    result = engine.qualify(host_snapshot=snapshot)

    assert isinstance(result.evidence, QualificationEvidence)
    assert result.evidence is not None
    assert result.evidence.policy_id == policy.policy_id
    assert result.evidence.policy_version == policy.policy_version
    assert result.evidence.requirement_set_id == result.profile_id
    assert (
        result.evidence.capability_evaluation_digest
        == result.evidence.basis.capability_evaluation_digest
    )


def test_policy_qualification_evidence_binds_actual_host_fingerprint() -> None:
    from lyrion.execution.backends.linux.host.policy import (
        LinuxHostQualificationPolicyRegistry,
    )
    from lyrion.execution.backends.linux.host.qualification.evidence import (
        host_fingerprint_digest,
    )

    policy = _policy(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
        requirement_id="policy-landlock",
    )

    engine = MultiDistributionQualificationEngine(
        policy_registry=LinuxHostQualificationPolicyRegistry((policy,)),
    )

    snapshot = _snapshot(
        os_name="Ubuntu",
        architecture="x86_64",
        capabilities=(_available_landlock(),),
    )

    result = engine.qualify(host_snapshot=snapshot)

    assert result.evidence is not None
    assert result.evidence.host_fingerprint_digest == (
        host_fingerprint_digest(snapshot.fingerprint)
    )


def test_policy_qualification_evidence_tracks_blocked_result() -> None:
    from lyrion.execution.backends.linux.host.policy import (
        LinuxHostQualificationPolicyRegistry,
    )

    policy = _policy(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
        requirement_id="policy-landlock",
    )

    engine = MultiDistributionQualificationEngine(
        policy_registry=LinuxHostQualificationPolicyRegistry((policy,)),
    )

    result = engine.qualify(
        host_snapshot=_snapshot(
            os_name="Ubuntu",
            architecture="x86_64",
        ),
    )

    assert result.blocked is True
    assert result.evidence is not None
    assert result.evidence.qualification_state == result.status.value
    assert result.execution_authorized is False
    assert result.enforcement_verified is False


def test_explicit_requirements_preserve_legacy_path_without_synthetic_policy() -> None:
    result = MultiDistributionQualificationEngine().qualify(
        host_snapshot=_snapshot(
            capabilities=(_available_landlock(),),
        ),
        requirements=_requirements(),
    )

    assert result.selected_policy_id is None
    assert result.evidence is None
    assert result.qualified is True


def test_policy_evidence_is_deterministic() -> None:
    from lyrion.execution.backends.linux.host.policy import (
        LinuxHostQualificationPolicyRegistry,
    )

    policy = _policy(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
        requirement_id="policy-landlock",
    )

    registry = LinuxHostQualificationPolicyRegistry((policy,))
    engine = MultiDistributionQualificationEngine(
        policy_registry=registry,
    )

    snapshot = _snapshot(
        os_name="Ubuntu",
        architecture="x86_64",
        capabilities=(_available_landlock(),),
    )

    first = engine.qualify(host_snapshot=snapshot)
    second = engine.qualify(host_snapshot=snapshot)

    assert first == second
    assert first.evidence is not None
    assert second.evidence is not None
    assert first.evidence == second.evidence


def test_policy_version_change_changes_integrated_evidence() -> None:
    from lyrion.execution.backends.linux.host.policy import (
        LinuxHostQualificationPolicyRegistry,
    )

    first_policy = _policy(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
        requirement_id="policy-landlock",
    )

    second_policy = _policy(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
        requirement_id="policy-landlock",
    )

    from dataclasses import replace

    second_policy = replace(second_policy, policy_version="2")

    snapshot = _snapshot(
        os_name="Ubuntu",
        architecture="x86_64",
        capabilities=(_available_landlock(),),
    )

    first = MultiDistributionQualificationEngine(
        policy_registry=LinuxHostQualificationPolicyRegistry(
            (first_policy,),
        ),
    ).qualify(host_snapshot=snapshot)

    second = MultiDistributionQualificationEngine(
        policy_registry=LinuxHostQualificationPolicyRegistry(
            (second_policy,),
        ),
    ).qualify(host_snapshot=snapshot)

    assert first.evidence is not None
    assert second.evidence is not None
    assert first.evidence.policy_id == second.evidence.policy_id
    assert first.evidence.policy_version == "1"
    assert second.evidence.policy_version == "2"
    assert first.evidence.basis_digest != second.evidence.basis_digest
    assert first.evidence.qualification_id != second.evidence.qualification_id


def test_integrated_evidence_does_not_authorize_or_enforce() -> None:
    from lyrion.execution.backends.linux.host.policy import (
        LinuxHostQualificationPolicyRegistry,
    )

    policy = _policy(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
        requirement_id="policy-landlock",
    )

    result = MultiDistributionQualificationEngine(
        policy_registry=LinuxHostQualificationPolicyRegistry((policy,)),
    ).qualify(
        host_snapshot=_snapshot(
            os_name="Ubuntu",
            architecture="x86_64",
            capabilities=(_available_landlock(),),
        ),
    )

    assert result.evidence is not None
    assert result.execution_authorized is False
    assert result.enforcement_verified is False
    assert result.adaptive.execution_authorized is False
    assert result.adaptive.enforcement_verified is False
