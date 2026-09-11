"""Linux filesystem and network isolation enforcement adapters.

C2.2-C5 owns configuration of filesystem and network restrictions inside
the already-established execution boundary.

Security properties:
- requirements come exclusively from the typed Linux enforcement plan;
- filesystem and network controls remain separate primitive adapters;
- low-level host operations are dependency-injected;
- apply() never reports VERIFIED;
- verification independently observes enforcement state;
- required-control failures are fail-closed;
- no controller/root namespace mutation is performed here;
- network RESTRICTED is not given an invented enforcement semantic;
- native operations remain unavailable until the Linux process supervisor
  establishes the execution boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from lyrion.execution.backends.linux.enforcement.adapter import PrimitiveAdapter
from lyrion.execution.backends.linux.enforcement.application import (
    EnforcementApplicationContext,
    EnforcementEvidence,
    EnforcementPrimitiveResult,
)
from lyrion.execution.backends.linux.enforcement.contracts import (
    EnforcementPrimitive,
    EnforcementRequirement,
    EnforcementState,
    LinuxEnforcementPlan,
)
from lyrion.execution.sandbox import FilesystemMode, NetworkMode


@dataclass(frozen=True, slots=True)
class FilesystemIsolationState:
    """Observed filesystem isolation state."""

    mode: FilesystemMode
    writable_paths: tuple[str, ...]
    read_only_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NetworkIsolationState:
    """Observed network isolation state."""

    mode: NetworkMode
    network_access_allowed: bool


class FilesystemOperations(Protocol):
    """Low-level filesystem-isolation operation boundary."""

    def prepare_mount_namespace(self) -> None:
        """Prepare the isolated mount namespace for filesystem controls."""

    def apply_filesystem_mode(
        self,
        mode: FilesystemMode,
    ) -> None:
        """Apply the requested filesystem isolation mode."""

    def apply_writable_paths(
        self,
        paths: tuple[str, ...],
    ) -> None:
        """Configure explicitly writable filesystem paths."""

    def apply_read_only_paths(
        self,
        paths: tuple[str, ...],
    ) -> None:
        """Configure explicitly read-only filesystem paths."""

    def get_filesystem_state(self) -> FilesystemIsolationState:
        """Independently observe filesystem isolation state."""


class NetworkOperations(Protocol):
    """Low-level network-isolation operation boundary."""

    def prepare_network_namespace(self) -> None:
        """Prepare the isolated network namespace."""

    def apply_network_mode(
        self,
        mode: NetworkMode,
        network_access_allowed: bool,
    ) -> None:
        """Apply the requested network policy."""

    def get_network_state(self) -> NetworkIsolationState:
        """Independently observe network isolation state."""


class NativeFilesystemOperations:
    """Native filesystem-operation placeholder for the Linux supervisor."""

    def prepare_mount_namespace(self) -> None:
        raise OSError(
            "native filesystem operations require the Linux process boundary"
        )

    def apply_filesystem_mode(
        self,
        mode: FilesystemMode,
    ) -> None:
        del mode
        raise OSError(
            "native filesystem operations require the Linux process boundary"
        )

    def apply_writable_paths(
        self,
        paths: tuple[str, ...],
    ) -> None:
        del paths
        raise OSError(
            "native filesystem operations require the Linux process boundary"
        )

    def apply_read_only_paths(
        self,
        paths: tuple[str, ...],
    ) -> None:
        del paths
        raise OSError(
            "native filesystem operations require the Linux process boundary"
        )

    def get_filesystem_state(self) -> FilesystemIsolationState:
        raise OSError(
            "native filesystem operations require the Linux process boundary"
        )


class NativeNetworkOperations:
    """Native network-operation placeholder for the Linux supervisor."""

    def prepare_network_namespace(self) -> None:
        raise OSError(
            "native network operations require the Linux process boundary"
        )

    def apply_network_mode(
        self,
        mode: NetworkMode,
        network_access_allowed: bool,
    ) -> None:
        del mode, network_access_allowed
        raise OSError(
            "native network operations require the Linux process boundary"
        )

    def get_network_state(self) -> NetworkIsolationState:
        raise OSError(
            "native network operations require the Linux process boundary"
        )


class FilesystemIsolationAdapter(PrimitiveAdapter):
    """Filesystem-isolation primitive adapter."""

    primitive = EnforcementPrimitive.FILESYSTEM

    def __init__(self, operations: FilesystemOperations) -> None:
        self._operations = operations

    def supports(self, plan: LinuxEnforcementPlan) -> bool:
        """Return whether the plan contains a filesystem requirement."""
        return self._requirement(plan) is not None

    def validate(
        self,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Validate filesystem requirements without changing host state."""
        requirement = self._requirement(plan)

        if requirement is None:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason="filesystem requirement is absent",
            )

        filesystem = plan.filesystem

        if requirement.required != filesystem.required:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=(
                    "filesystem requirement and filesystem plan have "
                    "inconsistent required state"
                ),
            )

        if not filesystem.required:
            return self._result(
                plan=plan,
                state=EnforcementState.PLANNED,
                success=True,
                reason="filesystem isolation is not required",
            )

        if filesystem.mode is FilesystemMode.NONE:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=(
                    "filesystem enforcement is required but filesystem "
                    "mode is NONE"
                ),
            )

        if set(filesystem.writable_paths) & set(
            filesystem.read_only_paths
        ):
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=(
                    "filesystem path cannot be both writable and "
                    "read-only"
                ),
            )

        return self._result(
            plan=plan,
            state=EnforcementState.SUPPORTED,
            success=True,
            reason="filesystem isolation requirement is structurally valid",
        )

    def apply(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Apply filesystem restrictions; never claim verification."""
        del context

        validation = self.validate(plan)

        if validation.state is EnforcementState.FAILED:
            return validation

        filesystem = plan.filesystem

        if not filesystem.required:
            return self._result(
                plan=plan,
                state=EnforcementState.APPLIED,
                success=True,
                reason="filesystem isolation is not required",
            )

        try:
            self._operations.prepare_mount_namespace()
            self._operations.apply_filesystem_mode(filesystem.mode)

            if filesystem.writable_paths:
                self._operations.apply_writable_paths(
                    filesystem.writable_paths
                )

            if filesystem.read_only_paths:
                self._operations.apply_read_only_paths(
                    filesystem.read_only_paths
                )

            return self._result(
                plan=plan,
                state=EnforcementState.APPLIED,
                success=True,
                reason=(
                    "filesystem isolation configuration applied; "
                    "independent verification is required"
                ),
            )

        except (OSError, ValueError) as exc:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=f"filesystem isolation failed: {exc}",
            )

    def verify(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Independently verify filesystem isolation state."""
        del context

        validation = self.validate(plan)

        if validation.state is EnforcementState.FAILED:
            return validation

        filesystem = plan.filesystem

        if not filesystem.required:
            evidence = (
                EnforcementEvidence.verified(
                    primitive=self.primitive,
                    evidence_type="filesystem_policy",
                    observation="Filesystem isolation is not required.",
                ),
            )
            return self._result(
                plan=plan,
                state=EnforcementState.VERIFIED,
                success=True,
                reason="filesystem isolation is not required",
                evidence=evidence,
            )

        try:
            current = self._operations.get_filesystem_state()

            if current.mode is not filesystem.mode:
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason=(
                        "filesystem mode verification failed: "
                        f"expected {filesystem.mode.value}, "
                        f"observed {current.mode.value}"
                    ),
                )

            if current.writable_paths != filesystem.writable_paths:
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason="writable filesystem paths verification failed",
                )

            if current.read_only_paths != filesystem.read_only_paths:
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason="read-only filesystem paths verification failed",
                )

            evidence = (
                EnforcementEvidence.verified(
                    primitive=self.primitive,
                    evidence_type="filesystem_state",
                    observation=(
                        "Filesystem mode and configured writable/read-only "
                        "paths were independently verified."
                    ),
                ),
            )

            return self._result(
                plan=plan,
                state=EnforcementState.VERIFIED,
                success=True,
                reason="filesystem isolation independently verified",
                evidence=evidence,
            )

        except (OSError, ValueError) as exc:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=f"filesystem verification failed: {exc}",
            )

    def evidence(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> tuple[EnforcementEvidence, ...]:
        """Return independently collected filesystem evidence."""
        return self.verify(context, plan).evidence

    def _result(
        self,
        *,
        plan: LinuxEnforcementPlan,
        state: EnforcementState,
        success: bool,
        reason: str,
        evidence: tuple[EnforcementEvidence, ...] = (),
    ) -> EnforcementPrimitiveResult:
        """Construct a result using the authoritative result contract."""
        requirement = self._requirement(plan)
        required = requirement.required if requirement is not None else True

        return EnforcementPrimitiveResult(
            primitive=self.primitive,
            required=required,
            state=state,
            success=success,
            reason=reason,
            evidence=evidence,
        )

    @staticmethod
    def _requirement(
        plan: LinuxEnforcementPlan,
    ) -> EnforcementRequirement | None:
        """Return the authoritative filesystem requirement."""
        return next(
            (
                requirement
                for requirement in plan.requirements
                if requirement.primitive is EnforcementPrimitive.FILESYSTEM
            ),
            None,
        )


class NetworkIsolationAdapter(PrimitiveAdapter):
    """Network-isolation primitive adapter."""

    primitive = EnforcementPrimitive.NETWORK

    def __init__(self, operations: NetworkOperations) -> None:
        self._operations = operations

    def supports(self, plan: LinuxEnforcementPlan) -> bool:
        """Return whether the plan contains a network requirement."""
        return self._requirement(plan) is not None

    def validate(
        self,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Validate network requirements without changing host state."""
        requirement = self._requirement(plan)

        if requirement is None:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason="network requirement is absent",
            )

        network = plan.network

        if requirement.required != network.required:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=(
                    "network requirement and network plan have "
                    "inconsistent required state"
                ),
            )

        if not network.required:
            return self._result(
                plan=plan,
                state=EnforcementState.PLANNED,
                success=True,
                reason="network isolation is not required",
            )

        if network.mode is NetworkMode.ENABLED:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=(
                    "network requirement is marked required while "
                    "network mode is ENABLED"
                ),
            )

        # RESTRICTED intentionally remains an explicit mode rather than
        # inventing a firewall/allowlist implementation in C2.2-C5-R1.
        return self._result(
            plan=plan,
            state=EnforcementState.SUPPORTED,
            success=True,
            reason="network isolation requirement is structurally valid",
        )

    def apply(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Apply network restrictions; never claim verification."""
        del context

        validation = self.validate(plan)

        if validation.state is EnforcementState.FAILED:
            return validation

        network = plan.network

        if not network.required:
            return self._result(
                plan=plan,
                state=EnforcementState.APPLIED,
                success=True,
                reason="network isolation is not required",
            )

        try:
            self._operations.prepare_network_namespace()
            self._operations.apply_network_mode(
                network.mode,
                network.network_access_allowed,
            )

            return self._result(
                plan=plan,
                state=EnforcementState.APPLIED,
                success=True,
                reason=(
                    "network isolation configuration applied; "
                    "independent verification is required"
                ),
            )

        except (OSError, ValueError) as exc:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=f"network isolation failed: {exc}",
            )

    def verify(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Independently verify network isolation state."""
        del context

        validation = self.validate(plan)

        if validation.state is EnforcementState.FAILED:
            return validation

        network = plan.network

        if not network.required:
            evidence = (
                EnforcementEvidence.verified(
                    primitive=self.primitive,
                    evidence_type="network_policy",
                    observation="Network isolation is not required.",
                ),
            )
            return self._result(
                plan=plan,
                state=EnforcementState.VERIFIED,
                success=True,
                reason="network isolation is not required",
                evidence=evidence,
            )

        try:
            current = self._operations.get_network_state()

            if current.mode is not network.mode:
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason=(
                        "network mode verification failed: "
                        f"expected {network.mode.value}, "
                        f"observed {current.mode.value}"
                    ),
                )

            if (
                current.network_access_allowed
                != network.network_access_allowed
            ):
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason=(
                        "network access policy verification failed: "
                        f"expected {network.network_access_allowed}, "
                        f"observed {current.network_access_allowed}"
                    ),
                )

            evidence = (
                EnforcementEvidence.verified(
                    primitive=self.primitive,
                    evidence_type="network_state",
                    observation=(
                        "Network mode and network access policy were "
                        "independently verified."
                    ),
                ),
            )

            return self._result(
                plan=plan,
                state=EnforcementState.VERIFIED,
                success=True,
                reason="network isolation independently verified",
                evidence=evidence,
            )

        except (OSError, ValueError) as exc:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=f"network verification failed: {exc}",
            )

    def evidence(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> tuple[EnforcementEvidence, ...]:
        """Return independently collected network evidence."""
        return self.verify(context, plan).evidence

    def _result(
        self,
        *,
        plan: LinuxEnforcementPlan,
        state: EnforcementState,
        success: bool,
        reason: str,
        evidence: tuple[EnforcementEvidence, ...] = (),
    ) -> EnforcementPrimitiveResult:
        """Construct a result using the authoritative result contract."""
        requirement = self._requirement(plan)
        required = requirement.required if requirement is not None else True

        return EnforcementPrimitiveResult(
            primitive=self.primitive,
            required=required,
            state=state,
            success=success,
            reason=reason,
            evidence=evidence,
        )

    @staticmethod
    def _requirement(
        plan: LinuxEnforcementPlan,
    ) -> EnforcementRequirement | None:
        """Return the authoritative network requirement."""
        return next(
            (
                requirement
                for requirement in plan.requirements
                if requirement.primitive is EnforcementPrimitive.NETWORK
            ),
            None,
        )


__all__ = [
    "FilesystemIsolationAdapter",
    "FilesystemIsolationState",
    "FilesystemOperations",
    "NativeFilesystemOperations",
    "NativeNetworkOperations",
    "NetworkIsolationAdapter",
    "NetworkIsolationState",
    "NetworkOperations",
]
