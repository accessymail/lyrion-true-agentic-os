"""Deterministic Linux enforcement-plan construction."""

from __future__ import annotations

from lyrion.execution.backends.linux.enforcement.contracts import (
    AppArmorPlan,
    CgroupPlan,
    EnforcementPlanStatus,
    EnforcementPrimitive,
    EnforcementRequirement,
    EnforcementState,
    EnvironmentPlan,
    FilesystemPlan,
    LandlockPlan,
    LinuxEnforcementPlan,
    NamespacePlan,
    NetworkPlan,
    PrivilegePlan,
    SeccompPlan,
)
from lyrion.execution.sandbox import (
    FilesystemMode,
    IsolationLevel,
    NetworkMode,
    SandboxConfig,
)


class LinuxEnforcementPlanner:
    """
    Translate an already-validated SandboxConfig into an enforcement plan.

    The planner performs no host mutation and does not execute commands.
    """

    def plan(
        self,
        sandbox: SandboxConfig,
    ) -> LinuxEnforcementPlan:
        """Build a deterministic, planning-only enforcement contract."""
        requirements = self._requirements(sandbox)

        plan = LinuxEnforcementPlan(
            status=EnforcementPlanStatus.READY,
            isolation_level=sandbox.isolation_level,
            privilege=PrivilegePlan(
                no_new_privs_required=True,
                capability_reduction_required=True,
            ),
            namespaces=NamespacePlan(
                required=sandbox.isolation_level is not IsolationLevel.MINIMAL,
                process_isolation=True,
                mount_isolation=True,
                network_isolation=sandbox.network_mode is not NetworkMode.ENABLED,
            ),
            cgroups=CgroupPlan(
                required=True,
                max_runtime_seconds=sandbox.resource_limits.max_runtime_seconds,
                max_memory_mb=sandbox.resource_limits.max_memory_mb,
                max_output_bytes=sandbox.resource_limits.max_output_bytes,
                max_cpu_seconds=sandbox.resource_limits.max_cpu_seconds,
            ),
            filesystem=FilesystemPlan(
                required=sandbox.filesystem_mode is not FilesystemMode.NONE,
                mode=sandbox.filesystem_mode,
                writable_paths=tuple(
                    item.path for item in sandbox.writable_paths
                ),
                read_only_paths=tuple(
                    item.path for item in sandbox.read_only_paths
                ),
            ),
            network=NetworkPlan(
                required=sandbox.network_mode is not NetworkMode.ENABLED,
                mode=sandbox.network_mode,
                network_access_allowed=False,
            ),
            environment=EnvironmentPlan(
                mode=sandbox.environment_mode,
                allowed_keys=sandbox.allowed_environment_keys,
            ),
            seccomp=SeccompPlan(
                required=sandbox.isolation_level
                is sandbox.isolation_level.STRICT,
            ),
            landlock=LandlockPlan(
                required=sandbox.isolation_level
                is sandbox.isolation_level.STRICT,
            ),
            apparmor=AppArmorPlan(
                required=sandbox.isolation_level
                is sandbox.isolation_level.STRICT,
            ),
            requirements=requirements,
        )

        plan.assert_planning_only()
        return plan

    def _requirements(
        self,
        sandbox: SandboxConfig,
    ) -> tuple[EnforcementRequirement, ...]:
        """Build requirements in stable security-control order."""
        strict = sandbox.isolation_level.value == "STRICT"

        return (
            EnforcementRequirement(
                primitive=EnforcementPrimitive.NO_NEW_PRIVS,
                state=EnforcementState.PLANNED,
                required=True,
                reason="Privilege escalation prevention is mandatory.",
            ),
            EnforcementRequirement(
                primitive=EnforcementPrimitive.CAPABILITIES,
                state=EnforcementState.PLANNED,
                required=True,
                reason="Execution must run with reduced Linux capabilities.",
            ),
            EnforcementRequirement(
                primitive=EnforcementPrimitive.NAMESPACES,
                state=EnforcementState.PLANNED,
                required=sandbox.isolation_level.value != "MINIMAL",
                reason="Namespace isolation follows the requested isolation level.",
            ),
            EnforcementRequirement(
                primitive=EnforcementPrimitive.CGROUPS_V2,
                state=EnforcementState.PLANNED,
                required=True,
                reason="Resource limits require cgroup v2 enforcement.",
            ),
            EnforcementRequirement(
                primitive=EnforcementPrimitive.FILESYSTEM,
                state=EnforcementState.PLANNED,
                required=sandbox.filesystem_mode.value != "NONE",
                reason="Filesystem access must follow the sandbox filesystem mode.",
            ),
            EnforcementRequirement(
                primitive=EnforcementPrimitive.NETWORK,
                state=EnforcementState.PLANNED,
                required=sandbox.network_mode.value != "ENABLED",
                reason="Network access must remain bounded by the sandbox policy.",
            ),
            EnforcementRequirement(
                primitive=EnforcementPrimitive.SECCOMP,
                state=EnforcementState.PLANNED,
                required=strict,
                reason="Strict isolation requires syscall filtering.",
            ),
            EnforcementRequirement(
                primitive=EnforcementPrimitive.LANDLOCK,
                state=EnforcementState.PLANNED,
                required=strict,
                reason="Strict isolation requires kernel-enforced filesystem restrictions.",
            ),
            EnforcementRequirement(
                primitive=EnforcementPrimitive.APPARMOR,
                state=EnforcementState.PLANNED,
                required=strict,
                reason="Strict isolation requires mandatory access-control policy.",
            ),
        )
