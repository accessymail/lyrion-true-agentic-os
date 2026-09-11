"""NoNewPrivs Linux enforcement adapter and kernel-operation boundary."""

from __future__ import annotations

import ctypes
import errno
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

PR_SET_NO_NEW_PRIVS = 38
PR_GET_NO_NEW_PRIVS = 39


class NoNewPrivsOperations(Protocol):
    """Low-level boundary for Linux no_new_privs operations."""

    def set_no_new_privs(self) -> None:
        """Request no_new_privs for the current execution context."""

    def get_no_new_privs(self) -> bool:
        """Read the current kernel no_new_privs state."""


class LibcNoNewPrivsOperations:
    """Native Linux implementation backed by libc.prctl."""

    def __init__(self) -> None:
        self._libc = ctypes.CDLL(None, use_errno=True)

        if not hasattr(self._libc, "prctl"):
            raise RuntimeError("libc.prctl is unavailable")

        self._prctl = self._libc.prctl
        self._prctl.argtypes = [
            ctypes.c_int,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
        ]
        self._prctl.restype = ctypes.c_int

    def set_no_new_privs(self) -> None:
        """Set PR_SET_NO_NEW_PRIVS and fail closed on failure."""
        result = self._prctl(
            PR_SET_NO_NEW_PRIVS,
            1,
            0,
            0,
            0,
        )

        if result != 0:
            error_number = ctypes.get_errno()
            message = errno.errorcode.get(
                error_number,
                f"errno={error_number}",
            )
            raise OSError(
                error_number,
                f"PR_SET_NO_NEW_PRIVS failed: {message}",
            )

    def get_no_new_privs(self) -> bool:
        """Read PR_GET_NO_NEW_PRIVS and fail closed on failure."""
        result = self._prctl(
            PR_GET_NO_NEW_PRIVS,
            0,
            0,
            0,
            0,
        )

        if result < 0:
            error_number = ctypes.get_errno()
            message = errno.errorcode.get(
                error_number,
                f"errno={error_number}",
            )
            raise OSError(
                error_number,
                f"PR_GET_NO_NEW_PRIVS failed: {message}",
            )

        verified: bool = result == 1
        return verified


class NoNewPrivsAdapter(PrimitiveAdapter):
    """LYRION adapter for Linux no_new_privs enforcement."""

    @property
    def primitive(self) -> EnforcementPrimitive:
        """Return the primitive owned by this adapter."""
        return EnforcementPrimitive.NO_NEW_PRIVS

    def __init__(self, operations: NoNewPrivsOperations) -> None:
        self._operations = operations

    def supports(self, plan: LinuxEnforcementPlan) -> bool:
        """Return whether this plan requires no_new_privs."""
        requirement = self._requirement(plan)
        return requirement is not None and requirement.required

    def validate(
        self,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Validate the plan without changing host state."""
        requirement = self._requirement(plan)

        if requirement is None:
            return self._failed(
                required=True,
                reason="NoNewPrivs requirement is missing from the plan.",
            )

        if not requirement.required:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=False,
                state=EnforcementState.SUPPORTED,
                success=True,
                reason="NoNewPrivs is not required by this plan.",
            )

        if requirement.state is EnforcementState.FAILED:
            return self._failed(
                required=True,
                reason=requirement.reason,
            )

        return EnforcementPrimitiveResult(
            primitive=self.primitive,
            required=True,
            state=EnforcementState.SUPPORTED,
            success=True,
            reason="NoNewPrivs requirement is structurally valid.",
        )

    def apply(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Apply no_new_privs without claiming verification."""
        del context

        validation = self.validate(plan)

        if not validation.success or not validation.required:
            return validation

        try:
            self._operations.set_no_new_privs()
        except OSError as exc:
            return self._failed(
                required=True,
                reason=f"Unable to apply no_new_privs: {exc}",
            )
        except Exception as exc:
            return self._failed(
                required=True,
                reason=f"Unexpected no_new_privs application failure: {exc}",
            )

        return EnforcementPrimitiveResult(
            primitive=self.primitive,
            required=True,
            state=EnforcementState.APPLIED,
            success=True,
            reason=(
                "PR_SET_NO_NEW_PRIVS completed; "
                "independent verification is required."
            ),
        )

    def verify(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Independently verify the kernel no_new_privs state."""
        del context

        validation = self.validate(plan)

        if not validation.success or not validation.required:
            return validation

        try:
            active = self._operations.get_no_new_privs()
        except OSError as exc:
            return self._failed(
                required=True,
                reason=f"Unable to verify no_new_privs: {exc}",
            )
        except Exception as exc:
            return self._failed(
                required=True,
                reason=(
                    "Unexpected no_new_privs verification failure: "
                    f"{exc}"
                ),
            )

        if not active:
            return self._failed(
                required=True,
                reason="Kernel verification reports no_new_privs=0.",
            )

        evidence = EnforcementEvidence.verified(
            primitive=self.primitive,
            evidence_type="linux_prctl_state",
            observation="PR_GET_NO_NEW_PRIVS returned 1.",
        )

        return EnforcementPrimitiveResult(
            primitive=self.primitive,
            required=True,
            state=EnforcementState.VERIFIED,
            success=True,
            reason="Kernel no_new_privs state independently verified.",
            evidence=(evidence,),
        )

    def evidence(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> tuple[EnforcementEvidence, ...]:
        """Return evidence only following positive verification."""
        result = self.verify(context, plan)

        if result.state is not EnforcementState.VERIFIED:
            return ()

        return result.evidence

    def _requirement(
        self,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementRequirement | None:
        for requirement in plan.requirements:
            if requirement.primitive is self.primitive:
                return requirement
        return None

    def _failed(
        self,
        *,
        required: bool,
        reason: str,
    ) -> EnforcementPrimitiveResult:
        return EnforcementPrimitiveResult(
            primitive=self.primitive,
            required=required,
            state=EnforcementState.FAILED,
            success=False,
            reason=reason,
        )


__all__ = [
    "LibcNoNewPrivsOperations",
    "NoNewPrivsAdapter",
    "NoNewPrivsOperations",
    "PR_GET_NO_NEW_PRIVS",
    "PR_SET_NO_NEW_PRIVS",
]
