"""Landlock enforcement adapter and native Linux kernel implementation."""

from __future__ import annotations

import ctypes
import ctypes.util
import errno
import os
import platform
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
    FilesystemPlan,
    LinuxEnforcementPlan,
)
from lyrion.execution.backends.linux.enforcement.landlock_policy import (
    LandlockAbiCapabilities,
    LandlockFilesystemAccess,
    LandlockPolicy,
    LandlockPolicyValidator,
    attest_policy,
    verify_policy_attestation,
)

_LANDLOCK_CREATE_RULESET_VERSION = 1 << 0
_LANDLOCK_RULE_PATH_BENEATH = 1
_LANDLOCK_RESTRICT_SELF_NO_NEW_PRIVS = 1 << 2

_O_PATH = getattr(os, "O_PATH", 0o10000000)
_O_CLOEXEC = getattr(os, "O_CLOEXEC", 0o2000000)

# Linux Landlock syscall numbers for the supported architectures.
_SYSCALLS: dict[str, tuple[int, int, int]] = {
    "x86_64": (444, 445, 446),
    "aarch64": (444, 445, 446),
}


class _LandlockRulesetAttr(ctypes.Structure):
    """Userspace representation of struct landlock_ruleset_attr."""

    _fields_ = [
        ("handled_access_fs", ctypes.c_uint64),
        ("handled_access_net", ctypes.c_uint64),
        ("scoped", ctypes.c_uint64),
    ]


class _LandlockPathBeneathAttr(ctypes.Structure):
    """
    Userspace representation of the Linux Landlock packed ABI structure.

    Linux defines struct landlock_path_beneath_attr as a packed structure:
    u64 allowed_access followed by s32 parent_fd, for a total size of
    exactly 12 bytes.

    Python 3.14 requires the ctypes layout choice to be explicit when
    _pack_ is used. The "ms" layout is used here solely because ctypes
    restricts non-zero _pack_ to that layout; the resulting byte layout
    is explicitly validated against the Linux UAPI ABI.
    """

    _layout_ = "ms"
    _pack_ = 1

    _fields_ = [
        ("allowed_access", ctypes.c_uint64),
        ("parent_fd", ctypes.c_int32),
    ]


@dataclass(frozen=True, slots=True)
class LandlockState:
    """Kernel-observable Landlock state."""

    installed: bool
    abi_version: int | None
    policy_id: str | None
    policy_version: str | None
    filesystem_paths: tuple[str, ...] = ()


class LandlockOperations(Protocol):
    """Operations required by the Landlock adapter."""

    def get_capabilities(self) -> LandlockAbiCapabilities:
        """Return runtime Landlock capabilities."""

    def install_policy(
        self,
        policy: LandlockPolicy,
        filesystem: FilesystemPlan,
    ) -> None:
        """Install and enforce the supplied policy."""

    def get_state(self) -> LandlockState:
        """Return independently observed runtime state."""


