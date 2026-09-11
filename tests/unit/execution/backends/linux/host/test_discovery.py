from __future__ import annotations

from pathlib import Path

from lyrion.execution.backends.linux.capabilities import (
    LinuxHostCapabilityDetector,
    LinuxHostCapabilitySnapshot,
)
from lyrion.execution.backends.linux.host.contracts import (
    CapabilityState,
    HostPrimitive,
)
from lyrion.execution.backends.linux.host.discovery import (
    LinuxHostDiscovery,
    LinuxHostDiscoveryOperations,
)


class FakeDetector(LinuxHostCapabilityDetector):
    def __init__(self, snapshot: LinuxHostCapabilitySnapshot) -> None:
        self._snapshot = snapshot

    def detect(self) -> LinuxHostCapabilitySnapshot:
        return self._snapshot


def _snapshot() -> LinuxHostCapabilitySnapshot:
    return LinuxHostCapabilitySnapshot(
        os_name="Ubuntu",
        os_version="26.04",
        kernel="6.18.0-test",
        architecture="x86_64",
        virtualization="vmware",
        cgroup_version="v2",
        namespaces=("cgroup", "ipc", "mnt", "net", "pid", "user", "uts"),
        seccomp_kernel_supported=True,
        landlock_kernel_supported=True,
        apparmor_kernel_supported=True,
        apparmor_active=True,
        no_new_privs_available=True,
        no_new_privs_active=False,
        systemd_available=True,
        bubblewrap_available=True,
        docker_available=False,
        nft_available=True,
        iptables_available=False,
        user_id=1000,
        effective_capabilities=(),
        notes=(),
    )


def _operations() -> LinuxHostDiscoveryOperations:
    files = {
        Path("/proc/1/comm"): "systemd",
    }

    return LinuxHostDiscoveryOperations(
        read_file=lambda path: files.get(path),
        command_exists=lambda command: command == "systemctl",
        get_user_id=lambda: 1000,
        get_kernel=lambda: "6.18.0-test",
        get_architecture=lambda: "x86_64",
    )


def test_discovery_is_read_only_and_normalizes_host() -> None:
    discovery = LinuxHostDiscovery(
        detector=FakeDetector(_snapshot()),
        operations=_operations(),
    )

    result = discovery.discover()

    assert result.identity.os_name == "Ubuntu"
    assert result.identity.os_version == "26.04"
    assert result.identity.kernel == "6.18.0-test"
    assert result.identity.architecture == "x86_64"
    assert result.identity.virtualization == "vmware"
    assert result.identity.init_system == "systemd"


def test_security_primitive_states_are_normalized() -> None:
    result = LinuxHostDiscovery(
        detector=FakeDetector(_snapshot()),
        operations=_operations(),
    ).discover()

    assert (
        result.capability(HostPrimitive.CGROUPS_V2).state
        == CapabilityState.AVAILABLE
    )
    assert (
        result.capability(HostPrimitive.SECCOMP).state
        == CapabilityState.SUPPORTED
    )
    assert (
        result.capability(HostPrimitive.LANDLOCK).state
        == CapabilityState.SUPPORTED
    )
    assert (
        result.capability(HostPrimitive.APPARMOR).state
        == CapabilityState.AVAILABLE
    )


def test_unavailable_host_primitive_is_not_reported_as_supported() -> None:
    snapshot = _snapshot()
    snapshot = LinuxHostCapabilitySnapshot(
        **{
            field: getattr(snapshot, field)
            for field in snapshot.__dataclass_fields__
            if field != "seccomp_kernel_supported"
        },
        seccomp_kernel_supported=False,
    )

    result = LinuxHostDiscovery(
        detector=FakeDetector(snapshot),
        operations=_operations(),
    ).discover()

    assert (
        result.capability(HostPrimitive.SECCOMP).state
        == CapabilityState.UNSUPPORTED
    )


def test_discovery_does_not_authorize_execution() -> None:
    result = LinuxHostDiscovery(
        detector=FakeDetector(_snapshot()),
        operations=_operations(),
    ).discover()

    assert not hasattr(result, "authorized")
    assert not hasattr(result, "execution_permitted")


def test_discovery_is_deterministic_for_same_observation() -> None:
    first = LinuxHostDiscovery(
        detector=FakeDetector(_snapshot()),
        operations=_operations(),
    ).discover()

    second = LinuxHostDiscovery(
        detector=FakeDetector(_snapshot()),
        operations=_operations(),
    ).discover()

    assert first == second
    assert first.fingerprint.primitive_ids == second.fingerprint.primitive_ids


def test_landlock_runtime_abi_takes_precedence_over_kernel_config() -> None:
    operations = LinuxHostDiscoveryOperations(
        read_file=lambda path: None,
        command_exists=lambda command: False,
        get_user_id=lambda: 1000,
        get_kernel=lambda: "6.18.0-test",
        get_architecture=lambda: "x86_64",
        get_landlock_abi=lambda: 7,
    )

    result = LinuxHostDiscovery(
        detector=FakeDetector(_snapshot()),
        operations=operations,
    ).discover()

    capability = result.capability(HostPrimitive.LANDLOCK)

    assert capability.state is CapabilityState.AVAILABLE
    assert "runtime_abi=7" in capability.evidence


def test_landlock_kernel_support_without_runtime_abi_is_not_available() -> None:
    operations = LinuxHostDiscoveryOperations(
        read_file=lambda path: None,
        command_exists=lambda command: False,
        get_user_id=lambda: 1000,
        get_kernel=lambda: "6.18.0-test",
        get_architecture=lambda: "x86_64",
        get_landlock_abi=lambda: None,
    )

    result = LinuxHostDiscovery(
        detector=FakeDetector(_snapshot()),
        operations=operations,
    ).discover()

    capability = result.capability(HostPrimitive.LANDLOCK)

    assert capability.state is CapabilityState.SUPPORTED
    assert "runtime_abi=unavailable" in capability.evidence


def test_linux_capability_observation_is_not_privilege_availability() -> None:
    result = LinuxHostDiscovery(
        detector=FakeDetector(_snapshot()),
        operations=_operations(),
    ).discover()

    capability = result.capability(HostPrimitive.LINUX_CAPABILITIES)

    assert capability.state is CapabilityState.OBSERVED
    assert result.effective_capabilities == ()


def test_runtime_landlock_probe_is_dependency_injected() -> None:
    calls = 0

    def probe() -> int:
        nonlocal calls
        calls += 1
        return 7

    operations = LinuxHostDiscoveryOperations(
        read_file=lambda path: None,
        command_exists=lambda command: False,
        get_user_id=lambda: 1000,
        get_kernel=lambda: "6.18.0-test",
        get_architecture=lambda: "x86_64",
        get_landlock_abi=probe,
    )

    LinuxHostDiscovery(
        detector=FakeDetector(_snapshot()),
        operations=operations,
    ).discover()

    assert calls == 1
