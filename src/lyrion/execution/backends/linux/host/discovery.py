from __future__ import annotations

import os
import platform
from collections.abc import Callable
from dataclasses import dataclass
from errno import EOPNOTSUPP
from pathlib import Path

from lyrion.execution.backends.linux.capabilities import (
    LinuxHostCapabilityDetector,
    LinuxHostCapabilitySnapshot,
)
from lyrion.execution.backends.linux.enforcement.primitives.landlock import (
    NativeLandlockOperations,
)
from lyrion.execution.backends.linux.host.contracts import (
    CapabilityState,
    HostPrimitive,
    HostPrimitiveCapability,
    LinuxHostAbstractionSnapshot,
    LinuxHostFingerprint,
    LinuxHostIdentity,
)


@dataclass(frozen=True, slots=True)
class LinuxHostDiscoveryOperations:
    """
    Read-only discovery operations.

    Dependency injection keeps discovery deterministic and makes host access
    replaceable in tests without mutating the host.
    """

    read_file: Callable[[Path], str | None]
    command_exists: Callable[[str], bool]
    get_user_id: Callable[[], int]
    get_kernel: Callable[[], str]
    get_architecture: Callable[[], str]
    get_landlock_abi: Callable[[], int | None] | None = None


def _default_read_file(path: Path) -> str | None:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        ).strip()
    except OSError:
        return None


def _default_command_exists(command: str) -> bool:
    from shutil import which

    return which(command) is not None


def _probe_landlock_abi() -> int | None:
    """
    Query Landlock through the existing native LYRION implementation.

    None means runtime capability could not be established. In particular,
    EOPNOTSUPP means the kernel/userspace path does not expose a usable
    Landlock ABI at runtime.
    """
    try:
        operations = NativeLandlockOperations()
        return operations.get_capabilities().abi_version
    except OSError as exc:
        if exc.errno == EOPNOTSUPP:
            return None
        return None
    except (RuntimeError, ValueError):
        return None


def _default_operations() -> LinuxHostDiscoveryOperations:
    return LinuxHostDiscoveryOperations(
        read_file=_default_read_file,
        command_exists=_default_command_exists,
        get_user_id=os.getuid,
        get_kernel=platform.release,
        get_architecture=platform.machine,
        get_landlock_abi=_probe_landlock_abi,
    )


def _read_os_release(
    read_file: Callable[[Path], str | None],
) -> tuple[str, str]:
    text = read_file(Path("/etc/os-release"))

    if not text:
        return platform.system(), platform.release()

    values: dict[str, str] = {}

    for line in text.splitlines():
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')

    return (
        values.get("NAME", platform.system()),
        values.get("VERSION_ID", platform.release()),
    )


def _detect_init_system(
    read_file: Callable[[Path], str | None],
    command_exists: Callable[[str], bool],
) -> str | None:
    if command_exists("systemctl"):
        pid1_comm = read_file(Path("/proc/1/comm"))

        if pid1_comm:
            return pid1_comm

        return "systemd"

    return None


def _capability(
    primitive: HostPrimitive,
    state: CapabilityState,
    *evidence: str,
) -> HostPrimitiveCapability:
    return HostPrimitiveCapability(
        primitive=primitive,
        state=state,
        evidence=tuple(evidence),
    )


