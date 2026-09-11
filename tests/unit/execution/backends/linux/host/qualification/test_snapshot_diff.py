from __future__ import annotations

from dataclasses import replace

from lyrion.execution.backends.linux.host.contracts import (
    CapabilityState,
    HostPrimitive,
    HostPrimitiveCapability,
    LinuxHostAbstractionSnapshot,
    LinuxHostFingerprint,
    LinuxHostIdentity,
)
from lyrion.execution.backends.linux.host.qualification.change_contracts import (
    ChangeImpact,
)
from lyrion.execution.backends.linux.host.qualification.snapshot_diff import (
    LinuxHostSnapshotDiff,
)


def _snapshot(
    *,
    os_name: str = "Ubuntu",
    os_version: str = "26.04",
    kernel: str = "6.18.1",
    architecture: str = "x86_64",
    virtualization: str | None = "wsl",
    init_system: str | None = "systemd",
    primitive_state: CapabilityState = CapabilityState.AVAILABLE,
    effective_capabilities: tuple[str, ...] = (),
    namespaces: tuple[str, ...] = ("mnt", "pid", "net"),
) -> LinuxHostAbstractionSnapshot:
    identity = LinuxHostIdentity(
        os_name=os_name,
        os_version=os_version,
        kernel=kernel,
        architecture=architecture,
        virtualization=virtualization,
        init_system=init_system,
    )

    primitives = tuple(
        HostPrimitiveCapability(
            primitive=primitive,
            state=primitive_state,
            evidence=(f"state={primitive_state.value}",),
        )
        for primitive in HostPrimitive
    )

    fingerprint = LinuxHostFingerprint(
        identity=identity,
        primitives=primitives,
    )

    return LinuxHostAbstractionSnapshot(
        identity=identity,
        fingerprint=fingerprint,
        user_id=1000,
        effective_capabilities=effective_capabilities,
        namespaces=namespaces,
        notes=(),
    )


def test_identical_snapshots_have_no_changes() -> None:
    snapshot = _snapshot()

    assert LinuxHostSnapshotDiff().diff(
        previous=snapshot,
        current=snapshot,
    ) == ()


def test_kernel_change_is_high_impact() -> None:
    previous = _snapshot(kernel="6.18.1")
    current = _snapshot(kernel="6.18.2")

    changes = LinuxHostSnapshotDiff().diff(
        previous=previous,
        current=current,
    )

    change = next(
        item
        for item in changes
        if item.component == "host.identity.kernel"
    )

    assert change.impact is ChangeImpact.HIGH


def test_os_version_change_is_critical() -> None:
    previous = _snapshot(os_version="26.04")
    current = _snapshot(os_version="27.04")

    changes = LinuxHostSnapshotDiff().diff(
        previous=previous,
        current=current,
    )

    change = next(
        item
        for item in changes
        if item.component == "host.identity.os_version"
    )

    assert change.impact is ChangeImpact.CRITICAL


def test_architecture_change_is_critical() -> None:
    previous = _snapshot(architecture="x86_64")
    current = _snapshot(architecture="aarch64")

    changes = LinuxHostSnapshotDiff().diff(
        previous=previous,
        current=current,
    )

    change = next(
        item
        for item in changes
        if item.component == "host.identity.architecture"
    )

    assert change.impact is ChangeImpact.CRITICAL


def test_security_primitive_state_change_is_high() -> None:
    previous = _snapshot(
        primitive_state=CapabilityState.AVAILABLE,
    )
    current = _snapshot(
        primitive_state=CapabilityState.UNAVAILABLE,
    )

    changes = LinuxHostSnapshotDiff().diff(
        previous=previous,
        current=current,
    )

    change = next(
        item
        for item in changes
        if item.component == "host.primitive.seccomp.state"
    )

    assert change.impact is ChangeImpact.HIGH


def test_effective_capability_change_is_high() -> None:
    previous = _snapshot(effective_capabilities=())
    current = _snapshot(
        effective_capabilities=("CAP_SYS_ADMIN",),
    )

    changes = LinuxHostSnapshotDiff().diff(
        previous=previous,
        current=current,
    )

    change = next(
        item
        for item in changes
        if item.component == "host.effective_capabilities"
    )

    assert change.impact is ChangeImpact.HIGH


def test_namespace_change_is_high() -> None:
    previous = _snapshot(namespaces=("mnt", "pid"))
    current = _snapshot(namespaces=("mnt", "pid", "net"))

    changes = LinuxHostSnapshotDiff().diff(
        previous=previous,
        current=current,
    )

    change = next(
        item
        for item in changes
        if item.component == "host.namespaces"
    )

    assert change.impact is ChangeImpact.HIGH


def test_user_change_is_medium() -> None:
    previous = _snapshot()
    current = replace(previous, user_id=0)

    changes = LinuxHostSnapshotDiff().diff(
        previous=previous,
        current=current,
    )

    change = next(
        item
        for item in changes
        if item.component == "host.user_id"
    )

    assert change.impact is ChangeImpact.MEDIUM


def test_virtualization_change_is_critical() -> None:
    previous = _snapshot(virtualization="wsl")
    current = _snapshot(virtualization="vmware")

    changes = LinuxHostSnapshotDiff().diff(
        previous=previous,
        current=current,
    )

    change = next(
        item
        for item in changes
        if item.component == "host.identity.virtualization"
    )

    assert change.impact is ChangeImpact.CRITICAL


def test_results_are_deterministically_ordered() -> None:
    previous = _snapshot()
    current = _snapshot(
        kernel="6.18.2",
        architecture="aarch64",
        effective_capabilities=("CAP_SYS_ADMIN",),
    )

    first = LinuxHostSnapshotDiff().diff(
        previous=previous,
        current=current,
    )

    second = LinuxHostSnapshotDiff().diff(
        previous=previous,
        current=current,
    )

    assert first == second

    components = tuple(item.component for item in first)

    assert components == tuple(sorted(components))


def test_notes_are_not_treated_as_host_capability_changes() -> None:
    previous = _snapshot()
    current = replace(
        previous,
        notes=("diagnostic note changed",),
    )

    assert LinuxHostSnapshotDiff().diff(
        previous=previous,
        current=current,
    ) == ()


def test_diff_is_observational_only() -> None:
    previous = _snapshot()
    current = _snapshot(kernel="6.18.2")

    before_previous = previous
    before_current = current

    LinuxHostSnapshotDiff().diff(
        previous=previous,
        current=current,
    )

    assert previous == before_previous
    assert current == before_current
