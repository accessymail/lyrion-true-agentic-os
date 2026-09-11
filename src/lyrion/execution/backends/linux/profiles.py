from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from lyrion.execution.backends.contracts import (
    BackendCapabilityState,
)
from lyrion.execution.backends.linux.capabilities import (
    LinuxHostCapabilitySnapshot,
)


class EnforcementProfileId(StrEnum):
    CONTROLLED_LOCAL = "controlled-local"
    STRICT_LOCAL = "strict-local"


@dataclass(frozen=True, slots=True)
class EnforcementProfile:
    profile_id: EnforcementProfileId
    namespaces_required: bool
    cgroups_required: bool
    filesystem_isolation_required: bool
    network_isolation_required: bool
    no_new_privs_required: bool
    capability_reduction_required: bool
    seccomp_required: bool
    landlock_required: bool
    apparmor_required: bool
    evidence_required: bool


CONTROLLED_LOCAL_PROFILE = EnforcementProfile(
    profile_id=EnforcementProfileId.CONTROLLED_LOCAL,
    namespaces_required=False,
    cgroups_required=True,
    filesystem_isolation_required=True,
    network_isolation_required=True,
    no_new_privs_required=True,
    capability_reduction_required=True,
    seccomp_required=False,
    landlock_required=False,
    apparmor_required=False,
    evidence_required=True,
)

STRICT_LOCAL_PROFILE = EnforcementProfile(
    profile_id=EnforcementProfileId.STRICT_LOCAL,
    namespaces_required=True,
    cgroups_required=True,
    filesystem_isolation_required=True,
    network_isolation_required=True,
    no_new_privs_required=True,
    capability_reduction_required=True,
    seccomp_required=True,
    landlock_required=True,
    apparmor_required=True,
    evidence_required=True,
)

# Canonical short aliases retained for internal use.
CONTROLLED_LOCAL = CONTROLLED_LOCAL_PROFILE
STRICT_LOCAL = STRICT_LOCAL_PROFILE


@dataclass(frozen=True, slots=True)
class ProfileEvaluation:
    allowed: bool
    state: BackendCapabilityState
    reasons: tuple[str, ...]


class EnforcementProfileResolver:
    """
    Determines whether a profile can safely be considered enforceable.

    Kernel support is not treated as proof of enforcement readiness.
    """

    def evaluate(
        self,
        profile: EnforcementProfile,
        host: LinuxHostCapabilitySnapshot,
    ) -> ProfileEvaluation:
        reasons: list[str] = []

        if host.virtualization == "wsl":
            reasons.append(
                "native Linux production enforcement is not established on WSL2"
            )

        if profile.namespaces_required and not host.namespaces:
            reasons.append("required namespaces are unavailable")

        if profile.cgroups_required and host.cgroup_version != "v2":
            reasons.append("required cgroup v2 is unavailable")

        if profile.seccomp_required and not host.seccomp_kernel_supported:
            reasons.append("required seccomp kernel support is unavailable")

        if profile.landlock_required and not host.landlock_kernel_supported:
            reasons.append("required Landlock kernel support is unavailable")

        if profile.apparmor_required:
            if not host.apparmor_kernel_supported:
                reasons.append("required AppArmor kernel support is unavailable")
            elif not host.apparmor_active:
                reasons.append("required AppArmor enforcement is not active")

        if profile.no_new_privs_required and not host.no_new_privs_available:
            reasons.append("no_new_privs capability is unavailable")

        if profile.capability_reduction_required and host.effective_capabilities:
            reasons.append("current process retains effective Linux capabilities")

        if not profile.evidence_required:
            reasons.append("enforcement evidence is not required")

        if reasons:
            return ProfileEvaluation(
                allowed=False,
                state=BackendCapabilityState.UNAVAILABLE,
                reasons=tuple(reasons),
            )

        return ProfileEvaluation(
            allowed=True,
            state=BackendCapabilityState.AVAILABLE,
            reasons=(),
        )
