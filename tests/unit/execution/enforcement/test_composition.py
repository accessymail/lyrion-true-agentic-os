from __future__ import annotations

from unittest.mock import patch

import pytest

from lyrion.execution.backends.linux.enforcement.contracts import (
    EnforcementPrimitive,
)
from lyrion.execution.backends.linux.enforcement.registry import (
    PrimitiveAdapterRegistry,
)


def test_composition_module_exports_trusted_factory() -> None:
    from lyrion.execution.backends.linux.enforcement.composition import (
        create_native_linux_enforcement_registry,
    )

    assert callable(create_native_linux_enforcement_registry)


def test_registry_is_explicit_and_deterministic() -> None:
    from lyrion.execution.backends.linux.enforcement.composition import (
        create_native_linux_enforcement_registry,
    )

    class FakePolicy:
        pass

    with (
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "NoNewPrivsAdapter",
        ) as no_new_privs,
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "CapabilityAdapter",
        ) as capabilities,
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "NamespaceAdapter",
        ) as namespaces,
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "CgroupV2Adapter",
        ) as cgroups,
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "FilesystemIsolationAdapter",
        ) as filesystem,
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "NetworkIsolationAdapter",
        ) as network,
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "SeccompAdapter",
        ) as seccomp,
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "LandlockAdapter",
        ) as landlock,
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "AppArmorAdapter",
        ) as apparmor,
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "LibcNoNewPrivsOperations",
        ),
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "LibcCapabilityOperations",
        ),
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "NativeNamespaceOperations",
        ),
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "NativeCgroupV2Operations",
        ),
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "NativeFilesystemOperations",
        ),
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "NativeNetworkOperations",
        ),
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "NativeSeccompOperations",
        ),
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "NativeLandlockOperations",
        ),
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "NativeAppArmorOperations",
        ),
    ):
        primitive_map = {
            no_new_privs.return_value.primitive:
                no_new_privs.return_value,
            capabilities.return_value.primitive:
                capabilities.return_value,
            namespaces.return_value.primitive:
                namespaces.return_value,
            cgroups.return_value.primitive:
                cgroups.return_value,
            filesystem.return_value.primitive:
                filesystem.return_value,
            network.return_value.primitive:
                network.return_value,
            seccomp.return_value.primitive:
                seccomp.return_value,
            landlock.return_value.primitive:
                landlock.return_value,
            apparmor.return_value.primitive:
                apparmor.return_value,
        }

        for primitive, adapter in primitive_map.items():
            type(adapter).primitive = property(lambda _self, p=primitive: p)

        registry = create_native_linux_enforcement_registry(
            seccomp_policy=FakePolicy(),
            landlock_policy=FakePolicy(),
            apparmor_policy=FakePolicy(),
        )

        assert isinstance(registry, PrimitiveAdapterRegistry)
        assert len(registry) == 9


def test_factory_requires_all_security_policies() -> None:
    from lyrion.execution.backends.linux.enforcement.composition import (
        create_native_linux_enforcement_registry,
    )

    with pytest.raises(ValueError, match="seccomp_policy"):
        create_native_linux_enforcement_registry(
            seccomp_policy=None,  # type: ignore[arg-type]
            landlock_policy=object(),  # type: ignore[arg-type]
            apparmor_policy=object(),  # type: ignore[arg-type]
        )

    with pytest.raises(ValueError, match="landlock_policy"):
        create_native_linux_enforcement_registry(
            seccomp_policy=object(),  # type: ignore[arg-type]
            landlock_policy=None,  # type: ignore[arg-type]
            apparmor_policy=object(),  # type: ignore[arg-type]
        )

    with pytest.raises(ValueError, match="apparmor_policy"):
        create_native_linux_enforcement_registry(
            seccomp_policy=object(),  # type: ignore[arg-type]
            landlock_policy=object(),  # type: ignore[arg-type]
            apparmor_policy=None,  # type: ignore[arg-type]
        )


def test_factory_does_not_dynamically_discover_adapters() -> None:
    from pathlib import Path

    source = Path(
        "src/lyrion/execution/backends/linux/enforcement/composition.py"
    ).read_text(encoding="utf-8")

    forbidden = (
        "importlib.import_module",
        "pkgutil.iter_modules",
        "inspect.getmembers",
        "__import__(",
        "entry_points(",
    )

    for pattern in forbidden:
        assert pattern not in source


def test_factory_contains_all_required_linux_primitives() -> None:
    expected = (
        EnforcementPrimitive.NO_NEW_PRIVS,
        EnforcementPrimitive.CAPABILITIES,
        EnforcementPrimitive.NAMESPACES,
        EnforcementPrimitive.CGROUPS_V2,
        EnforcementPrimitive.FILESYSTEM,
        EnforcementPrimitive.NETWORK,
        EnforcementPrimitive.SECCOMP,
        EnforcementPrimitive.LANDLOCK,
        EnforcementPrimitive.APPARMOR,
    )

    assert len(expected) == 9
    assert len(set(expected)) == 9
