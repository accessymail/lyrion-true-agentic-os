"""Immutable seccomp policy contracts and deterministic validation.

C2.2-C6-R1 intentionally defines policy semantics without installing or
executing a seccomp filter.

Security principles:
- policy identity and version are explicit;
- architecture is explicit;
- default action is explicit;
- syscall names are normalized deterministically;
- duplicate syscall entries are rejected;
- empty required policies fail closed;
- no native kernel mutation occurs here;
- executable BPF/libseccomp policy generation belongs to later stages.
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SeccompArchitecture(StrEnum):
    """Supported LYRION seccomp target architectures."""

    X86_64 = "x86_64"
    AARCH64 = "aarch64"
    ARM = "arm"
    I386 = "i386"
    RISCV64 = "riscv64"


class SeccompDefaultAction(StrEnum):
    """Allowed default actions for a seccomp policy."""

    KILL_PROCESS = "kill_process"
    ERRNO = "errno"


_SYSCALL_NAME_PATTERN = re.compile(
    r"^[a-z_][a-z0-9_]{0,127}$",
)

_POLICY_ID_PATTERN = re.compile(
    r"^[A-Z0-9][A-Z0-9._-]{2,127}$",
)

_POLICY_VERSION_PATTERN = re.compile(
    r"^[0-9]+\.[0-9]+\.[0-9]+$",
)


class SeccompPolicy(BaseModel):
    """Immutable declarative seccomp policy.

    This model deliberately contains policy data only. It does not contain
    BPF instructions, file descriptors, native handles, or executable code.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    policy_id: str = Field(
        min_length=3,
        max_length=128,
    )
    policy_version: str = Field(
        min_length=1,
        max_length=32,
    )
    architecture: SeccompArchitecture
    default_action: SeccompDefaultAction
    allowed_syscalls: tuple[str, ...] = ()

    @field_validator("policy_id")
    @classmethod
    def validate_policy_id(cls, value: str) -> str:
        """Require deterministic policy identifiers."""
        if not _POLICY_ID_PATTERN.fullmatch(value):
            raise ValueError(
                "policy_id must contain only uppercase letters, digits, "
                "dot, underscore, or hyphen and must start with an "
                "uppercase letter or digit"
            )

        return value

    @field_validator("policy_version")
    @classmethod
    def validate_policy_version(cls, value: str) -> str:
        """Require semantic-version-shaped policy versions."""
        if not _POLICY_VERSION_PATTERN.fullmatch(value):
            raise ValueError(
                "policy_version must use MAJOR.MINOR.PATCH format"
            )

        return value

    @field_validator("allowed_syscalls")
    @classmethod
    def validate_syscalls(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Validate syscall names without resolving them on the host."""
        normalized = tuple(
            syscall.strip().lower()
            for syscall in value
        )

        if any(not syscall for syscall in normalized):
            raise ValueError("syscall names cannot be empty")

        invalid = tuple(
            syscall
            for syscall in normalized
            if not _SYSCALL_NAME_PATTERN.fullmatch(syscall)
        )

        if invalid:
            raise ValueError(
                "invalid syscall names: "
                + ", ".join(invalid)
            )

        if len(normalized) != len(set(normalized)):
            raise ValueError(
                "allowed_syscalls must not contain duplicates"
            )

        return tuple(sorted(normalized))


class SeccompPolicyValidationResult(BaseModel):
    """Immutable deterministic policy-validation result."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    valid: bool
    reason: str = Field(
        min_length=1,
        max_length=2000,
    )
    normalized_syscalls: tuple[str, ...] = ()


class SeccompPolicyValidator:
    """Validate declarative seccomp policies without host mutation."""

    @staticmethod
    def validate(
        policy: SeccompPolicy,
        *,
        required: bool = True,
    ) -> SeccompPolicyValidationResult:
        """Perform deterministic policy-level validation.

        This method deliberately does not resolve syscall numbers or query
        the host kernel. Native architecture/syscall resolution belongs to
        the later native operation boundary.
        """
        if not required:
            return SeccompPolicyValidationResult(
                valid=True,
                reason="seccomp policy is not required",
                normalized_syscalls=policy.allowed_syscalls,
            )

        if not policy.allowed_syscalls:
            return SeccompPolicyValidationResult(
                valid=False,
                reason=(
                    "required seccomp policy must define at least one "
                    "allowed syscall"
                ),
            )

        if policy.default_action is SeccompDefaultAction.KILL_PROCESS:
            return SeccompPolicyValidationResult(
                valid=True,
                reason=(
                    "required seccomp policy is structurally valid "
                    "with fail-closed KILL_PROCESS default"
                ),
                normalized_syscalls=policy.allowed_syscalls,
            )

        if policy.default_action is SeccompDefaultAction.ERRNO:
            return SeccompPolicyValidationResult(
                valid=True,
                reason=(
                    "required seccomp policy is structurally valid "
                    "with ERRNO default"
                ),
                normalized_syscalls=policy.allowed_syscalls,
            )

        return SeccompPolicyValidationResult(
            valid=False,
            reason="unsupported seccomp default action",
        )


__all__ = [
    "SeccompArchitecture",
    "SeccompDefaultAction",
    "SeccompPolicy",
    "SeccompPolicyValidationResult",
    "SeccompPolicyValidator",
]