class NativeLandlockOperations:
    """
    Native Linux Landlock implementation.

    This class intentionally owns only Landlock kernel operations.
    no_new_privs is a separate enforcement primitive and must already be
    established by the execution boundary before enforcement.
    """

    def __init__(self) -> None:
        library = ctypes.util.find_library("c")
        if not library:
            raise RuntimeError("Unable to locate libc")

        self._libc = ctypes.CDLL(
            library,
            use_errno=True,
        )

        self._libc.syscall.argtypes = [
            ctypes.c_long,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_uint32,
        ]
        self._libc.syscall.restype = ctypes.c_long

        self._architecture = self._normalize_architecture(
            platform.machine()
        )

        if self._architecture not in _SYSCALLS:
            raise RuntimeError(
                "Unsupported architecture for native Landlock backend: "
                f"{platform.machine()}"
            )

        (
            self._create_syscall,
            self._add_rule_syscall,
            self._restrict_syscall,
        ) = _SYSCALLS[self._architecture]

        self._state = LandlockState(
            installed=False,
            abi_version=None,
            policy_id=None,
            policy_version=None,
        )

    @staticmethod
    def _normalize_architecture(machine: str) -> str:
        normalized = machine.lower()

        aliases = {
            "amd64": "x86_64",
            "x86-64": "x86_64",
            "arm64": "aarch64",
        }

        return aliases.get(normalized, normalized)

    def _syscall(
        self,
        number: int,
        arg1: ctypes.c_void_p | int | None,
        arg2: int,
        arg3: int,
    ) -> int:
        result = self._libc.syscall(
            ctypes.c_long(number),
            arg1,
            ctypes.c_size_t(arg2),
            ctypes.c_uint32(arg3),
        )

        if result < 0:
            error = ctypes.get_errno()
            raise OSError(
                error,
                os.strerror(error),
            )

        return int(result)

    def _query_abi(self) -> int:
        result = self._libc.syscall(
            ctypes.c_long(self._create_syscall),
            None,
            ctypes.c_size_t(0),
            ctypes.c_uint32(_LANDLOCK_CREATE_RULESET_VERSION),
        )

        if result < 0:
            error = ctypes.get_errno()
            raise OSError(
                error,
                os.strerror(error),
            )

        return int(result)

    def get_capabilities(self) -> LandlockAbiCapabilities:
        abi = self._query_abi()

        return LandlockAbiCapabilities(
            abi_version=abi,
            filesystem_access=LandlockFilesystemAccess(
                (1 << 16) - 1
            ),
        )

    @staticmethod
    def _require_no_new_privs() -> None:
        status_path = "/proc/self/status"

        try:
            status = open(
                status_path,
                encoding="utf-8",
            )
        except OSError as exc:
            raise RuntimeError(
                "Unable to inspect /proc/self/status for no_new_privs"
            ) from exc

        with status:
            for line in status:
                if line.startswith("NoNewPrivs:"):
                    value = int(line.split(":", 1)[1].strip())
                    if value != 1:
                        raise PermissionError(
                            "Landlock requires existing no_new_privs=1 "
                            "or CAP_SYS_ADMIN; the Landlock adapter does "
                            "not establish no_new_privs itself"
                        )
                    return

        raise RuntimeError(
            "NoNewPrivs field was not present in /proc/self/status"
        )

    @staticmethod
    def _open_path(path: str) -> int:
        return os.open(
            path,
            _O_PATH | _O_CLOEXEC,
        )

    def _create_ruleset(
        self,
        policy: LandlockPolicy,
        abi: int,
    ) -> int:
        validator = LandlockPolicyValidator()

        capabilities = LandlockAbiCapabilities(
            abi_version=abi,
            filesystem_access=LandlockFilesystemAccess(
                (1 << 16) - 1
            ),
        )

        validation = validator.validate(
            policy,
            capabilities,
            required=True,
        )

        if not validation.success:
            raise ValueError(validation.reason)

        attr = _LandlockRulesetAttr(
            handled_access_fs=int(policy.handled_access_fs),
            handled_access_net=0,
            scoped=0,
        )

        return self._syscall(
            self._create_syscall,
            ctypes.cast(
                ctypes.pointer(attr),
                ctypes.c_void_p,
            ),
            ctypes.sizeof(attr),
            0,
        )

    def _add_path_rule(
        self,
        ruleset_fd: int,
        path: str,
        allowed_access: LandlockFilesystemAccess,
    ) -> None:
        parent_fd = self._open_path(path)

        try:
            rule = _LandlockPathBeneathAttr(
                allowed_access=int(allowed_access),
                parent_fd=parent_fd,
            )

            result = self._libc.syscall(
                ctypes.c_long(self._add_rule_syscall),
                ctypes.c_int(ruleset_fd),
                ctypes.c_uint32(_LANDLOCK_RULE_PATH_BENEATH),
                ctypes.cast(
                    ctypes.pointer(rule),
                    ctypes.c_void_p,
                ),
                ctypes.c_uint32(0),
            )

            if result < 0:
                error = ctypes.get_errno()
                raise OSError(
                    error,
                    os.strerror(error),
                )
        finally:
            os.close(parent_fd)

    def install_policy(
        self,
        policy: LandlockPolicy,
        filesystem: FilesystemPlan,
    ) -> None:
        if not filesystem.required:
            raise ValueError(
                "Landlock cannot be installed without a filesystem "
                "enforcement boundary"
            )

        self._require_no_new_privs()

        abi = self._query_abi()

        if abi < policy.minimum_abi:
            raise RuntimeError(
                "Landlock ABI is below policy requirement: "
                f"required {policy.minimum_abi}, observed {abi}"
            )

        ruleset_fd = self._create_ruleset(
            policy,
            abi,
        )

        try:
            # Read-only paths receive only the read rights represented
            # by the policy's default allowance.
            read_access = (
                policy.default_allowed_access_fs
                & policy.handled_access_fs
            )

            for path in filesystem.read_only_paths:
                self._add_path_rule(
                    ruleset_fd,
                    path,
                    read_access,
                )

            # Writable paths receive the policy's handled rights. This is
            # intentionally bounded by handled_access_fs.
            writable_access = policy.handled_access_fs

            for path in filesystem.writable_paths:
                self._add_path_rule(
                    ruleset_fd,
                    path,
                    writable_access,
                )

            self._libc.syscall.argtypes = [
                ctypes.c_long,
                ctypes.c_int,
                ctypes.c_uint32,
            ]

            self._libc.syscall.restype = ctypes.c_long

            result = self._libc.syscall(
                ctypes.c_long(self._restrict_syscall),
                ctypes.c_int(ruleset_fd),
                ctypes.c_uint32(
                    _LANDLOCK_RESTRICT_SELF_NO_NEW_PRIVS
                ),
            )

            if result < 0:
                error = ctypes.get_errno()

                if error == errno.EPERM:
                    raise PermissionError(
                        "Landlock enforcement rejected by kernel; "
                        "no_new_privs prerequisite is not satisfied"
                    )

                raise OSError(
                    error,
                    os.strerror(error),
                )
        finally:
            os.close(ruleset_fd)

        self._state = LandlockState(
            installed=True,
            abi_version=abi,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            filesystem_paths=(
                *filesystem.writable_paths,
                *filesystem.read_only_paths,
            ),
        )

    def get_state(self) -> LandlockState:
        return self._state


