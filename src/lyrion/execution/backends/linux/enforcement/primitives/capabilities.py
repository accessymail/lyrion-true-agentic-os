"""Linux capability-reduction enforcement adapter.

The adapter owns only Linux capability reduction.

Security properties:
- capability policy comes from the typed PrivilegePlan;
- reduction is monotonic and cannot add capabilities;
- host operations are isolated behind CapabilityOperations;
- apply() never reports VERIFIED;
- verification independently reads the resulting capability state;
- failures are fail-closed;
- unit tests inject a deterministic operation boundary and never mutate
  the host process.
"""

from __future__ import annotations

import ctypes
import errno
import os
from pathlib import Path
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


class CapabilityState:
    """Immutable snapshot of Linux capability sets."""

    __slots__ = (
        "effective",
        "permitted",
        "inheritable",
        "bounding",
        "ambient",
    )

    def __init__(
        self,
        *,
        effective: frozenset[int],
        permitted: frozenset[int],
        inheritable: frozenset[int],
        bounding: frozenset[int],
        ambient: frozenset[int],
    ) -> None:
        self.effective = effective
        self.permitted = permitted
        self.inheritable = inheritable
        self.bounding = bounding
        self.ambient = ambient


class CapabilityOperations(Protocol):
    """Low-level Linux capability operation boundary."""

    def get_state(self) -> CapabilityState:
        """Return the current thread capability state."""

    def set_capabilities(
        self,
        *,
        effective: frozenset[int],
        permitted: frozenset[int],
        inheritable: frozenset[int],
    ) -> None:
        """Apply reduced effective/permitted/inheritable sets."""

    def drop_bounding(self, capability: int) -> None:
        """Drop one capability from the bounding set."""

    def get_bounding(self, capability: int) -> bool:
        """Return whether a capability remains in the bounding set."""

    def get_ambient(self, capability: int) -> bool:
        """Return whether a capability remains in the ambient set."""

    def clear_ambient(self) -> None:
        """Clear all ambient capabilities for the current process."""


class _CapHeader(ctypes.Structure):
    _fields_ = [
        ("version", ctypes.c_uint32),
        ("pid", ctypes.c_int),
    ]


class _CapData(ctypes.Structure):
    _fields_ = [
        ("effective", ctypes.c_uint32),
        ("permitted", ctypes.c_uint32),
        ("inheritable", ctypes.c_uint32),
    ]


_LINUX_CAPABILITY_VERSION_3 = 0x20080522
_LINUX_CAPABILITY_U32S_3 = 2

_PR_CAPBSET_READ = 23
_PR_CAPBSET_DROP = 24
_PR_CAP_AMBIENT = 47
_PR_CAP_AMBIENT_CLEAR_ALL = 4

_CAPABILITY_STATUS_FILES = {
    "effective": "CapEff",
    "permitted": "CapPrm",
    "inheritable": "CapInh",
    "bounding": "CapBnd",
    "ambient": "CapAmb",
}


