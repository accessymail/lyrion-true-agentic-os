"""Linux cgroup v2 resource-enforcement adapter.

The adapter owns only cgroup-v2 resource-control enforcement.

Security properties:
- resource requirements come exclusively from the typed CgroupPlan;
- host operations are isolated behind CgroupV2Operations;
- apply() never reports VERIFIED;
- verification independently observes configured limits;
- required-control failures are fail-closed;
- unit tests use an injected deterministic operation boundary;
- no root/init cgroup mutation is performed by this implementation.
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


@dataclass(frozen=True, slots=True)
class CgroupV2State:
    """Observed cgroup-v2 resource state."""

    controllers: frozenset[str]
    memory_max_bytes: int | None
    cpu_max: tuple[int | None, int] | None


class CgroupV2Operations(Protocol):
    """Low-level cgroup-v2 operation boundary."""

    def get_state(self) -> CgroupV2State:
        """Return independently observed cgroup state."""

    def create_execution_cgroup(self, execution_id: str) -> None:
        """Create the dedicated execution cgroup."""

    def configure_memory_max(self, memory_max_bytes: int) -> None:
        """Configure the hard memory limit."""

    def configure_cpu_max(self, quota_usec: int, period_usec: int) -> None:
        """Configure CPU bandwidth for the execution cgroup."""


class NativeCgroupV2Operations:
    """Native-operation placeholder for the future Linux supervisor.

    Actual cgroup mutation must occur against a dedicated execution cgroup,
    never against the LYRION controller/root cgroup.
    """

    def get_state(self) -> CgroupV2State:
        raise OSError(
            "native cgroup operations require the Linux process boundary"
        )

    def create_execution_cgroup(self, execution_id: str) -> None:
        del execution_id
        raise OSError(
            "native cgroup operations require the Linux process boundary"
        )

    def configure_memory_max(self, memory_max_bytes: int) -> None:
        del memory_max_bytes
        raise OSError(
            "native cgroup operations require the Linux process boundary"
        )

    def configure_cpu_max(self, quota_usec: int, period_usec: int) -> None:
        del quota_usec, period_usec
        raise OSError(
            "native cgroup operations require the Linux process boundary"
        )


class CgroupV2Adapter(PrimitiveAdapter):
    """cgroup-v2 resource-enforcement adapter."""

    primitive = EnforcementPrimitive.CGROUPS_V2

    def __init__(self, operations: CgroupV2Operations) -> None:
        self._operations = operations

    def supports(self, plan: LinuxEnforcementPlan) -> bool:
        """Return whether the plan contains a cgroup-v2 requirement."""
        return self._requirement(plan) is not None

    def validate(
        self,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Validate cgroup requirements without changing host state."""
        requirement = self._requirement(plan)

        if requirement is None:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason="cgroup v2 requirement is absent",
            )

        cgroups = plan.cgroups

        if requirement.required != cgroups.required:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=(
                    "cgroup requirement and cgroup plan have "
                    "inconsistent required state"
                ),
            )

        if not cgroups.required:
            return self._result(
                plan=plan,
                state=EnforcementState.PLANNED,
                success=True,
                reason="cgroup v2 enforcement is not required",
            )

        if cgroups.max_memory_mb <= 0:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason="maximum memory must be positive",
            )

        if cgroups.max_runtime_seconds <= 0:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason="maximum runtime must be positive",
            )

        if cgroups.max_cpu_seconds <= 0:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason="maximum CPU seconds must be positive",
            )

        return self._result(
            plan=plan,
            state=EnforcementState.SUPPORTED,
            success=True,
            reason="cgroup v2 resource requirements are structurally valid",
        )

    def apply(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Apply cgroup resource controls; never claim verification."""
        validation = self.validate(plan)

        if validation.state is EnforcementState.FAILED:
            return validation

        cgroups = plan.cgroups

        if not cgroups.required:
            return self._result(
                plan=plan,
                state=EnforcementState.APPLIED,
                success=True,
                reason="cgroup v2 enforcement is not required",
            )

        memory_max_bytes = cgroups.max_memory_mb * 1024 * 1024

        # CPU-seconds is deliberately NOT converted into cpu.max here.
        # cpu.max is a bandwidth control, while max_cpu_seconds is an
        # execution CPU-time budget. The dedicated supervisor/lifecycle
        # layer must enforce the latter.
        try:
            self._operations.create_execution_cgroup(context.execution_id)
            self._operations.configure_memory_max(memory_max_bytes)

            return self._result(
                plan=plan,
                state=EnforcementState.APPLIED,
                success=True,
                reason=(
                    "execution cgroup created and memory limit applied; "
                    "CPU-time and runtime budgets require independent "
                    "execution-lifecycle enforcement"
                ),
            )
        except (OSError, ValueError) as exc:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=f"cgroup v2 enforcement failed: {exc}",
            )

    def verify(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Independently verify cgroup-v2 resource state."""
        del context

        validation = self.validate(plan)

        if validation.state is EnforcementState.FAILED:
            return validation

        cgroups = plan.cgroups

        if not cgroups.required:
            evidence = (
                EnforcementEvidence.verified(
                    primitive=self.primitive,
                    evidence_type="cgroup_policy",
                    observation="cgroup v2 enforcement is not required",
                ),
            )
            return self._result(
                plan=plan,
                state=EnforcementState.VERIFIED,
                success=True,
                reason="cgroup v2 enforcement is not required",
                evidence=evidence,
            )

        try:
            state = self._operations.get_state()

            required_controllers = {"memory"}
            missing = required_controllers - state.controllers

            if missing:
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason=(
                        "required cgroup controllers are unavailable: "
                        + ", ".join(sorted(missing))
                    ),
                )

            expected_memory = cgroups.max_memory_mb * 1024 * 1024

            if state.memory_max_bytes != expected_memory:
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason=(
                        "memory.max verification failed: "
                        f"expected {expected_memory}, "
                        f"observed {state.memory_max_bytes}"
                    ),
                )

            evidence = (
                EnforcementEvidence.verified(
                    primitive=self.primitive,
                    evidence_type="cgroup_state",
                    observation=(
                        "Required cgroup v2 controller availability and "
                        "memory.max were independently verified."
                    ),
                ),
            )

            return self._result(
                plan=plan,
                state=EnforcementState.VERIFIED,
                success=True,
                reason="cgroup v2 resource enforcement independently verified",
                evidence=evidence,
            )

        except (OSError, ValueError) as exc:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=f"cgroup v2 verification failed: {exc}",
            )

    def evidence(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> tuple[EnforcementEvidence, ...]:
        """Return independently collected cgroup evidence."""
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
        """Return the authoritative cgroup-v2 requirement."""
        return next(
            (
                requirement
                for requirement in plan.requirements
                if requirement.primitive is EnforcementPrimitive.CGROUPS_V2
            ),
            None,
        )


__all__ = [
    "CgroupV2Adapter",
    "CgroupV2Operations",
    "CgroupV2State",
    "NativeCgroupV2Operations",
]