class LandlockAdapter(PrimitiveAdapter):
    """Adapter for the Landlock enforcement primitive."""

    def __init__(
        self,
        policy: LandlockPolicy,
        operations: LandlockOperations,
    ) -> None:
        self._policy = policy
        self._operations = operations
        self._attestation = attest_policy(policy)

    @property
    def primitive(self) -> EnforcementPrimitive:
        return EnforcementPrimitive.LANDLOCK

    @staticmethod
    def _plan_requirement(
        plan: LinuxEnforcementPlan,
    ) -> EnforcementRequirement | None:
        for requirement in plan.requirements:
            if requirement.primitive is EnforcementPrimitive.LANDLOCK:
                return requirement
        return None

    def _validate_requirement_consistency(
        self,
        plan: LinuxEnforcementPlan,
    ) -> tuple[bool, str]:
        requirement = self._plan_requirement(plan)

        if requirement is None:
            return False, "Landlock requirement is missing"

        if requirement.required != plan.landlock.required:
            return False, (
                "Landlock requirement is inconsistent with "
                "LandlockPlan.required"
            )

        return True, ""

    def supports(self, plan: LinuxEnforcementPlan) -> bool:
        valid, _ = self._validate_requirement_consistency(plan)

        if not valid:
            return False

        if not plan.landlock.required:
            return True

        try:
            capabilities = self._operations.get_capabilities()
            result = LandlockPolicyValidator().validate(
                self._policy,
                capabilities,
                required=True,
            )
            return result.success
        except (OSError, RuntimeError, ValueError):
            return False

    def validate(
        self,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        required = plan.landlock.required

        valid, reason = self._validate_requirement_consistency(plan)

        if not valid:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=required,
                state=EnforcementState.FAILED,
                success=False,
                reason=reason,
                evidence=(),
            )

        if not required:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=False,
                state=EnforcementState.PLANNED,
                success=True,
                reason="Landlock is not required",
                evidence=(),
            )

        if not plan.filesystem.required:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason=(
                    "Landlock requires a filesystem enforcement boundary"
                ),
                evidence=(),
            )

        try:
            capabilities = self._operations.get_capabilities()

            validation = LandlockPolicyValidator().validate(
                self._policy,
                capabilities,
                required=True,
            )

            if not validation.success:
                return EnforcementPrimitiveResult(
                    primitive=self.primitive,
                    required=True,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason=(
                        "Landlock validation failed: "
                        f"{validation.reason}"
                    ),
                    evidence=(),
                )

            verify_policy_attestation(
                self._policy,
                self._attestation,
            )

        except (OSError, RuntimeError, ValueError) as exc:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason=f"Landlock validation failed: {exc}",
                evidence=(),
            )

        return EnforcementPrimitiveResult(
            primitive=self.primitive,
            required=True,
            state=EnforcementState.SUPPORTED,
            success=True,
            reason="Landlock policy is supported",
            evidence=(),
        )

    def apply(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        del context

        validation = self.validate(plan)

        if not validation.success:
            return validation

        if not plan.landlock.required:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=False,
                state=EnforcementState.APPLIED,
                success=True,
                reason="Landlock was not required",
                evidence=(),
            )

        try:
            self._operations.install_policy(
                self._policy,
                plan.filesystem,
            )
        except (OSError, PermissionError, RuntimeError, ValueError) as exc:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason=f"Landlock application failed: {exc}",
                evidence=(),
            )

        return EnforcementPrimitiveResult(
            primitive=self.primitive,
            required=True,
            state=EnforcementState.APPLIED,
            success=True,
            reason="Landlock policy applied",
            evidence=(),
        )

    def verify(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        del context

        validation = self.validate(plan)

        if not validation.success:
            return validation

        if not plan.landlock.required:
            evidence = EnforcementEvidence.verified(
                primitive=self.primitive,
                evidence_type="landlock_not_required",
                observation="Landlock was not required by the plan",
            )

            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=False,
                state=EnforcementState.VERIFIED,
                success=True,
                reason="Landlock not required",
                evidence=(evidence,),
            )

        state = self._operations.get_state()

        if not state.installed:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason="Landlock ruleset is not installed",
                evidence=(),
            )

        if state.abi_version is None:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason="Landlock ABI state is unavailable",
                evidence=(),
            )

        if state.abi_version < self._policy.minimum_abi:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason=(
                    "Landlock ABI state is below policy requirement: "
                    f"required {self._policy.minimum_abi}, "
                    f"observed {state.abi_version}"
                ),
                evidence=(),
            )

        if state.policy_id != self._policy.policy_id:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason="Landlock policy identity mismatch",
                evidence=(),
            )

        if state.policy_version != self._policy.policy_version:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason="Landlock policy version mismatch",
                evidence=(),
            )

        try:
            verify_policy_attestation(
                self._policy,
                self._attestation,
            )
        except ValueError as exc:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason=f"Landlock attestation verification failed: {exc}",
                evidence=(),
            )

        runtime_evidence = EnforcementEvidence.verified(
            primitive=self.primitive,
            evidence_type="landlock_runtime_state",
            observation=(
                "Landlock kernel state reports an installed ruleset "
                f"with ABI {state.abi_version}"
            ),
        )

        attestation_evidence = EnforcementEvidence.verified(
            primitive=self.primitive,
            evidence_type="landlock_policy_attestation",
            observation=(
                "Application policy attestation matches the configured "
                "Landlock policy"
            ),
        )

        return EnforcementPrimitiveResult(
            primitive=self.primitive,
            required=True,
            state=EnforcementState.VERIFIED,
            success=True,
            reason="Landlock enforcement verified",
            evidence=(
                runtime_evidence,
                attestation_evidence,
            ),
        )

    def evidence(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> tuple[EnforcementEvidence, ...]:
        result = self.verify(context, plan)

        if result.state is not EnforcementState.VERIFIED:
            return ()

        return result.evidence