class LibcCapabilityOperations:
    """Native Linux capability operations.

    Native mutation is deliberately limited to privilege reduction:
    effective, permitted, and inheritable sets may only be reduced;
    bounding capabilities may only be dropped; ambient capabilities
    are cleared completely.

    No capability-addition operation is exposed.
    """

    def __init__(self) -> None:
        self._libc = ctypes.CDLL(None, use_errno=True)

        self._libc.capget.argtypes = [
            ctypes.POINTER(_CapHeader),
            ctypes.POINTER(_CapData),
        ]
        self._libc.capget.restype = ctypes.c_int

        self._libc.capset.argtypes = [
            ctypes.POINTER(_CapHeader),
            ctypes.POINTER(_CapData),
        ]
        self._libc.capset.restype = ctypes.c_int

        self._libc.prctl.argtypes = [
            ctypes.c_int,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
        ]
        self._libc.prctl.restype = ctypes.c_int

    @staticmethod
    def _raise_errno(operation: str) -> None:
        error_number = ctypes.get_errno()
        if error_number == 0:
            error_number = errno.EIO

        error_message = os.strerror(error_number)

        raise OSError(
            error_number,
            f"{operation} failed: {error_message}",
        )

    @staticmethod
    def _words_to_set(
        low: int,
        high: int,
    ) -> frozenset[int]:
        capabilities: set[int] = set()

        for word_index, word in enumerate((low, high)):
            value = int(word)

            for bit in range(32):
                if value & (1 << bit):
                    capabilities.add((word_index * 32) + bit)

        return frozenset(capabilities)

    @staticmethod
    def _read_status_capability(name: str) -> frozenset[int]:
        target = _CAPABILITY_STATUS_FILES[name]

        try:
            status = Path("/proc/self/status").read_text(
                encoding="ascii",
            )
        except OSError as exc:
            raise OSError(
                exc.errno or errno.EIO,
                f"unable to read /proc/self/status: {exc}",
            ) from exc

        for line in status.splitlines():
            if not line.startswith(f"{target}:"):
                continue

            _, value = line.split(":", 1)
            raw = value.strip()

            try:
                mask = int(raw, 16)
            except ValueError as exc:
                raise OSError(
                    errno.EINVAL,
                    f"invalid {target} capability mask",
                ) from exc

            capabilities: set[int] = set()

            bit = 0
            while mask:
                if mask & 1:
                    capabilities.add(bit)
                mask >>= 1
                bit += 1

            return frozenset(capabilities)

        raise OSError(
            errno.ENOENT,
            f"{target} capability field not found in /proc/self/status",
        )

    def _capget(self) -> tuple[frozenset[int], frozenset[int], frozenset[int]]:
        header = _CapHeader(
            version=_LINUX_CAPABILITY_VERSION_3,
            pid=0,
        )

        data = (_CapData * _LINUX_CAPABILITY_U32S_3)()

        result = self._libc.capget(
            ctypes.byref(header),
            data,
        )

        if result != 0:
            self._raise_errno("capget")

        return (
            self._words_to_set(
                data[0].effective,
                data[1].effective,
            ),
            self._words_to_set(
                data[0].permitted,
                data[1].permitted,
            ),
            self._words_to_set(
                data[0].inheritable,
                data[1].inheritable,
            ),
        )

    def get_state(self) -> CapabilityState:
        effective, permitted, inheritable = self._capget()

        return CapabilityState(
            effective=effective,
            permitted=permitted,
            inheritable=inheritable,
            bounding=self._read_status_capability("bounding"),
            ambient=self._read_status_capability("ambient"),
        )

    @staticmethod
    def _validate_capability_number(capability: int) -> None:
        if capability < 0:
            raise ValueError("capability number must be non-negative")

    def set_capabilities(
        self,
        *,
        effective: frozenset[int],
        permitted: frozenset[int],
        inheritable: frozenset[int],
    ) -> None:
        """Set reduced capability sets using Linux capset(2).

        The caller is responsible for enforcing monotonic reduction before
        invoking this operation.
        """
        for capability in effective:
            self._validate_capability_number(capability)

        for capability in permitted:
            self._validate_capability_number(capability)

        for capability in inheritable:
            self._validate_capability_number(capability)

        current = self.get_state()

        if not effective.issubset(current.effective):
            raise ValueError(
                "effective capability operation would add privilege"
            )

        if not permitted.issubset(current.permitted):
            raise ValueError(
                "permitted capability operation would add privilege"
            )

        if not inheritable.issubset(current.inheritable):
            raise ValueError(
                "inheritable capability operation would add privilege"
            )

        effective_mask = 0
        permitted_mask = 0
        inheritable_mask = 0

        for capability in effective:
            if capability < 0:
                raise ValueError("capability number must be non-negative")
            effective_mask |= 1 << capability

        for capability in permitted:
            if capability < 0:
                raise ValueError("capability number must be non-negative")
            permitted_mask |= 1 << capability

        for capability in inheritable:
            if capability < 0:
                raise ValueError("capability number must be non-negative")
            inheritable_mask |= 1 << capability

        data = (_CapData * _LINUX_CAPABILITY_U32S_3)()

        data[0].effective = effective_mask & 0xFFFFFFFF
        data[1].effective = (
            (effective_mask >> 32) & 0xFFFFFFFF
        )

        data[0].permitted = permitted_mask & 0xFFFFFFFF
        data[1].permitted = (
            (permitted_mask >> 32) & 0xFFFFFFFF
        )

        data[0].inheritable = inheritable_mask & 0xFFFFFFFF
        data[1].inheritable = (
            (inheritable_mask >> 32) & 0xFFFFFFFF
        )

        header = _CapHeader(
            version=_LINUX_CAPABILITY_VERSION_3,
            pid=0,
        )

        result = self._libc.capset(
            ctypes.byref(header),
            data,
        )

        if result != 0:
            self._raise_errno("capset")

    def drop_bounding(self, capability: int) -> None:
        if capability < 0:
            raise ValueError("capability number must be non-negative")

        result = self._libc.prctl(
            _PR_CAPBSET_DROP,
            capability,
            0,
            0,
            0,
        )

        if result != 0:
            self._raise_errno(
                f"prctl(PR_CAPBSET_DROP, {capability})"
            )

    def get_bounding(self, capability: int) -> bool:
        if capability < 0:
            raise ValueError("capability number must be non-negative")

        result = self._libc.prctl(
            _PR_CAPBSET_READ,
            capability,
            0,
            0,
            0,
        )

        result = int(result)

        if result < 0:
            self._raise_errno(
                f"prctl(PR_CAPBSET_READ, {capability})"
            )

        return result == 1

    def get_ambient(self, capability: int) -> bool:
        if capability < 0:
            raise ValueError("capability number must be non-negative")

        result = self._libc.prctl(
            _PR_CAP_AMBIENT,
            1,
            capability,
            0,
            0,
        )

        result = int(result)

        if result < 0:
            self._raise_errno(
                f"prctl(PR_CAP_AMBIENT_IS_SET, {capability})"
            )

        return result == 1

    def clear_ambient(self) -> None:
        result = self._libc.prctl(
            _PR_CAP_AMBIENT,
            _PR_CAP_AMBIENT_CLEAR_ALL,
            0,
            0,
            0,
        )

        if result != 0:
            self._raise_errno(
                "prctl(PR_CAP_AMBIENT_CLEAR_ALL)"
            )


