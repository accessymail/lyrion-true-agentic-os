from __future__ import annotations

import pytest

from lyrion.execution.backends.linux.host.profiles.contracts import (
    HostQualificationStatus,
    HostQualificationTier,
    LinuxArchitecture,
    LinuxArchitectureIdentity,
    LinuxDistribution,
    LinuxDistributionFamily,
    LinuxDistributionIdentity,
    LinuxHostQualificationProfile,
)


def make_distribution(
    distribution: LinuxDistribution = LinuxDistribution.UBUNTU,
) -> LinuxDistributionIdentity:
    return LinuxDistributionIdentity(
        distribution=distribution,
        family=LinuxDistributionFamily.DEBIAN,
        raw_id=distribution.value,
        version="26.04",
        version_id="26.04",
    )


def make_architecture(
    architecture: LinuxArchitecture = LinuxArchitecture.X86_64,
) -> LinuxArchitectureIdentity:
    return LinuxArchitectureIdentity(
        architecture=architecture,
        raw_value=architecture.value,
    )


def make_profile(
    *,
    distribution: LinuxDistribution = LinuxDistribution.UBUNTU,
    architecture: LinuxArchitecture = LinuxArchitecture.X86_64,
    tier: HostQualificationTier = HostQualificationTier.CANDIDATE,
    status: HostQualificationStatus = HostQualificationStatus.DISCOVERED,
) -> LinuxHostQualificationProfile:
    return LinuxHostQualificationProfile(
        distribution=make_distribution(distribution),
        architecture=make_architecture(architecture),
        kernel="6.18.0",
        virtualization=None,
        init_system="systemd",
        tier=tier,
        status=status,
    )


@pytest.mark.parametrize(
    "distribution",
    [
        LinuxDistribution.UBUNTU,
        LinuxDistribution.DEBIAN,
        LinuxDistribution.LINUX_MINT,
        LinuxDistribution.KALI,
        LinuxDistribution.PARROT,
        LinuxDistribution.MX,
        LinuxDistribution.RASPBERRY_PI_OS,
    ],
)
def test_debian_family_candidates_are_explicitly_classified(
    distribution: LinuxDistribution,
) -> None:
    identity = make_distribution(distribution)

    assert identity.family is LinuxDistributionFamily.DEBIAN
    assert identity.distribution is distribution


def test_other_distribution_does_not_claim_debian_family() -> None:
    identity = LinuxDistributionIdentity(
        distribution=LinuxDistribution.OTHER,
        family=LinuxDistributionFamily.OTHER,
        raw_id="example-linux",
        version="1.0",
        version_id="1.0",
    )

    assert identity.family is LinuxDistributionFamily.OTHER
    assert identity.distribution is LinuxDistribution.OTHER


@pytest.mark.parametrize(
    "distribution",
    [
        LinuxDistribution.UBUNTU,
        LinuxDistribution.DEBIAN,
        LinuxDistribution.LINUX_MINT,
        LinuxDistribution.KALI,
        LinuxDistribution.PARROT,
        LinuxDistribution.MX,
        LinuxDistribution.RASPBERRY_PI_OS,
    ],
)
def test_known_debian_family_distribution_rejects_wrong_family(
    distribution: LinuxDistribution,
) -> None:
    with pytest.raises(ValueError, match="Debian family"):
        LinuxDistributionIdentity(
            distribution=distribution,
            family=LinuxDistributionFamily.OTHER,
            raw_id=distribution.value,
            version="1",
            version_id="1",
        )


@pytest.mark.parametrize(
    "architecture",
    [
        LinuxArchitecture.X86_64,
        LinuxArchitecture.AARCH64,
        LinuxArchitecture.ARMV7,
        LinuxArchitecture.ARMV6,
        LinuxArchitecture.I686,
        LinuxArchitecture.OTHER,
    ],
)
def test_architecture_contract_accepts_canonical_values(
    architecture: LinuxArchitecture,
) -> None:
    identity = make_architecture(architecture)

    assert identity.architecture is architecture
    assert identity.raw_value == architecture.value


def test_candidate_profile_is_not_native_qualified() -> None:
    profile = make_profile()

    assert profile.tier is HostQualificationTier.CANDIDATE
    assert profile.status is HostQualificationStatus.DISCOVERED
    assert profile.is_debian_family
    assert not profile.is_native_qualified
    assert not profile.production_certification_eligible


def test_native_qualified_profile_requires_qualified_status() -> None:
    with pytest.raises(ValueError, match="native_qualified tier"):
        make_profile(
            tier=HostQualificationTier.NATIVE_QUALIFIED,
            status=HostQualificationStatus.QUALIFICATION_PENDING,
        )


def test_production_eligible_profile_requires_qualified_status() -> None:
    with pytest.raises(
        ValueError,
        match="production-certification-eligible tier",
    ):
        make_profile(
            tier=HostQualificationTier.PRODUCTION_CERTIFICATION_ELIGIBLE,
            status=HostQualificationStatus.CAPABILITY_ASSESSED,
        )


def test_native_qualified_profile_is_explicit() -> None:
    profile = make_profile(
        tier=HostQualificationTier.NATIVE_QUALIFIED,
        status=HostQualificationStatus.QUALIFIED,
    )

    assert profile.is_native_qualified
    assert not profile.production_certification_eligible


def test_production_certification_eligibility_is_explicit() -> None:
    profile = make_profile(
        tier=HostQualificationTier.PRODUCTION_CERTIFICATION_ELIGIBLE,
        status=HostQualificationStatus.QUALIFIED,
    )

    assert profile.production_certification_eligible


def test_profile_is_immutable() -> None:
    profile = make_profile()

    with pytest.raises(AttributeError):
        profile.kernel = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"raw_id": ""},
        {"version": ""},
        {"version_id": ""},
    ],
)
def test_distribution_identity_rejects_blank_identity_fields(
    kwargs: dict[str, str],
) -> None:
    values = {
        "distribution": LinuxDistribution.UBUNTU,
        "family": LinuxDistributionFamily.DEBIAN,
        "raw_id": "ubuntu",
        "version": "26.04",
        "version_id": "26.04",
    }
    values.update(kwargs)

    with pytest.raises(ValueError):
        LinuxDistributionIdentity(**values)


def test_architecture_identity_rejects_blank_raw_value() -> None:
    with pytest.raises(ValueError, match="raw_value"):
        LinuxArchitectureIdentity(
            architecture=LinuxArchitecture.X86_64,
            raw_value="",
        )


def test_profile_rejects_blank_kernel() -> None:
    with pytest.raises(ValueError, match="kernel"):
        LinuxHostQualificationProfile(
            distribution=make_distribution(),
            architecture=make_architecture(),
            kernel="",
            virtualization=None,
            init_system="systemd",
            tier=HostQualificationTier.CANDIDATE,
            status=HostQualificationStatus.DISCOVERED,
        )


def test_profile_allows_unknown_architecture() -> None:
    profile = make_profile(
        architecture=LinuxArchitecture.OTHER,
    )

    assert profile.architecture.architecture is LinuxArchitecture.OTHER
