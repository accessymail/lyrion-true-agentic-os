from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class HostPrimitive(StrEnum):
    CGROUPS_V2 = "cgroups_v2"
    NAMESPACES = "namespaces"
    SECCOMP = "seccomp"
    NO_NEW_PRIVS = "no_new_privs"
    LANDLOCK = "landlock"
    APPARMOR = "apparmor"
    LINUX_CAPABILITIES = "linux_capabilities"
    SYSTEMD = "systemd"
    BUBBLEWRAP = "bubblewrap"
    DOCKER = "docker"
    NFT = "nft"
    IPTABLES = "iptables"


class CapabilityState(StrEnum):
    SUPPORTED = "supported"
    OBSERVED = "observed"
    UNSUPPORTED = "unsupported"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class HostPrimitiveCapability:
    """
    Immutable observation of one host primitive.

    This object describes host state only. It never grants authorization
    and never represents applied or verified enforcement.
    """

    primitive: HostPrimitive
    state: CapabilityState
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.evidence and self.state == CapabilityState.UNKNOWN:
            return

        for item in self.evidence:
            if not isinstance(item, str):
                raise TypeError("capability evidence must contain strings")


@dataclass(frozen=True, slots=True)
class LinuxHostIdentity:
    """
    Stable, normalized identity information for the observed Linux host.

    Version strings are descriptive metadata. They are not capability proof.
    """

    os_name: str
    os_version: str
    kernel: str
    architecture: str
    virtualization: str | None
    init_system: str | None


@dataclass(frozen=True, slots=True)
class LinuxHostFingerprint:
    """
    Deterministic host fingerprint inputs.

    This is an observation identity, not a trust or authorization token.
    """

    identity: LinuxHostIdentity
    primitives: tuple[HostPrimitiveCapability, ...]

    def primitive(
        self,
        primitive: HostPrimitive,
    ) -> HostPrimitiveCapability:
        for capability in self.primitives:
            if capability.primitive == primitive:
                return capability

        raise KeyError(f"primitive not present: {primitive}")

    @property
    def primitive_ids(self) -> tuple[str, ...]:
        return tuple(item.primitive.value for item in self.primitives)


@dataclass(frozen=True, slots=True)
class LinuxHostAbstractionSnapshot:
    """
    Complete immutable Phase 2A host observation.

    This snapshot is intentionally non-authorizing. It contains observations
    that later qualification and regression layers may evaluate.
    """

    identity: LinuxHostIdentity
    fingerprint: LinuxHostFingerprint
    user_id: int
    effective_capabilities: tuple[str, ...]
    namespaces: tuple[str, ...]
    notes: tuple[str, ...]

    def capability(
        self,
        primitive: HostPrimitive,
    ) -> HostPrimitiveCapability:
        return self.fingerprint.primitive(primitive)
