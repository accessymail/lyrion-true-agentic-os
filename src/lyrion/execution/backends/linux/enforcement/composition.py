"""
Trusted Linux enforcement composition root.

This module is the explicit production composition boundary for the Linux
enforcement primitives.

Security properties:
- No dynamic adapter discovery.
- No reflection-based registration.
- No untrusted adapter injection.
- No security-policy generation.
- No authorization decisions.
- No SandboxConfig or ExecutionPolicy mutation.
- No silent fallback.
- Native operation boundaries are constructed explicitly.
- Policy objects are supplied explicitly by trusted application code.
"""

from __future__ import annotations

from lyrion.execution.backends.linux.enforcement.apparmor_policy import (
    AppArmorPolicy,
)
from lyrion.execution.backends.linux.enforcement.landlock_policy import (
    LandlockPolicy,
)
from lyrion.execution.backends.linux.enforcement.primitives.apparmor import (
    AppArmorAdapter,
    AppArmorOperations,
    NativeAppArmorOperations,
)
from lyrion.execution.backends.linux.enforcement.primitives.capabilities import (
    CapabilityAdapter,
    LibcCapabilityOperations,
)
from lyrion.execution.backends.linux.enforcement.primitives.cgroups import (
    CgroupV2Adapter,
    NativeCgroupV2Operations,
)
from lyrion.execution.backends.linux.enforcement.primitives.filesystem_network import (
    FilesystemIsolationAdapter,
    NativeFilesystemOperations,
    NativeNetworkOperations,
    NetworkIsolationAdapter,
)
from lyrion.execution.backends.linux.enforcement.primitives.landlock import (
    LandlockAdapter,
    LandlockOperations,
    NativeLandlockOperations,
)
from lyrion.execution.backends.linux.enforcement.primitives.namespaces import (
    NamespaceAdapter,
    NativeNamespaceOperations,
)
from lyrion.execution.backends.linux.enforcement.primitives.no_new_privs import (
    LibcNoNewPrivsOperations,
    NoNewPrivsAdapter,
)
from lyrion.execution.backends.linux.enforcement.primitives.seccomp import (
    NativeSeccompOperations,
    SeccompAdapter,
    SeccompOperations,
)
from lyrion.execution.backends.linux.enforcement.registry import (
    PrimitiveAdapterRegistry,
)
from lyrion.execution.backends.linux.enforcement.seccomp_attestation import (
    SeccompPolicyAttestation,
)
from lyrion.execution.backends.linux.enforcement.seccomp_policy import (
    SeccompPolicy,
)


def create_native_linux_enforcement_registry(
    *,
    seccomp_policy: SeccompPolicy,
    landlock_policy: LandlockPolicy,
    apparmor_policy: AppArmorPolicy,
    seccomp_attestation: SeccompPolicyAttestation | None = None,
) -> PrimitiveAdapterRegistry:
    """
    Construct the trusted native Linux enforcement registry.

    Security policies are mandatory explicit inputs. This function never
    invents, weakens, or substitutes a policy.

    Native operation objects are deliberately created here rather than
    discovered dynamically. Test doubles must be injected through tests or
    non-production composition roots and must never be silently selected here.

    Construction of this registry does not authorize execution and does not
    establish that every primitive is currently enforceable. The enforcement
    application must still perform supports -> validate -> apply -> verify
    and fail closed if any required primitive cannot be verified.
    """
    if seccomp_policy is None:
        raise ValueError("seccomp_policy is required")

    if landlock_policy is None:
        raise ValueError("landlock_policy is required")

    if apparmor_policy is None:
        raise ValueError("apparmor_policy is required")

    no_new_privs = NoNewPrivsAdapter(
        LibcNoNewPrivsOperations(),
    )

    capabilities = CapabilityAdapter(
        LibcCapabilityOperations(),
    )

    namespaces = NamespaceAdapter(
        NativeNamespaceOperations(),
    )

    cgroups = CgroupV2Adapter(
        NativeCgroupV2Operations(),
    )

    filesystem = FilesystemIsolationAdapter(
        NativeFilesystemOperations(),
    )

    network = NetworkIsolationAdapter(
        NativeNetworkOperations(),
    )

    seccomp_operations: SeccompOperations = NativeSeccompOperations()

    seccomp = SeccompAdapter(
        policy=seccomp_policy,
        operations=seccomp_operations,
        attestation=seccomp_attestation,
    )

    landlock_operations: LandlockOperations = NativeLandlockOperations()

    landlock = LandlockAdapter(
        policy=landlock_policy,
        operations=landlock_operations,
    )

    apparmor_operations: AppArmorOperations = NativeAppArmorOperations()

    apparmor = AppArmorAdapter(
        policy=apparmor_policy,
        operations=apparmor_operations,
    )

    adapters = (
        no_new_privs,
        capabilities,
        namespaces,
        cgroups,
        filesystem,
        network,
        seccomp,
        landlock,
        apparmor,
    )

    registry = PrimitiveAdapterRegistry(adapters)

    return registry


__all__ = [
    "create_native_linux_enforcement_registry",
]
