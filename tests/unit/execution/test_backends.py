from __future__ import annotations

from dataclasses import FrozenInstanceError
from unittest.mock import Mock

import pytest

from lyrion.execution.backends.contracts import (
    BackendCapabilities,
    BackendCapabilityState,
)
from lyrion.execution.backends.linux.backend import LinuxExecutionBackend
from lyrion.execution.backends.linux.capabilities import (
    LinuxHostCapabilitySnapshot,
)
from lyrion.execution.backends.linux.profiles import (
    STRICT_LOCAL_PROFILE,
    EnforcementProfileId,
    EnforcementProfileResolver,
)
from lyrion.execution.backends.registry import ExecutionBackendRegistry


def _snapshot(**overrides: object) -> LinuxHostCapabilitySnapshot:
    values: dict[str, object] = {
        "os_name": "Ubuntu",
        "os_version": "26.04",
        "kernel": "6.18.0",
        "architecture": "x86_64",
        "virtualization": None,
        "cgroup_version": "v2",
        "namespaces": (
            "cgroup",
            "ipc",
            "mnt",
            "net",
            "pid",
            "user",
            "uts",
        ),
        "seccomp_kernel_supported": True,
        "landlock_kernel_supported": True,
        "apparmor_kernel_supported": True,
        "apparmor_active": True,
        "no_new_privs_available": True,
        "no_new_privs_active": False,
        "systemd_available": True,
        "bubblewrap_available": True,
        "docker_available": False,
        "nft_available": True,
        "iptables_available": False,
        "user_id": 1000,
        "effective_capabilities": (),
        "notes": (),
    }
    values.update(overrides)
    return LinuxHostCapabilitySnapshot(**values)


def test_backend_capabilities_are_immutable() -> None:
    capabilities = BackendCapabilities(
        backend_id="linux-native",
        state=BackendCapabilityState.AVAILABLE,
        details={},
    )

    with pytest.raises(FrozenInstanceError):
        capabilities.state = BackendCapabilityState.UNAVAILABLE  # type: ignore[misc]


def test_strict_profile_passes_when_all_required_primitives_are_ready() -> None:
    result = EnforcementProfileResolver().evaluate(
        STRICT_LOCAL_PROFILE,
        _snapshot(),
    )

    assert result.allowed is True
    assert result.state is BackendCapabilityState.AVAILABLE
    assert result.reasons == ()


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("virtualization", "wsl", "native Linux production enforcement"),
        ("cgroup_version", None, "cgroup v2"),
        ("namespaces", (), "namespaces"),
        ("seccomp_kernel_supported", False, "seccomp"),
        ("landlock_kernel_supported", False, "Landlock"),
        ("apparmor_kernel_supported", False, "AppArmor"),
        ("apparmor_active", False, "AppArmor"),
        ("no_new_privs_available", False, "no_new_privs"),
        ("effective_capabilities", ("0x1",), "effective Linux capabilities"),
    ],
)
def test_strict_profile_fails_closed(
    field: str,
    value: object,
    expected: str,
) -> None:
    result = EnforcementProfileResolver().evaluate(
        STRICT_LOCAL_PROFILE,
        _snapshot(**{field: value}),
    )

    assert result.allowed is False
    assert result.state is BackendCapabilityState.UNAVAILABLE
    assert any(expected in reason for reason in result.reasons)


def test_linux_backend_does_not_claim_available_on_wsl2() -> None:
    provider = Mock()
    provider.snapshot.return_value = _snapshot(virtualization="wsl")

    backend = LinuxExecutionBackend(capability_provider=provider)
    capabilities = backend.capabilities()

    assert capabilities.state is BackendCapabilityState.UNAVAILABLE
    assert capabilities.details["enforcement_ready"] is False


def test_linux_backend_prepare_fails_closed_on_wsl2() -> None:
    provider = Mock()
    provider.snapshot.return_value = _snapshot(virtualization="wsl")

    backend = LinuxExecutionBackend(capability_provider=provider)

    with pytest.raises(RuntimeError, match="failed closed"):
        backend.prepare()


def test_real_execution_remains_disabled() -> None:
    backend = LinuxExecutionBackend(
        capability_provider=Mock(snapshot=Mock(return_value=_snapshot()))
    )

    with pytest.raises(
        NotImplementedError,
        match="intentionally disabled",
    ):
        backend.execute()


def test_prepare_returns_immutable_context_on_ready_host() -> None:
    provider = Mock()
    provider.snapshot.return_value = _snapshot()

    backend = LinuxExecutionBackend(capability_provider=provider)
    context = backend.prepare()

    assert context.profile_id == "strict-local"
    assert context.enforcement_ready is True
    assert context.reasons == ()

    with pytest.raises(FrozenInstanceError):
        context.enforcement_ready = False  # type: ignore[misc]


def test_cleanup_clears_preparation() -> None:
    provider = Mock()
    provider.snapshot.return_value = _snapshot()

    backend = LinuxExecutionBackend(capability_provider=provider)

    backend.prepare()
    backend.cleanup()

    assert backend._preparation is None  # noqa: SLF001


def test_strict_profile_identifier_is_stable() -> None:
    assert EnforcementProfileId.STRICT_LOCAL.value == "strict-local"


def test_registry_rejects_duplicate_backend_identifier() -> None:
    registry = ExecutionBackendRegistry()

    first = Mock()
    first.backend_id = "linux-native"
    first.capabilities.return_value = Mock()
    first.prepare.return_value = None
    first.execute.return_value = None
    first.cleanup.return_value = None
    first.close.return_value = None

    second = Mock()
    second.backend_id = "linux-native"

    registry.register(first)

    with pytest.raises(ValueError):
        registry.register(second)


def test_registry_fails_closed_for_missing_backend() -> None:
    registry = ExecutionBackendRegistry()

    with pytest.raises(LookupError):
        registry.resolve("does-not-exist")
