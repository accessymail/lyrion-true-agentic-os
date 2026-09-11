from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lyrion.execution.backends.contracts import (
    BackendCapabilities,
    ExecutionBackend,
)
from lyrion.execution.backends.linux.capabilities import (
    LinuxHostCapabilityProvider,
    LinuxHostCapabilitySnapshot,
)
from lyrion.execution.backends.linux.profiles import (
    STRICT_LOCAL_PROFILE,
    EnforcementProfileResolver,
)


@dataclass(frozen=True, slots=True)
class LinuxPreparationContext:
    """
    Immutable preparation context.

    The context records the host snapshot and profile evaluation used before
    any future execution implementation is allowed to launch a process.
    """

    host: LinuxHostCapabilitySnapshot
    profile_id: str
    enforcement_ready: bool
    reasons: tuple[str, ...]


class LinuxExecutionBackend(ExecutionBackend):
    """
    Linux execution backend foundation.

    Real process execution remains deliberately disabled until the native
    Linux enforcement implementation and its certification gates are complete.
    """

    BACKEND_ID = "linux-native"

    def __init__(
        self,
        capability_provider: LinuxHostCapabilityProvider | None = None,
        profile_resolver: EnforcementProfileResolver | None = None,
    ) -> None:
        self._capability_provider = (
            capability_provider or LinuxHostCapabilityProvider()
        )
        self._profile_resolver = (
            profile_resolver or EnforcementProfileResolver()
        )
        self._preparation: LinuxPreparationContext | None = None

    @property
    def backend_id(self) -> str:
        return self.BACKEND_ID

    def capabilities(self) -> BackendCapabilities:
        snapshot = self._capability_provider.snapshot()
        evaluation = self._profile_resolver.evaluate(
            STRICT_LOCAL_PROFILE,
            snapshot,
        )

        return BackendCapabilities(
            backend_id=self.BACKEND_ID,
            state=evaluation.state,
            details={
                "profile": STRICT_LOCAL_PROFILE.profile_id.value,
                "os": snapshot.os_name,
                "os_version": snapshot.os_version,
                "kernel": snapshot.kernel,
                "virtualization": snapshot.virtualization,
                "cgroup_version": snapshot.cgroup_version,
                "seccomp_kernel_supported": snapshot.seccomp_kernel_supported,
                "landlock_kernel_supported": snapshot.landlock_kernel_supported,
                "apparmor_kernel_supported": snapshot.apparmor_kernel_supported,
                "apparmor_active": snapshot.apparmor_active,
                "no_new_privs_available": snapshot.no_new_privs_available,
                "enforcement_ready": evaluation.allowed,
                "reasons": evaluation.reasons,
                "notes": snapshot.notes,
            },
        )

    def prepare(self, *args: Any, **kwargs: Any) -> LinuxPreparationContext:
        del args, kwargs

        snapshot = self._capability_provider.snapshot()
        evaluation = self._profile_resolver.evaluate(
            STRICT_LOCAL_PROFILE,
            snapshot,
        )

        if not evaluation.allowed:
            raise RuntimeError(
                "linux-native strict execution preparation failed closed: "
                + "; ".join(evaluation.reasons)
            )

        context = LinuxPreparationContext(
            host=snapshot,
            profile_id=STRICT_LOCAL_PROFILE.profile_id.value,
            enforcement_ready=True,
            reasons=(),
        )

        self._preparation = context
        return context

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        del args, kwargs

        raise NotImplementedError(
            "real Linux execution is intentionally disabled in Step 0.5-B-R3"
        )

    def cleanup(self, *args: Any, **kwargs: Any) -> None:
        del args, kwargs
        self._preparation = None

    def close(self) -> None:
        self._preparation = None
