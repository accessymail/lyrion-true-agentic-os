"""Linux seccomp enforcement adapter.

C2.2-C6-R2 owns the Seccomp primitive adapter boundary.

Security properties:
- the enforcement plan remains authoritative for whether Seccomp is required;
- the executable syscall policy is supplied explicitly and validated through
  the C2.2-C6-R1 policy validator;
- apply() never reports VERIFIED;
- verification is independent from application;
- required-control failures are fail-closed;
- native kernel mutation is delegated to an injected operation boundary;
- the native operation boundary remains unavailable until C2.2-C6-R3;
- no authorization, execution-policy, or sandbox decision is performed here.
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
from lyrion.execution.backends.linux.enforcement.primitives.no_new_privs import (
    LibcNoNewPrivsOperations,
)
from lyrion.execution.backends.linux.enforcement.seccomp_attestation import (
    SeccompPolicyAttestation,
    attest_policy,
    verify_policy_attestation,
)
from lyrion.execution.backends.linux.enforcement.seccomp_policy import (
    SeccompDefaultAction,
    SeccompPolicy,
    SeccompPolicyValidator,
)


@dataclass(frozen=True, slots=True)
class SeccompState:
    """Kernel-observable Seccomp state.

    Linux exposes filter mode/count and architecture-related process state,
    but does not expose LYRION policy IDs, versions, or policy digests.
    Those application-level claims are verified separately through
    SeccompPolicyAttestation.
    """

    architecture: str | None
    installed: bool
    seccomp_mode: int
    filter_count: int


class SeccompOperations(Protocol):
    """Low-level Seccomp operation boundary.

    C2.2-C6-R2 defines this interface only. Native implementation belongs
    to C2.2-C6-R3.
    """

    def install_policy(self, policy: SeccompPolicy) -> None:
        """Install the supplied policy in the execution process boundary."""

    def get_state(self) -> SeccompState:
        """Independently observe Seccomp enforcement state."""



class NativeSeccompOperations:
    """Native Linux seccomp implementation backed by libseccomp.

    This boundary deliberately requires no_new_privs to have already been
    established by the dedicated LYRION privilege adapter.  libseccomp's
    automatic no_new_privs behavior is disabled so that this operation cannot
    silently establish a security prerequisite owned by another primitive.
    """

    _SCMP_ACT_KILL_PROCESS = 0x80000000
    _SCMP_ACT_ERRNO_BASE = 0x00050000
    _SCMP_ACT_ALLOW = 0x7FFF0000

    # libseccomp filter attribute.
    _SCMP_FLTATR_CTL_NNP = 2

    _ARCHITECTURES = {
        "x86_64": "x86_64",
        "aarch64": "aarch64",
        "arm": "arm",
        "i386": "x86",
        "riscv64": "riscv64",
    }

    def __init__(self) -> None:
        import ctypes.util

        library = ctypes.util.find_library("seccomp")
        if library is None:
            raise RuntimeError("libseccomp is unavailable")

        self._lib = ctypes.CDLL(library, use_errno=True)

        self._configure_api()

    def _configure_api(self) -> None:
        """Configure the subset of libseccomp used by this adapter."""
        import ctypes

        self._lib.seccomp_init.argtypes = [ctypes.c_uint32]
        self._lib.seccomp_init.restype = ctypes.c_void_p

        self._lib.seccomp_release.argtypes = [ctypes.c_void_p]
        self._lib.seccomp_release.restype = None

        self._lib.seccomp_rule_add.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        self._lib.seccomp_rule_add.restype = ctypes.c_int

        self._lib.seccomp_load.argtypes = [ctypes.c_void_p]
        self._lib.seccomp_load.restype = ctypes.c_int

        self._lib.seccomp_attr_set.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_uint32,
        ]
        self._lib.seccomp_attr_set.restype = ctypes.c_int

        self._lib.seccomp_arch_native.argtypes = []
        self._lib.seccomp_arch_native.restype = ctypes.c_uint32

        self._lib.seccomp_arch_resolve_name.argtypes = [ctypes.c_char_p]
        self._lib.seccomp_arch_resolve_name.restype = ctypes.c_uint32

        self._lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
        self._lib.seccomp_syscall_resolve_name.restype = ctypes.c_int

    def _raise_libseccomp(self, operation: str, rc: int) -> None:
        """Convert a libseccomp negative result into an OSError."""
        import errno

        error_number = -rc if rc < 0 else rc
        message = errno.errorcode.get(
            error_number,
            f"libseccomp_rc={rc}",
        )
        raise OSError(
            error_number,
            f"{operation} failed: {message}",
        )

    def _native_architecture(self) -> str:
        """Return the normalized native architecture name."""
        import platform

        machine = platform.machine().lower()

        try:
            return self._ARCHITECTURES[machine]
        except KeyError as exc:
            raise OSError(
                0,
                f"Unsupported native architecture: {machine}",
            ) from exc

    def _validate_architecture(self, policy: SeccompPolicy) -> None:
        """Reject policies targeting a non-native architecture."""
        expected = self._ARCHITECTURES.get(policy.architecture.value)

        if expected is None:
            raise OSError(
                0,
                f"Unsupported Seccomp policy architecture: "
                f"{policy.architecture.value}",
            )

        native = self._native_architecture()

        if expected != native:
            raise OSError(
                0,
                "Seccomp policy architecture does not match the native "
                f"execution architecture: policy={expected}, "
                f"native={native}",
            )

        native_token = self._lib.seccomp_arch_native()
        policy_token = self._lib.seccomp_arch_resolve_name(
            expected.encode("ascii"),
        )

        if native_token == 0 or policy_token == 0:
            raise OSError(
                0,
                f"Unable to resolve libseccomp architecture: {expected}",
            )

        if native_token != policy_token:
            raise OSError(
                0,
                "libseccomp architecture token mismatch",
            )

    def _default_action(self, policy: SeccompPolicy) -> int:
        """Translate the LYRION policy action into a libseccomp action."""
        if policy.default_action is SeccompDefaultAction.KILL_PROCESS:
            return self._SCMP_ACT_KILL_PROCESS

        if policy.default_action is SeccompDefaultAction.ERRNO:
            # The current LYRION policy contract carries no errno field.
            # EPERM is therefore the only deterministic native mapping.
            return self._SCMP_ACT_ERRNO_BASE | 1

        raise ValueError(
            f"Unsupported Seccomp default action: "
            f"{policy.default_action!r}",
        )

    def _require_no_new_privs(self) -> None:
        """Require an already-established no_new_privs state."""
        operations = LibcNoNewPrivsOperations()

        if not operations.get_no_new_privs():
            raise PermissionError(
                "no_new_privs must already be enabled before "
                "native seccomp installation",
            )

    def install_policy(self, policy: SeccompPolicy) -> None:
        """Compile and load a native seccomp filter."""
        self._validate_architecture(policy)
        self._require_no_new_privs()

        default_action = self._default_action(policy)

        ctx = self._lib.seccomp_init(default_action)

        if not ctx:
            raise OSError(
                0,
                "seccomp_init failed",
            )

        try:
            # LYRION owns no_new_privs through its dedicated primitive.
            # Do not permit libseccomp to silently establish it here.
            rc = self._lib.seccomp_attr_set(
                ctx,
                self._SCMP_FLTATR_CTL_NNP,
                0,
            )

            if rc < 0:
                self._raise_libseccomp(
                    "seccomp_attr_set(CTL_NNP=0)",
                    rc,
                )

            for syscall_name in policy.allowed_syscalls:
                encoded_name = syscall_name.encode("ascii")

                syscall_number = (
                    self._lib.seccomp_syscall_resolve_name(
                        encoded_name,
                    )
                )

                if syscall_number < 0:
                    raise ValueError(
                        "Syscall is unavailable on the native "
                        f"architecture: {syscall_name}",
                    )

                rc = self._lib.seccomp_rule_add(
                    ctx,
                    self._SCMP_ACT_ALLOW,
                    syscall_number,
                    0,
                )

                if rc < 0:
                    self._raise_libseccomp(
                        f"seccomp_rule_add({syscall_name})",
                        rc,
                    )

            rc = self._lib.seccomp_load(ctx)

            if rc < 0:
                self._raise_libseccomp(
                    "seccomp_load",
                    rc,
                )

        finally:
            self._lib.seccomp_release(ctx)

    def get_state(self) -> SeccompState:
        """Read independently observable kernel seccomp state."""
        status_path = "/proc/self/status"

        try:
            status = open(
                status_path,
                encoding="utf-8",
            ).read()
        except OSError as exc:
            raise OSError(
                exc.errno or 0,
                f"Unable to read {status_path}: {exc}",
            ) from exc

        values: dict[str, str] = {}

        for line in status.splitlines():
            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()

        try:
            seccomp_mode = int(values["Seccomp"])
            filter_count = int(values["Seccomp_filters"])
        except (KeyError, ValueError) as exc:
            raise OSError(
                0,
                "Unable to independently determine kernel seccomp state",
            ) from exc

        installed = seccomp_mode == 2 and filter_count > 0

        architecture = self._native_architecture()

        return SeccompState(
            architecture=architecture,
            installed=installed,
            seccomp_mode=seccomp_mode,
            filter_count=filter_count,
        )


class SeccompAdapter(PrimitiveAdapter):
    """Seccomp enforcement primitive adapter."""

    primitive = EnforcementPrimitive.SECCOMP

    def __init__(
        self,
        *,
        policy: SeccompPolicy,
        operations: SeccompOperations,
        attestation: SeccompPolicyAttestation | None = None,
    ) -> None:
        self._policy = policy
        self._operations = operations
        self._attestation = (
            attest_policy(policy)
            if attestation is None
            else attestation
        )

    def supports(self, plan: LinuxEnforcementPlan) -> bool:
        """Return whether the plan contains a Seccomp requirement."""
        return self._requirement(plan) is not None

    def validate(
        self,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Validate Seccomp requirements without changing host state."""
        requirement = self._requirement(plan)

        if requirement is None:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason="Seccomp requirement is absent",
            )

        if requirement.required != plan.seccomp.required:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=(
                    "Seccomp requirement and Seccomp plan have "
                    "inconsistent required state"
                ),
            )

        validation = SeccompPolicyValidator.validate(
            self._policy,
            required=plan.seccomp.required,
        )

        if not validation.valid:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=f"Seccomp policy validation failed: {validation.reason}",
            )

        if not plan.seccomp.required:
            return self._result(
                plan=plan,
                state=EnforcementState.PLANNED,
                success=True,
                reason="Seccomp enforcement is not required",
            )

        return self._result(
            plan=plan,
            state=EnforcementState.SUPPORTED,
            success=True,
            reason=(
                "Seccomp policy and enforcement requirement are "
                "structurally valid"
            ),
        )

    def apply(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Apply Seccomp through the injected operation boundary."""
        del context

        validation = self.validate(plan)

        if validation.state is EnforcementState.FAILED:
            return validation

        if not plan.seccomp.required:
            return self._result(
                plan=plan,
                state=EnforcementState.APPLIED,
                success=True,
                reason="Seccomp enforcement is not required",
            )

        try:
            self._operations.install_policy(self._policy)

            return self._result(
                plan=plan,
                state=EnforcementState.APPLIED,
                success=True,
                reason=(
                    "Seccomp policy application completed; "
                    "independent verification is required"
                ),
            )

        except (OSError, ValueError) as exc:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=f"Seccomp policy application failed: {exc}",
            )

    def verify(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Independently verify kernel state and LYRION policy attestation."""
        del context

        validation = self.validate(plan)

        if validation.state is EnforcementState.FAILED:
            return validation

        if not plan.seccomp.required:
            evidence: tuple[EnforcementEvidence, ...] = (
                EnforcementEvidence.verified(
                    primitive=self.primitive,
                    evidence_type="seccomp_policy",
                    observation=(
                        "Seccomp enforcement is not required; "
                        "no kernel filter verification was necessary."
                    ),
                ),
            )

            return self._result(
                plan=plan,
                state=EnforcementState.VERIFIED,
                success=True,
                reason="Seccomp enforcement is not required",
                evidence=evidence,
            )

        try:
            current = self._operations.get_state()

            # Kernel-observable verification.
            if current.seccomp_mode != 2:
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason=(
                        "Kernel Seccomp mode verification failed: "
                        f"expected 2, observed {current.seccomp_mode}"
                    ),
                )

            if current.filter_count < 1:
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason=(
                        "Kernel Seccomp filter-count verification failed: "
                        f"expected >= 1, observed {current.filter_count}"
                    ),
                )

            if not current.installed:
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason="Kernel Seccomp filter is not installed",
                )

            if current.architecture != self._policy.architecture.value:
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason=(
                        "Seccomp architecture verification failed: "
                        f"expected {self._policy.architecture.value}, "
                        f"observed {current.architecture}"
                    ),
                )

            # Application-level policy attestation verification.
            if not verify_policy_attestation(
                self._policy,
                self._attestation,
            ):
                return self._result(
                    plan=plan,
                    state=EnforcementState.FAILED,
                    success=False,
                    reason=(
                        "LYRION Seccomp policy attestation verification "
                        "failed"
                    ),
                )

            evidence = (
                EnforcementEvidence.verified(
                    primitive=self.primitive,
                    evidence_type="seccomp_kernel_state",
                    observation=(
                        "Kernel Seccomp state independently verified: "
                        "mode=2, filter_count>=1, filter installed, "
                        f"architecture={current.architecture}."
                    ),
                ),
                EnforcementEvidence.verified(
                    primitive=self.primitive,
                    evidence_type="seccomp_policy_attestation",
                    observation=(
                        "LYRION policy identity and canonical SHA-256 "
                        "attestation independently verified in the "
                        "application trust boundary: "
                        f"policy_id={self._attestation.policy_id}, "
                        f"policy_version={self._attestation.policy_version}, "
                        f"digest={self._attestation.policy_digest}."
                    ),
                ),
            )

            return self._result(
                plan=plan,
                state=EnforcementState.VERIFIED,
                success=True,
                reason=(
                    "Seccomp kernel enforcement and LYRION policy "
                    "attestation independently verified"
                ),
                evidence=evidence,
            )

        except (OSError, ValueError) as exc:
            return self._result(
                plan=plan,
                state=EnforcementState.FAILED,
                success=False,
                reason=f"Seccomp verification failed: {exc}",
            )

    def evidence(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> tuple[EnforcementEvidence, ...]:
        """Return independently collected Seccomp evidence."""
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
        """Return the authoritative Seccomp requirement."""
        return next(
            (
                requirement
                for requirement in plan.requirements
                if requirement.primitive is EnforcementPrimitive.SECCOMP
            ),
            None,
        )


__all__ = [
    "NativeSeccompOperations",
    "SeccompAdapter",
    "SeccompOperations",
    "SeccompState",
]
