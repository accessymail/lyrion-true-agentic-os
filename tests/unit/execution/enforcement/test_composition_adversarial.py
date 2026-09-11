"""Adversarial validation of the trusted Linux composition root."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from lyrion.execution.backends.linux.enforcement.apparmor_policy import (
    AppArmorMode,
    AppArmorPolicy,
)
from lyrion.execution.backends.linux.enforcement.contracts import (
    EnforcementPrimitive,
)
from lyrion.execution.backends.linux.enforcement.landlock_policy import (
    LandlockFilesystemAccess,
    LandlockPolicy,
)
from lyrion.execution.backends.linux.enforcement.registry import (
    PrimitiveAdapterRegistry,
)
from lyrion.execution.backends.linux.enforcement.seccomp_policy import (
    SeccompArchitecture,
    SeccompDefaultAction,
    SeccompPolicy,
)


def _factory():
    from lyrion.execution.backends.linux.enforcement.composition import (
        create_native_linux_enforcement_registry,
    )

    return create_native_linux_enforcement_registry


def _valid_policy_inputs() -> dict[str, object]:
    """Return valid immutable security policies for composition tests."""
    return {
        "seccomp_policy": SeccompPolicy(
            policy_id="R3.2-TEST-SECCOMP",
            policy_version="1.0.0",
            architecture=SeccompArchitecture.X86_64,
            allowed_syscalls=("read", "write"),
            default_action=SeccompDefaultAction.ERRNO,
        ),
        "landlock_policy": LandlockPolicy(
            policy_id="r3.2-test-landlock",
            policy_version="1.0.0",
            minimum_abi=1,
            handled_access_fs=LandlockFilesystemAccess.READ_FILE,
            default_allowed_access_fs=LandlockFilesystemAccess.READ_FILE,
        ),
        "apparmor_policy": AppArmorPolicy(
            profile_name="lyrion-r3-2-test",
            policy_version="1.0.0",
            profile_text=(
                "profile lyrion-r3-2-test {\n"
                "  file,\n"
                "}\n"
            ),
            mode=AppArmorMode.ENFORCE,
        ),
    }


def test_factory_rejects_missing_required_policies() -> None:
    """Security policy omission must fail closed."""
    factory = _factory()
    policies = _valid_policy_inputs()

    with pytest.raises(ValueError, match="seccomp_policy"):
        factory(
            seccomp_policy=None,  # type: ignore[arg-type]
            landlock_policy=policies["landlock_policy"],  # type: ignore[arg-type]
            apparmor_policy=policies["apparmor_policy"],  # type: ignore[arg-type]
        )

    with pytest.raises(ValueError, match="landlock_policy"):
        factory(
            seccomp_policy=policies["seccomp_policy"],  # type: ignore[arg-type]
            landlock_policy=None,  # type: ignore[arg-type]
            apparmor_policy=policies["apparmor_policy"],  # type: ignore[arg-type]
        )

    with pytest.raises(ValueError, match="apparmor_policy"):
        factory(
            seccomp_policy=policies["seccomp_policy"],  # type: ignore[arg-type]
            landlock_policy=policies["landlock_policy"],  # type: ignore[arg-type]
            apparmor_policy=None,  # type: ignore[arg-type]
        )


def test_native_seccomp_construction_failure_has_no_fallback() -> None:
    """Seccomp construction failure must escape instead of downgrading."""
    factory = _factory()

    with patch(
        "lyrion.execution.backends.linux.enforcement.composition."
        "NativeSeccompOperations",
        side_effect=RuntimeError("controlled seccomp construction failure"),
    ):
        with pytest.raises(
            RuntimeError,
            match="controlled seccomp construction failure",
        ):
            factory(**_valid_policy_inputs())


def test_native_landlock_construction_failure_has_no_fallback() -> None:
    """Landlock construction failure must escape instead of downgrading."""
    factory = _factory()

    with patch(
        "lyrion.execution.backends.linux.enforcement.composition."
        "NativeLandlockOperations",
        side_effect=RuntimeError(
            "controlled landlock construction failure"
        ),
    ):
        with pytest.raises(
            RuntimeError,
            match="controlled landlock construction failure",
        ):
            factory(**_valid_policy_inputs())


def test_native_apparmor_construction_failure_has_no_fallback() -> None:
    """AppArmor construction failure must escape instead of downgrading."""
    factory = _factory()

    with patch(
        "lyrion.execution.backends.linux.enforcement.composition."
        "NativeAppArmorOperations",
        side_effect=RuntimeError(
            "controlled apparmor construction failure"
        ),
    ):
        with pytest.raises(
            RuntimeError,
            match="controlled apparmor construction failure",
        ):
            factory(**_valid_policy_inputs())


def test_factory_registry_is_complete_and_unique() -> None:
    """The trusted factory must expose exactly the nine required primitives."""
    factory = _factory()

    registry = factory(**_valid_policy_inputs())

    expected = tuple(EnforcementPrimitive)

    assert isinstance(registry, PrimitiveAdapterRegistry)
    assert len(registry) == len(expected)
    assert registry.identifiers() == expected
    assert len(set(registry.identifiers())) == len(expected)


def test_factory_does_not_expose_authorization_capabilities() -> None:
    """Composition must never become an authorization authority."""
    factory = _factory()

    registry = factory(**_valid_policy_inputs())

    assert not hasattr(registry, "authorize")
    assert not hasattr(registry, "grant")
    assert not hasattr(registry, "admit")
    assert not hasattr(registry, "is_authorized")


def test_factory_source_contains_no_dynamic_registration_path() -> None:
    """Trusted registration must remain explicit and deterministic."""
    from pathlib import Path

    source = Path(
        "src/lyrion/execution/backends/linux/enforcement/composition.py"
    ).read_text(encoding="utf-8")

    forbidden = (
        "importlib.import_module",
        "pkgutil.iter_modules",
        "pkgutil.walk_packages",
        "inspect.getmembers",
        "entry_points(",
        "__import__(",
        "__subclasses__()",
    )

    for pattern in forbidden:
        assert pattern not in source


def test_factory_construction_does_not_apply_enforcement() -> None:
    """Constructing the registry must not invoke adapter lifecycle methods."""
    factory = _factory()

    with (
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "NoNewPrivsAdapter"
        ) as no_new_privs,
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "CapabilityAdapter"
        ) as capabilities,
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "NamespaceAdapter"
        ) as namespaces,
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "CgroupV2Adapter"
        ) as cgroups,
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "FilesystemIsolationAdapter"
        ) as filesystem,
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "NetworkIsolationAdapter"
        ) as network,
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "SeccompAdapter"
        ) as seccomp,
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "LandlockAdapter"
        ) as landlock,
        patch(
            "lyrion.execution.backends.linux.enforcement.composition."
            "AppArmorAdapter"
        ) as apparmor,
    ):
        adapters = (
            no_new_privs.return_value,
            capabilities.return_value,
            namespaces.return_value,
            cgroups.return_value,
            filesystem.return_value,
            network.return_value,
            seccomp.return_value,
            landlock.return_value,
            apparmor.return_value,
        )

        for primitive, adapter in zip(
            EnforcementPrimitive,
            adapters,
            strict=True,
        ):
            type(adapter).primitive = property(
                lambda _self, value=primitive: value
            )

        registry = factory(**_valid_policy_inputs())

        assert isinstance(registry, PrimitiveAdapterRegistry)

        for adapter in adapters:
            assert not adapter.supports.called
            assert not adapter.validate.called
            assert not adapter.apply.called
            assert not adapter.verify.called
            assert not adapter.evidence.called


def test_factory_does_not_silently_replace_a_failed_native_boundary() -> None:
    """A failed native boundary must not be replaced by a test/fake adapter."""
    factory = _factory()

    with patch(
        "lyrion.execution.backends.linux.enforcement.composition."
        "NativeNamespaceOperations",
        side_effect=OSError("controlled namespace boundary failure"),
    ):
        with pytest.raises(
            OSError,
            match="controlled namespace boundary failure",
        ):
            factory(**_valid_policy_inputs())
