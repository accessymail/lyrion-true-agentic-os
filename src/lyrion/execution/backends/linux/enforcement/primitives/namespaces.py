"""Linux namespace-isolation enforcement adapter.

The adapter owns only namespace isolation.

Security properties:
- namespace requirements come exclusively from the typed NamespacePlan;
- host operations are isolated behind NamespaceOperations;
- apply() never reports VERIFIED;
- verification independently observes namespace state;
- required-control failures are fail-closed;
- unit tests use an injected deterministic operation boundary;
- no namespace mutation is performed by the unit-test implementation.
"""

from __future__ import annotations

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


class NamespaceState:
    """Immutable snapshot of relevant namespace isolation state."""

    __slots__ = (
        "process_isolated",
        "mount_isolated",
        "network_isolated",
    )

    def __init__(
        self,
        *,
        process_isolated: bool,
        mount_isolated: bool,
        network_isolated: bool,
    ) -> None:
        self.process_isolated = process_isolated
        self.mount_isolated = mount_isolated
        self.network_isolated = network_isolated


class NamespaceOperations(Protocol):
    """Low-level Linux namespace operation boundary."""

    def get_state(self) -> NamespaceState:
        """Return the current namespace-isolation state."""

    def isolate_process(self) -> None:
        """Create or enter the required process namespace boundary."""

    def isolate_mount(self) -> None:
        """Create or enter the required mount namespace boundary."""

    def isolate_network(self) -> None:
        """Create or enter the required network namespace boundary."""


class NativeNamespaceOperations:
    """Native-operation placeholder for the future process boundary.

    Actual namespace mutation is intentionally unavailable at C2.2-C3.
    Namespace creation must occur inside the dedicated Linux child-process
    supervisor rather than against the LYRION controller process.
    """

    def get_state(self) -> NamespaceState:
        raise OSError(
            "native namespace operations require the Linux process boundary"
        )

    def isolate_process(self) -> None:
        raise OSError(
            "native namespace operations require the Linux process boundary"
        )

    def isolate_mount(self) -> None:
        raise OSError(
            "native namespace operations require the Linux process boundary"
        )

    def isolate_network(self) -> None:
        raise OSError(
            "native namespace operations require the Linux process boundary"
        )


class NamespaceAdapter(PrimitiveAdapter):
    """Namespace-isolation adapter implementing the C2 lifecycle."""

    primitive = EnforcementPrimitive.NAMESPACES

    def __init__(self, operations: NamespaceOperations) -> None:
        self._operations = operations

    def supports(self, plan: LinuxEnforcementPlan) -> bool:
        """Return whether the plan contains a namespace requirement."""
        return self._requirement(plan) is not None

    def validate(
        self,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Validate namespace requirements without changing host state."""
        requirement = self._requirement(plan)

        if requirement is None:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason="namespace requirement is absent",
            )

        namespace_plan = plan.namespaces

        if requirement.required != namespace_plan.required:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=(
                    "namespace requirement and namespace plan have "
                    "inconsistent required state"
                ),
            )

        if not namespace_plan.required:
            return self._result(
                plan=plan,
                state=EnforcementState.PLANNED,
                success=True,
                reason="namespace isolation is not required",
            )

        if not (
            namespace_plan.process_isolation
            or namespace_plan.mount_isolation
            or namespace_plan.network_isolation
        ):
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=(
                    "namespace enforcement is required but no namespace "
                    "isolation control is enabled"
                ),
            )

        return self._result(
            plan=plan,
            state=EnforcementState.SUPPORTED,
            success=True,
            reason="namespace isolation requirement is structurally valid",
        )

    def apply(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Apply requested namespace boundaries; never claim verification."""
        del context

        validation = self.validate(plan)

        if validation.state is EnforcementState.FAILED:
            return validation

        namespace_plan = plan.namespaces

        if not namespace_plan.required:
            return self._result(
                plan=plan,
                state=EnforcementState.APPLIED,
                success=True,
                reason="namespace isolation is not required",
            )

        try:
            if namespace_plan.process_isolation:
                self._operations.isolate_process()

            if namespace_plan.mount_isolation:
                self._operations.isolate_mount()

            if namespace_plan.network_isolation:
                self._operations.isolate_network()

            return self._result(
                plan=plan,
                state=EnforcementState.APPLIED,
                success=True,
                reason=(
                    "required namespace boundaries applied; independent "
                    "verification is required"
                ),
            )

        except (OSError, ValueError) as exc:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=f"namespace isolation failed: {exc}",
            )

    def verify(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Independently verify namespace isolation state."""
        del context

        validation = self.validate(plan)

        if validation.state is EnforcementState.FAILED:
            return validation

        namespace_plan = plan.namespaces

        if not namespace_plan.required:
            evidence = (
                EnforcementEvidence.verified(
                    primitive=self.primitive,
                    evidence_type="namespace_policy",
                    observation=(
                        "Namespace isolation is not required by the plan."
                    ),
                ),
            )
            return self._result(
                plan=plan,
                state=EnforcementState.VERIFIED,
                success=True,
                reason="namespace isolation is not required",
                evidence=evidence,
            )

        try:
            current = self._operations.get_state()

            if (
                namespace_plan.process_isolation
                and not current.process_isolated
            ):
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason="process namespace isolation verification failed",
                )

            if namespace_plan.mount_isolation and not current.mount_isolated:
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason="mount namespace isolation verification failed",
                )

            if (
                namespace_plan.network_isolation
                and not current.network_isolated
            ):
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason="network namespace isolation verification failed",
                )

            evidence = (
                EnforcementEvidence.verified(
                    primitive=self.primitive,
                    evidence_type="namespace_state",
                    observation=(
                        "Required process, mount, and network namespace "
                        "isolation states were independently observed."
                    ),
                ),
            )

            return self._result(
                plan=plan,
                state=EnforcementState.VERIFIED,
                success=True,
                reason="namespace isolation independently verified",
                evidence=evidence,
            )

        except (OSError, ValueError) as exc:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=f"namespace verification failed: {exc}",
            )

    def evidence(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> tuple[EnforcementEvidence, ...]:
        """Return independently collected namespace evidence."""
        result = self.verify(context, plan)
        return result.evidence

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
        """Return the authoritative namespace requirement."""
        return next(
            (
                requirement
                for requirement in plan.requirements
                if requirement.primitive is EnforcementPrimitive.NAMESPACES
            ),
            None,
        )


__all__ = [
    "NamespaceAdapter",
    "NamespaceOperations",
    "NamespaceState",
    "NativeNamespaceOperations",
]
