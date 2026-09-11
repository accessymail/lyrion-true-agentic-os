from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class LinuxDistributionFamily(StrEnum):
    """
    Distribution-family classification used by LYRION host qualification.

    This classification is descriptive metadata. Membership in a family
    never establishes host compatibility, qualification, or certification.
    """

    DEBIAN = "debian"
    OTHER = "other"


class LinuxDistribution(StrEnum):
    """
    Known LYRION qualification targets.

    The enum identifies candidate distributions only. A listed distribution
    is not automatically supported, qualified, or production-certified.
    """

    UBUNTU = "ubuntu"
    DEBIAN = "debian"
    LINUX_MINT = "linux_mint"
    KALI = "kali"
    PARROT = "parrot"
    MX = "mx"
    RASPBERRY_PI_OS = "raspberry_pi_os"
    OTHER = "other"


class LinuxArchitecture(StrEnum):
    """
    Canonical architecture identifiers used by host qualification.

    Runtime discovery remains authoritative; these values normalize observed
    architecture identities for profile comparison.
    """

    X86_64 = "x86_64"
    AARCH64 = "aarch64"
    ARMV7 = "armv7"
    ARMV6 = "armv6"
    I686 = "i686"
    OTHER = "other"


class HostQualificationTier(StrEnum):
    """
    LYRION-defined host qualification tiers.

    These are project-level lifecycle classifications and are not external
    certification standards.
    """

    CANDIDATE = "candidate"
    ENGINEERING = "engineering"
    NATIVE_QUALIFIED = "native_qualified"
    PRODUCTION_CERTIFICATION_ELIGIBLE = (
        "production_certification_eligible"
    )


class HostQualificationStatus(StrEnum):
    """
    LYRION host qualification state.

    Qualification is evidence-based and host-specific.
    """

    DISCOVERED = "discovered"
    CAPABILITY_ASSESSED = "capability_assessed"
    QUALIFICATION_PENDING = "qualification_pending"
    QUALIFIED = "qualified"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class LinuxDistributionIdentity:
    """
    Normalized distribution identity observed from a Linux host.

    The canonical distribution value is classification metadata. The raw
    distribution identifier preserves the host's observed identity without
    assuming that every Debian-derived distribution behaves identically.
    """

    distribution: LinuxDistribution
    family: LinuxDistributionFamily
    raw_id: str
    version: str
    version_id: str

    def __post_init__(self) -> None:
        if not self.raw_id.strip():
            raise ValueError("raw_id must not be blank")

        if not self.version.strip():
            raise ValueError("version must not be blank")

        if not self.version_id.strip():
            raise ValueError("version_id must not be blank")

        if (
            self.distribution is LinuxDistribution.UBUNTU
            and self.family is not LinuxDistributionFamily.DEBIAN
        ):
            raise ValueError("Ubuntu must use the Debian family")

        if (
            self.distribution is LinuxDistribution.DEBIAN
            and self.family is not LinuxDistributionFamily.DEBIAN
        ):
            raise ValueError("Debian must use the Debian family")

        if (
            self.distribution is LinuxDistribution.LINUX_MINT
            and self.family is not LinuxDistributionFamily.DEBIAN
        ):
            raise ValueError("Linux Mint must use the Debian family")

        if (
            self.distribution is LinuxDistribution.KALI
            and self.family is not LinuxDistributionFamily.DEBIAN
        ):
            raise ValueError("Kali must use the Debian family")

        if (
            self.distribution is LinuxDistribution.PARROT
            and self.family is not LinuxDistributionFamily.DEBIAN
        ):
            raise ValueError("Parrot must use the Debian family")

        if (
            self.distribution is LinuxDistribution.MX
            and self.family is not LinuxDistributionFamily.DEBIAN
        ):
            raise ValueError("MX must use the Debian family")

        if (
            self.distribution is LinuxDistribution.RASPBERRY_PI_OS
            and self.family is not LinuxDistributionFamily.DEBIAN
        ):
            raise ValueError("Raspberry Pi OS must use the Debian family")


@dataclass(frozen=True, slots=True)
class LinuxArchitectureIdentity:
    """
    Normalized architecture observation.

    The raw value is retained so normalization never destroys the original
    host observation.
    """

    architecture: LinuxArchitecture
    raw_value: str

    def __post_init__(self) -> None:
        if not self.raw_value.strip():
            raise ValueError("raw_value must not be blank")


@dataclass(frozen=True, slots=True)
class LinuxHostQualificationProfile:
    """
    Immutable host qualification profile.

    This object combines identity and lifecycle metadata only. It does not
    authorize execution, apply security controls, or establish production
    certification.
    """

    distribution: LinuxDistributionIdentity
    architecture: LinuxArchitectureIdentity
    kernel: str
    virtualization: str | None
    init_system: str | None
    tier: HostQualificationTier
    status: HostQualificationStatus

    def __post_init__(self) -> None:
        if not self.kernel.strip():
            raise ValueError("kernel must not be blank")

        if self.virtualization is not None and not self.virtualization.strip():
            raise ValueError(
                "virtualization must be non-blank when provided"
            )

        if self.init_system is not None and not self.init_system.strip():
            raise ValueError(
                "init_system must be non-blank when provided"
            )

        if (
            self.tier is HostQualificationTier.NATIVE_QUALIFIED
            and self.status is not HostQualificationStatus.QUALIFIED
        ):
            raise ValueError(
                "native_qualified tier requires qualified status"
            )

        if (
            self.tier
            is HostQualificationTier.PRODUCTION_CERTIFICATION_ELIGIBLE
            and self.status is not HostQualificationStatus.QUALIFIED
        ):
            raise ValueError(
                "production-certification-eligible tier requires "
                "qualified status"
            )

    @property
    def is_debian_family(self) -> bool:
        return (
            self.distribution.family
            is LinuxDistributionFamily.DEBIAN
        )

    @property
    def is_native_qualified(self) -> bool:
        return (
            self.tier is HostQualificationTier.NATIVE_QUALIFIED
            and self.status is HostQualificationStatus.QUALIFIED
        )

    @property
    def production_certification_eligible(self) -> bool:
        return (
            self.tier
            is HostQualificationTier.PRODUCTION_CERTIFICATION_ELIGIBLE
            and self.status is HostQualificationStatus.QUALIFIED
        )