def _from_snapshot(
    snapshot: LinuxHostCapabilitySnapshot,
    operations: LinuxHostDiscoveryOperations,
) -> LinuxHostAbstractionSnapshot:
    identity = LinuxHostIdentity(
        os_name=snapshot.os_name,
        os_version=snapshot.os_version,
        kernel=operations.get_kernel(),
        architecture=operations.get_architecture(),
        virtualization=snapshot.virtualization,
        init_system=_detect_init_system(
            operations.read_file,
            operations.command_exists,
        ),
    )

    cgroup_state = (
        CapabilityState.AVAILABLE
        if snapshot.cgroup_version == "v2"
        else CapabilityState.UNAVAILABLE
    )

    namespace_state = (
        CapabilityState.AVAILABLE
        if snapshot.namespaces
        else CapabilityState.UNAVAILABLE
    )

    seccomp_state = (
        CapabilityState.SUPPORTED
        if snapshot.seccomp_kernel_supported
        else CapabilityState.UNSUPPORTED
    )

    landlock_abi: int | None = None

    if operations.get_landlock_abi is not None:
        landlock_abi = operations.get_landlock_abi()

    if landlock_abi is not None and landlock_abi >= 1:
        landlock_state = CapabilityState.AVAILABLE
        landlock_evidence = (
            f"runtime_abi={landlock_abi}",
            "runtime_abi_query=success",
        )
    elif snapshot.landlock_kernel_supported:
        landlock_state = CapabilityState.SUPPORTED
        landlock_evidence = (
            "kernel_config_support=True",
            "runtime_abi=unavailable",
        )
    else:
        landlock_state = CapabilityState.UNSUPPORTED
        landlock_evidence = (
            "kernel_config_support=False",
            "runtime_abi=unavailable",
        )

    apparmor_state = (
        CapabilityState.AVAILABLE
        if snapshot.apparmor_active
        else (
            CapabilityState.SUPPORTED
            if snapshot.apparmor_kernel_supported
            else CapabilityState.UNSUPPORTED
        )
    )

    no_new_privs_state = (
        CapabilityState.AVAILABLE
        if snapshot.no_new_privs_available
        else CapabilityState.UNAVAILABLE
    )

    primitives = (
        _capability(
            HostPrimitive.CGROUPS_V2,
            cgroup_state,
            f"cgroup_version={snapshot.cgroup_version!r}",
        ),
        _capability(
            HostPrimitive.NAMESPACES,
            namespace_state,
            f"namespaces={','.join(snapshot.namespaces)}",
        ),
        _capability(
            HostPrimitive.SECCOMP,
            seccomp_state,
            f"kernel_supported={snapshot.seccomp_kernel_supported}",
        ),
        _capability(
            HostPrimitive.NO_NEW_PRIVS,
            no_new_privs_state,
            f"available={snapshot.no_new_privs_available}",
            f"active={snapshot.no_new_privs_active}",
        ),
        _capability(
            HostPrimitive.LANDLOCK,
            landlock_state,
            f"kernel_supported={snapshot.landlock_kernel_supported}",
            *landlock_evidence,
        ),
        _capability(
            HostPrimitive.APPARMOR,
            apparmor_state,
            f"kernel_supported={snapshot.apparmor_kernel_supported}",
            f"active={snapshot.apparmor_active}",
        ),
        _capability(
            HostPrimitive.LINUX_CAPABILITIES,
            CapabilityState.OBSERVED,
            f"effective={','.join(snapshot.effective_capabilities)}",
            "cap_eff_source=/proc/self/status",
        ),
        _capability(
            HostPrimitive.SYSTEMD,
            CapabilityState.AVAILABLE
            if snapshot.systemd_available
            else CapabilityState.UNAVAILABLE,
        ),
        _capability(
            HostPrimitive.BUBBLEWRAP,
            CapabilityState.AVAILABLE
            if snapshot.bubblewrap_available
            else CapabilityState.UNAVAILABLE,
        ),
        _capability(
            HostPrimitive.DOCKER,
            CapabilityState.AVAILABLE
            if snapshot.docker_available
            else CapabilityState.UNAVAILABLE,
        ),
        _capability(
            HostPrimitive.NFT,
            CapabilityState.AVAILABLE
            if snapshot.nft_available
            else CapabilityState.UNAVAILABLE,
        ),
        _capability(
            HostPrimitive.IPTABLES,
            CapabilityState.AVAILABLE
            if snapshot.iptables_available
            else CapabilityState.UNAVAILABLE,
        ),
    )

    fingerprint = LinuxHostFingerprint(
        identity=identity,
        primitives=primitives,
    )

    return LinuxHostAbstractionSnapshot(
        identity=identity,
        fingerprint=fingerprint,
        user_id=operations.get_user_id(),
        effective_capabilities=snapshot.effective_capabilities,
        namespaces=snapshot.namespaces,
        notes=snapshot.notes,
    )


class LinuxHostDiscovery:
    """
    Deterministic, read-only host discovery boundary.

    Discovery observes the host and normalizes the result. It does not
    authorize execution, apply controls, alter kernel state, or launch
    workloads.
    """

    def __init__(
        self,
        *,
        detector: LinuxHostCapabilityDetector | None = None,
        operations: LinuxHostDiscoveryOperations | None = None,
    ) -> None:
        self._detector = detector or LinuxHostCapabilityDetector()
        self._operations = operations or _default_operations()

    def discover(self) -> LinuxHostAbstractionSnapshot:
        snapshot = self._detector.detect()

        return _from_snapshot(
            snapshot,
            self._operations,
        )