class CapabilityAdapter(PrimitiveAdapter):
    """Capability-reduction adapter implementing the C2 lifecycle."""

    primitive = EnforcementPrimitive.CAPABILITIES

    def __init__(self, operations: CapabilityOperations) -> None:
        self._operations = operations

    def supports(self, plan: LinuxEnforcementPlan) -> bool:
        """Return whether the plan contains a capability requirement."""
        return self._requirement(plan) is not None

    def validate(
        self,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Validate capability requirements without mutating the host."""
        requirement = self._requirement(plan)

        if requirement is None:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason="capability requirement is absent",
            )

        if not plan.privilege.capability_reduction_required:
            if requirement.required:
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason=(
                        "capability requirement is mandatory but the "
                        "privilege plan disables capability reduction"
                    ),
                )

            return self._result(
                plan=plan,
                state=EnforcementState.PLANNED,
                success=True,
                reason="capability reduction is not required",
            )

        if not requirement.required:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=(
                    "privilege plan requires capability reduction but the "
                    "capability requirement is not mandatory"
                ),
            )

        return self._result(
            plan=plan,
            state=EnforcementState.SUPPORTED,
            success=True,
            reason="capability reduction requirement is structurally valid",
        )

    def apply(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Apply only a capability reduction; never claim verification."""
        del context

        validation = self.validate(plan)
        if validation.state is EnforcementState.FAILED:
            return validation

        if not plan.privilege.capability_reduction_required:
            return self._result(
                plan=plan,
                state=EnforcementState.APPLIED,
                success=True,
                reason="capability reduction is not required",
            )

        try:
            current = self._operations.get_state()

            target_effective: frozenset[int] = frozenset()
            target_permitted: frozenset[int] = frozenset()
            target_inheritable: frozenset[int] = frozenset()

            if not target_effective.issubset(current.effective):
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason="effective capability reduction would gain privilege",
                )

            if not target_permitted.issubset(current.permitted):
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason="permitted capability reduction would gain privilege",
                )

            if not target_inheritable.issubset(current.inheritable):
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason=(
                        "inheritable capability reduction would gain privilege"
                    ),
                )

            # Bounding-set reduction must occur before dropping the
            # effective/permitted capability authority required by the
            # kernel for PR_CAPBSET_DROP.
            #
            # The operation is strictly monotonic: every capability currently
            # present in the bounding set is explicitly removed.
            for capability in sorted(current.bounding):
                self._operations.drop_bounding(capability)

            # Ambient capabilities must not survive into the workload.
            self._operations.clear_ambient()

            # Final privilege reduction occurs only after the bounding and
            # ambient transitions have completed successfully.
            self._operations.set_capabilities(
                effective=target_effective,
                permitted=target_permitted,
                inheritable=target_inheritable,
            )

            return self._result(
                plan=plan,
                state=EnforcementState.APPLIED,
                success=True,
                reason=(
                    "effective, permitted, inheritable, bounding, and "
                    "ambient capability sets reduced; independent "
                    "verification is required"
                ),
            )

        except (OSError, ValueError) as exc:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=f"capability reduction failed: {exc}",
            )

    def verify(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Independently verify the capability state."""
        del context

        validation = self.validate(plan)
        if validation.state is EnforcementState.FAILED:
            return validation

        if not plan.privilege.capability_reduction_required:
            evidence = (
                EnforcementEvidence.verified(
                    primitive=self.primitive,
                    evidence_type="capability_policy",
                    observation="Capability reduction is not required by plan.",
                ),
            )
            return self._result(
                plan=plan,
                state=EnforcementState.VERIFIED,
                success=True,
                reason="capability reduction is not required",
                evidence=evidence,
            )

        try:
            current = self._operations.get_state()

            if current.effective:
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason="effective capability verification failed",
                )

            if current.permitted:
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason="permitted capability verification failed",
                )

            if current.inheritable:
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason="inheritable capability verification failed",
                )

            if current.bounding:
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason="bounding capability verification failed",
                )

            if current.ambient:
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason="ambient capability verification failed",
                )

            evidence = (
                EnforcementEvidence.verified(
                    primitive=self.primitive,
                    evidence_type="capability_state",
                    observation=(
                        "Effective, permitted, inheritable, bounding, and "
                        "ambient capability sets were independently "
                        "observed empty."
                    ),
                ),
            )

            return self._result(
                plan=plan,
                state=EnforcementState.VERIFIED,
                success=True,
                reason="capability reduction independently verified",
                evidence=evidence,
            )

        except (OSError, ValueError) as exc:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=f"capability verification failed: {exc}",
            )

    def evidence(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> tuple[EnforcementEvidence, ...]:
        """Return independently collected capability evidence."""
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
            state=state,
            required=required,
            success=success,
            reason=reason,
            evidence=evidence,
        )

    @staticmethod
    def _requirement(
        plan: LinuxEnforcementPlan,
    ) -> EnforcementRequirement | None:
        """Return the authoritative capability requirement."""
        return next(
            (
                requirement
                for requirement in plan.requirements
                if requirement.primitive is EnforcementPrimitive.CAPABILITIES
            ),
            None,
        )


__all__ = [
    "CapabilityAdapter",
    "CapabilityOperations",
    "CapabilityState",
    "LibcCapabilityOperations",
]
