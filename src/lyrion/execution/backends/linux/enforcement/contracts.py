"""Immutable contracts for Linux execution enforcement planning."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from lyrion.execution.sandbox import (
    EnvironmentMode,
    FilesystemMode,
    IsolationLevel,
    NetworkMode,
    SandboxConfig,
)


class EnforcementPrimitive(StrEnum):
    """Linux security primitives represented by the enforcement plan."""

    NO_NEW_PRIVS = "no_new_privs"
    CAPABILITIES = "capabilities"
    NAMESPACES = "namespaces"
    CGROUPS_V2 = "cgroups_v2"
    FILESYSTEM = "filesystem"
    NETWORK = "network"
    SECCOMP = "seccomp"
    LANDLOCK = "landlock"
    APPARMOR = "apparmor"


class EnforcementState(StrEnum):
    """Lifecycle state of an enforcement requirement."""

    REQUESTED = "requested"
    SUPPORTED = "supported"
    PLANNED = "planned"
    APPLIED = "applied"
    VERIFIED = "verified"
    FAILED = "failed"


class EnforcementPlanStatus(StrEnum):
    """Overall planning result."""

    READY = "ready"
    REJECTED = "rejected"


class PrivilegePlan(BaseModel):
    """Privilege-reduction requirements for one execution."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    no_new_privs_required: bool = True
    capability_reduction_required: bool = True


class NamespacePlan(BaseModel):
    """Namespace-isolation requirements."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    required: bool
    process_isolation: bool = True
    mount_isolation: bool = True
    network_isolation: bool = True


class CgroupPlan(BaseModel):
    """cgroup v2 resource-control requirements."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    required: bool
    max_runtime_seconds: float = Field(gt=0)
    max_memory_mb: int = Field(gt=0)
    max_output_bytes: int = Field(gt=0)
    max_cpu_seconds: float = Field(gt=0)


class FilesystemPlan(BaseModel):
    """Filesystem isolation requirements derived from SandboxConfig."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    required: bool
    mode: FilesystemMode
    writable_paths: tuple[str, ...] = ()
    read_only_paths: tuple[str, ...] = ()


class NetworkPlan(BaseModel):
    """Network isolation requirements derived from SandboxConfig."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    required: bool
    mode: NetworkMode
    network_access_allowed: bool


class EnvironmentPlan(BaseModel):
    """Environment exposure requirements."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    mode: EnvironmentMode
    allowed_keys: tuple[str, ...] = ()


class SeccompPlan(BaseModel):
    """Seccomp requirements without containing an executable filter."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    required: bool


class LandlockPlan(BaseModel):
    """Landlock requirements."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    required: bool


class AppArmorPlan(BaseModel):
    """AppArmor requirements."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    required: bool


class EnforcementRequirement(BaseModel):
    """One immutable primitive-level enforcement requirement."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    primitive: EnforcementPrimitive
    state: EnforcementState
    required: bool
    reason: str = Field(min_length=1, max_length=1000)


class LinuxEnforcementPlan(BaseModel):
    """
    Immutable Linux enforcement plan.

    This is a planning contract only. It does not claim that any control has
    been applied or verified.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    status: EnforcementPlanStatus
    isolation_level: IsolationLevel

    privilege: PrivilegePlan
    namespaces: NamespacePlan
    cgroups: CgroupPlan
    filesystem: FilesystemPlan
    network: NetworkPlan
    environment: EnvironmentPlan
    seccomp: SeccompPlan
    landlock: LandlockPlan
    apparmor: AppArmorPlan

    requirements: tuple[EnforcementRequirement, ...]

    def required_primitives(self) -> tuple[EnforcementPrimitive, ...]:
        """Return required primitives in deterministic plan order."""
        return tuple(
            requirement.primitive
            for requirement in self.requirements
            if requirement.required
        )

    def has_failed_requirements(self) -> bool:
        """Return whether any requirement is explicitly failed."""
        return any(
            requirement.state is EnforcementState.FAILED
            for requirement in self.requirements
        )

    def assert_planning_only(self) -> None:
        """
        Reject plans that falsely claim application or verification.

        C1 planners must never emit APPLIED or VERIFIED states.
        """
        invalid_states = {
            EnforcementState.APPLIED,
            EnforcementState.VERIFIED,
        }

        if any(
            requirement.state in invalid_states
            for requirement in self.requirements
        ):
            raise ValueError(
                "C1 enforcement plans cannot claim applied or verified controls"
            )

    @classmethod
    def rejected(
        cls,
        sandbox: SandboxConfig,
        reason: str,
    ) -> LinuxEnforcementPlan:
        """Construct a deterministic rejected plan."""
        requirements = tuple(
            EnforcementRequirement(
                primitive=primitive,
                state=EnforcementState.FAILED,
                required=True,
                reason=reason,
            )
            for primitive in EnforcementPrimitive
        )

        limits = sandbox.resource_limits

        return cls(
            status=EnforcementPlanStatus.REJECTED,
            isolation_level=sandbox.isolation_level,
            privilege=PrivilegePlan(),
            namespaces=NamespacePlan(
                required=True,
            ),
            cgroups=CgroupPlan(
                required=True,
                max_runtime_seconds=limits.max_runtime_seconds,
                max_memory_mb=limits.max_memory_mb,
                max_output_bytes=limits.max_output_bytes,
                max_cpu_seconds=limits.max_cpu_seconds,
            ),
            filesystem=FilesystemPlan(
                required=True,
                mode=sandbox.filesystem_mode,
                writable_paths=tuple(
                    item.path for item in sandbox.writable_paths
                ),
                read_only_paths=tuple(
                    item.path for item in sandbox.read_only_paths
                ),
            ),
            network=NetworkPlan(
                required=True,
                mode=sandbox.network_mode,
                network_access_allowed=False,
            ),
            environment=EnvironmentPlan(
                mode=sandbox.environment_mode,
                allowed_keys=sandbox.allowed_environment_keys,
            ),
            seccomp=SeccompPlan(required=True),
            landlock=LandlockPlan(required=True),
            apparmor=AppArmorPlan(required=True),
            requirements=requirements,
        )
