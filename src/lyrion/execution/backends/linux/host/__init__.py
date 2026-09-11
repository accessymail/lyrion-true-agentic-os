"""Distro-neutral Linux host abstraction boundary."""

from lyrion.execution.backends.linux.host.contracts import (
    CapabilityState,
    HostPrimitive,
    HostPrimitiveCapability,
    LinuxHostAbstractionSnapshot,
    LinuxHostFingerprint,
    LinuxHostIdentity,
)
from lyrion.execution.backends.linux.host.discovery import (
    LinuxHostDiscovery,
    LinuxHostDiscoveryOperations,
)

__all__ = [
    "CapabilityState",
    "HostPrimitive",
    "HostPrimitiveCapability",
    "LinuxHostAbstractionSnapshot",
    "LinuxHostDiscovery",
    "LinuxHostDiscoveryOperations",
    "LinuxHostFingerprint",
    "LinuxHostIdentity",
]
