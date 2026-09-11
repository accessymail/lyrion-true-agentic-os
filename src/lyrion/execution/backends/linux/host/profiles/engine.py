from __future__ import annotations

from lyrion.execution.backends.linux.host.contracts import (
    LinuxHostAbstractionSnapshot,
)
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


class HostQualificationProfileError(ValueError):
    """Raised when an observed host cannot produce a valid profile."""


class LinuxHostQualificationProfileEngine:
    """
    Build an immutable qualification profile from an observed host snapshot.

    The engine is observational only.

    It does not:
    - authorize execution,
    - apply enforcement,
    - execute commands,
    - mutate the host,
    - infer security capability from distribution name,
    - or establish production certification.
    """

    _DEBIAN_FAMILY_IDS = frozenset(
        {
            "debian",
            "ubuntu",
            "linuxmint",
            "linux-mint",
            "kali",
            "parrot",
            "mx",
            "raspios",
            "raspberrypi",
            "raspberry-pi",
        }
    )

    _DISTRIBUTION_MAP = {
        "ubuntu": LinuxDistribution.UBUNTU,
        "debian": LinuxDistribution.DEBIAN,
        "linuxmint": LinuxDistribution.LINUX_MINT,
        "linux-mint": LinuxDistribution.LINUX_MINT,
        "kali": LinuxDistribution.KALI,
        "parrot": LinuxDistribution.PARROT,
        "mx": LinuxDistribution.MX,
        "raspios": LinuxDistribution.RASPBERRY_PI_OS,
        "raspberrypi": LinuxDistribution.RASPBERRY_PI_OS,
        "raspberry-pi": LinuxDistribution.RASPBERRY_PI_OS,
    }

    _ARCHITECTURE_MAP = {
        "x86_64": LinuxArchitecture.X86_64,
        "amd64": LinuxArchitecture.X86_64,
        "aarch64": LinuxArchitecture.AARCH64,
        "arm64": LinuxArchitecture.AARCH64,
        "armv7l": LinuxArchitecture.ARMV7,
        "armv7": LinuxArchitecture.ARMV7,
        "armhf": LinuxArchitecture.ARMV7,
        "armv6l": LinuxArchitecture.ARMV6,
        "armv6": LinuxArchitecture.ARMV6,
        "i686": LinuxArchitecture.I686,
        "i386": LinuxArchitecture.I686,
    }

    def build(
        self,
        snapshot: LinuxHostAbstractionSnapshot,
    ) -> LinuxHostQualificationProfile:
        """
        Build a candidate profile from an observed host snapshot.

        A newly observed host always starts at the CANDIDATE /
        DISCOVERED lifecycle state. Qualification is performed separately.
        """

        distribution = self._normalize_distribution(snapshot)
        architecture = self._normalize_architecture(snapshot)

        return LinuxHostQualificationProfile(
            distribution=distribution,
            architecture=architecture,
            kernel=snapshot.identity.kernel,
            virtualization=snapshot.identity.virtualization,
            init_system=snapshot.identity.init_system,
            tier=HostQualificationTier.CANDIDATE,
            status=HostQualificationStatus.DISCOVERED,
        )

    def _normalize_distribution(
        self,
        snapshot: LinuxHostAbstractionSnapshot,
    ) -> LinuxDistributionIdentity:
        raw_name = snapshot.identity.os_name.strip()
        raw_id = raw_name.lower().replace(" ", "")

        distribution = self._DISTRIBUTION_MAP.get(
            raw_id,
            LinuxDistribution.OTHER,
        )

        family = (
            LinuxDistributionFamily.DEBIAN
            if raw_id in self._DEBIAN_FAMILY_IDS
            else LinuxDistributionFamily.OTHER
        )

        try:
            return LinuxDistributionIdentity(
                distribution=distribution,
                family=family,
                raw_id=raw_name,
                version=snapshot.identity.os_version,
                version_id=snapshot.identity.os_version,
            )
        except ValueError as exc:
            raise HostQualificationProfileError(
                f"invalid observed distribution identity: {raw_name!r}"
            ) from exc

    def _normalize_architecture(
        self,
        snapshot: LinuxHostAbstractionSnapshot,
    ) -> LinuxArchitectureIdentity:
        raw_value = snapshot.identity.architecture.strip()
        normalized = raw_value.lower()

        architecture = self._ARCHITECTURE_MAP.get(
            normalized,
            LinuxArchitecture.OTHER,
        )

        return LinuxArchitectureIdentity(
            architecture=architecture,
            raw_value=raw_value,
        )
