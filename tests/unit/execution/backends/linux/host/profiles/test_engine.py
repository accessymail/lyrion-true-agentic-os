from __future__ import annotations

from lyrion.execution.backends.linux.host.contracts import (
    CapabilityState,
    HostPrimitive,
    HostPrimitiveCapability,
    LinuxHostAbstractionSnapshot,
    LinuxHostFingerprint,
    LinuxHostIdentity,
)
from lyrion.execution.backends.linux.host.profiles.contracts import (
    HostQualificationStatus,
    HostQualificationTier,
    LinuxArchitecture,
    LinuxDistribution,
    LinuxDistributionFamily,
)
from lyrion.execution.backends.linux.host.profiles.engine import (
    LinuxHostQualificationProfileEngine,
)


def make_snapshot(
    *,
    os_name: str = "Ubuntu",
    os_version: str = "26.04",
    architecture: str = "x86_64",
) -> LinuxHostAbstractionSnapshot:
    identity = LinuxHostIdentity(
        os_name=os_name,
        os_version=os_version,
        kernel="6.18.0-test",
        architecture=architecture,
        virtualization=None,
        init_system="systemd",
    )

    fingerprint = LinuxHostFingerprint(
        identity=identity,
        primitives=tuple(
            HostPrimitiveCapability(
                primitive=primitive,
                state=CapabilityState.UNKNOWN,
            )
            for primitive in HostPrimitive
        ),
    )

    return LinuxHostAbstractionSnapshot(
        identity=identity,
        fingerprint=fingerprint,
        user_id=1000,
        effective_capabilities=(),
        namespaces=(),
        notes=(),
    )


def test_ubuntu_x86_64_becomes_candidate_profile() -> None:
    profile = LinuxHostQualificationProfileEngine().build(
        make_snapshot()
    )

    assert profile.distribution.distribution is LinuxDistribution.UBUNTU
    assert profile.distribution.family is LinuxDistributionFamily.DEBIAN
    assert profile.architecture.architecture is LinuxArchitecture.X86_64
    assert profile.tier is HostQualificationTier.CANDIDATE
    assert profile.status is HostQualificationStatus.DISCOVERED


def test_debian_is_detected_without_ubuntu_specific_logic() -> None:
    profile = LinuxHostQualificationProfileEngine().build(
        make_snapshot(os_name="Debian", os_version="13")
    )

    assert profile.distribution.distribution is LinuxDistribution.DEBIAN
    assert profile.distribution.family is LinuxDistributionFamily.DEBIAN


def test_known_debian_family_distributions_are_normalized() -> None:
    cases = (
        ("Linux Mint", LinuxDistribution.LINUX_MINT),
        ("Kali", LinuxDistribution.KALI),
        ("Parrot", LinuxDistribution.PARROT),
        ("MX", LinuxDistribution.MX),
        ("Raspios", LinuxDistribution.RASPBERRY_PI_OS),
    )

    engine = LinuxHostQualificationProfileEngine()

    for os_name, expected in cases:
        profile = engine.build(make_snapshot(os_name=os_name))

        assert profile.distribution.distribution is expected
        assert profile.distribution.family is LinuxDistributionFamily.DEBIAN


def test_unknown_distribution_is_not_claimed_as_debian_family() -> None:
    profile = LinuxHostQualificationProfileEngine().build(
        make_snapshot(os_name="Example Linux")
    )

    assert profile.distribution.distribution is LinuxDistribution.OTHER
    assert profile.distribution.family is LinuxDistributionFamily.OTHER


def test_architecture_aliases_are_normalized() -> None:
    engine = LinuxHostQualificationProfileEngine()

    assert (
        engine.build(make_snapshot(architecture="amd64"))
        .architecture.architecture
        is LinuxArchitecture.X86_64
    )

    assert (
        engine.build(make_snapshot(architecture="arm64"))
        .architecture.architecture
        is LinuxArchitecture.AARCH64
    )

    assert (
        engine.build(make_snapshot(architecture="armv7l"))
        .architecture.architecture
        is LinuxArchitecture.ARMV7
    )


def test_unknown_architecture_is_preserved_as_other() -> None:
    profile = LinuxHostQualificationProfileEngine().build(
        make_snapshot(architecture="future-architecture")
    )

    assert profile.architecture.architecture is LinuxArchitecture.OTHER
    assert profile.architecture.raw_value == "future-architecture"


def test_raw_distribution_identity_is_preserved() -> None:
    profile = LinuxHostQualificationProfileEngine().build(
        make_snapshot(os_name="Ubuntu")
    )

    assert profile.distribution.raw_id == "Ubuntu"


def test_raw_architecture_identity_is_preserved() -> None:
    profile = LinuxHostQualificationProfileEngine().build(
        make_snapshot(architecture="AMD64")
    )

    assert profile.architecture.raw_value == "AMD64"


def test_profile_is_always_initially_candidate() -> None:
    engine = LinuxHostQualificationProfileEngine()

    for os_name in ("Ubuntu", "Debian", "Kali", "Parrot", "MX"):
        profile = engine.build(make_snapshot(os_name=os_name))

        assert profile.tier is HostQualificationTier.CANDIDATE
        assert profile.status is HostQualificationStatus.DISCOVERED
        assert not profile.is_native_qualified


def test_engine_preserves_kernel_and_host_context() -> None:
    profile = LinuxHostQualificationProfileEngine().build(
        make_snapshot()
    )

    assert profile.kernel == "6.18.0-test"
    assert profile.virtualization is None
    assert profile.init_system == "systemd"


def test_engine_is_deterministic() -> None:
    snapshot = make_snapshot(
        os_name="Debian",
        os_version="13",
        architecture="aarch64",
    )

    engine = LinuxHostQualificationProfileEngine()

    assert engine.build(snapshot) == engine.build(snapshot)


def test_engine_does_not_modify_snapshot() -> None:
    snapshot = make_snapshot()
    before = snapshot

    LinuxHostQualificationProfileEngine().build(snapshot)

    assert snapshot == before


def test_profile_cannot_claim_production_certification() -> None:
    profile = LinuxHostQualificationProfileEngine().build(
        make_snapshot()
    )

    assert not profile.production_certification_eligible


def test_profile_does_not_authorize_execution() -> None:
    profile = LinuxHostQualificationProfileEngine().build(
        make_snapshot()
    )

    assert not hasattr(profile, "execution_authorized")
    assert not hasattr(profile, "enforcement_verified")
