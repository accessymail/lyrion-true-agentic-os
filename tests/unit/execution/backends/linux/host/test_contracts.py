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


def _identity() -> LinuxHostIdentity:
    return LinuxHostIdentity(
        os_name="Ubuntu",
        os_version="26.04",
        kernel="6.18.0-test",
        architecture="x86_64",
        virtualization=None,
        init_system="systemd",
    )


def test_host_identity_is_immutable() -> None:
    identity = _identity()

    with pytest.raises(AttributeError):
        identity.os_name = "Debian"  # type: ignore[misc]


def test_capability_observation_is_immutable() -> None:
    capability = HostPrimitiveCapability(
        primitive=HostPrimitive.CGROUPS_V2,
        state=CapabilityState.AVAILABLE,
    )

    with pytest.raises(AttributeError):
        capability.state = CapabilityState.UNKNOWN  # type: ignore[misc]


def test_fingerprint_is_deterministically_ordered() -> None:
    fingerprint = LinuxHostFingerprint(
        identity=_identity(),
        primitives=(
            HostPrimitiveCapability(
                primitive=HostPrimitive.CGROUPS_V2,
                state=CapabilityState.AVAILABLE,
            ),
            HostPrimitiveCapability(
                primitive=HostPrimitive.SECCOMP,
                state=CapabilityState.SUPPORTED,
            ),
        ),
    )

    assert fingerprint.primitive_ids == (
        "cgroups_v2",
        "seccomp",
    )


def test_fingerprint_lookup_is_explicit() -> None:
    fingerprint = LinuxHostFingerprint(
        identity=_identity(),
        primitives=(
            HostPrimitiveCapability(
                primitive=HostPrimitive.SECCOMP,
                state=CapabilityState.SUPPORTED,
            ),
        ),
    )

    assert (
        fingerprint.primitive(HostPrimitive.SECCOMP).state
        == CapabilityState.SUPPORTED
    )


def test_missing_primitive_fails_closed_at_lookup_boundary() -> None:
    fingerprint = LinuxHostFingerprint(
        identity=_identity(),
        primitives=(),
    )

    with pytest.raises(KeyError):
        fingerprint.primitive(HostPrimitive.SECCOMP)


def test_snapshot_is_immutable() -> None:
    identity = _identity()
    fingerprint = LinuxHostFingerprint(
        identity=identity,
        primitives=(),
    )

    snapshot = LinuxHostAbstractionSnapshot(
        identity=identity,
        fingerprint=fingerprint,
        user_id=1000,
        effective_capabilities=(),
        namespaces=(),
        notes=(),
    )

    with pytest.raises(AttributeError):
        snapshot.user_id = 0  # type: ignore[misc]
