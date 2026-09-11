"""Landlock policy, ABI capability, and deterministic attestation contracts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import IntFlag, StrEnum

_SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class LandlockFilesystemAccess(IntFlag):
    """Linux Landlock filesystem access-right bit assignments."""

    EXECUTE = 1 << 0
    WRITE_FILE = 1 << 1
    READ_FILE = 1 << 2
    READ_DIR = 1 << 3
    REMOVE_DIR = 1 << 4
    REMOVE_FILE = 1 << 5
    MAKE_CHAR = 1 << 6
    MAKE_DIR = 1 << 7
    MAKE_REG = 1 << 8
    MAKE_SOCK = 1 << 9
    MAKE_FIFO = 1 << 10
    MAKE_BLOCK = 1 << 11
    MAKE_SYM = 1 << 12
    REFER = 1 << 13
    TRUNCATE = 1 << 14
    IOCTL_DEV = 1 << 15


class LandlockPolicyValidationState(StrEnum):
    """Validation outcome for a Landlock policy."""

    VALID = "valid"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class LandlockAbiCapabilities:
    """Runtime Landlock capability information."""

    abi_version: int
    filesystem_access: LandlockFilesystemAccess

    def __post_init__(self) -> None:
        if self.abi_version < 0:
            raise ValueError("Landlock ABI version must not be negative")

        if self.filesystem_access.value < 0:
            raise ValueError(
                "Landlock filesystem access mask must not be negative"
            )


@dataclass(frozen=True, slots=True)
class LandlockPolicyValidationResult:
    """Deterministic Landlock policy validation result."""

    state: LandlockPolicyValidationState
    success: bool
    reason: str


@dataclass(frozen=True, slots=True)
class LandlockPolicyAttestation:
    """Application-level identity for a deterministic Landlock policy."""

    policy_id: str
    policy_version: str
    policy_digest: str
    minimum_abi: int

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("policy_id must not be empty")

        if not _SEMVER_RE.fullmatch(self.policy_version):
            raise ValueError(
                "policy_version must use MAJOR.MINOR.PATCH format"
            )

        if not _SHA256_RE.fullmatch(self.policy_digest):
            raise ValueError(
                "policy_digest must be a lowercase SHA-256 hexadecimal digest"
            )

        if self.minimum_abi < 1:
            raise ValueError("minimum_abi must be at least 1")


@dataclass(frozen=True, slots=True)
class LandlockPolicy:
    """Immutable filesystem restriction policy for Landlock."""

    policy_id: str
    policy_version: str
    minimum_abi: int
    handled_access_fs: LandlockFilesystemAccess
    default_allowed_access_fs: LandlockFilesystemAccess

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("policy_id must not be empty")

        if not _SEMVER_RE.fullmatch(self.policy_version):
            raise ValueError(
                "policy_version must use MAJOR.MINOR.PATCH format"
            )

        if self.minimum_abi < 1:
            raise ValueError("minimum_abi must be at least 1")

        handled = int(self.handled_access_fs)
        allowed = int(self.default_allowed_access_fs)

        if handled < 0 or allowed < 0:
            raise ValueError("Landlock access masks must not be negative")

        if allowed & ~handled:
            raise ValueError(
                "default allowed access must be a subset of handled access"
            )


def filesystem_access_for_abi(
    abi_version: int,
) -> LandlockFilesystemAccess:
    """Return filesystem rights available through the requested ABI."""

    if abi_version < 1:
        return LandlockFilesystemAccess(0)

    access = (
        LandlockFilesystemAccess.EXECUTE
        | LandlockFilesystemAccess.WRITE_FILE
        | LandlockFilesystemAccess.READ_FILE
        | LandlockFilesystemAccess.READ_DIR
        | LandlockFilesystemAccess.REMOVE_DIR
        | LandlockFilesystemAccess.REMOVE_FILE
        | LandlockFilesystemAccess.MAKE_CHAR
        | LandlockFilesystemAccess.MAKE_DIR
        | LandlockFilesystemAccess.MAKE_REG
        | LandlockFilesystemAccess.MAKE_SOCK
        | LandlockFilesystemAccess.MAKE_FIFO
        | LandlockFilesystemAccess.MAKE_BLOCK
        | LandlockFilesystemAccess.MAKE_SYM
    )

    if abi_version >= 2:
        access |= LandlockFilesystemAccess.REFER

    if abi_version >= 3:
        access |= LandlockFilesystemAccess.TRUNCATE

    if abi_version >= 5:
        access |= LandlockFilesystemAccess.IOCTL_DEV

    return access


def canonical_policy_bytes(policy: LandlockPolicy) -> bytes:
    """Return deterministic canonical policy bytes."""

    payload = {
        "default_allowed_access_fs": int(
            policy.default_allowed_access_fs
        ),
        "handled_access_fs": int(policy.handled_access_fs),
        "minimum_abi": policy.minimum_abi,
        "policy_id": policy.policy_id,
        "policy_version": policy.policy_version,
    }

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def attest_policy(policy: LandlockPolicy) -> LandlockPolicyAttestation:
    """Create deterministic application-level policy attestation."""

    digest = hashlib.sha256(
        canonical_policy_bytes(policy)
    ).hexdigest()

    return LandlockPolicyAttestation(
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        policy_digest=digest,
        minimum_abi=policy.minimum_abi,
    )


def verify_policy_attestation(
    policy: LandlockPolicy,
    attestation: LandlockPolicyAttestation,
) -> bool:
    """Verify that an attestation exactly matches the supplied policy."""

    expected = attest_policy(policy)

    return (
        expected.policy_id == attestation.policy_id
        and expected.policy_version == attestation.policy_version
        and expected.policy_digest == attestation.policy_digest
        and expected.minimum_abi == attestation.minimum_abi
    )


class LandlockPolicyValidator:
    """Deterministic validator for Landlock policy/capability compatibility."""

    def validate(
        self,
        policy: LandlockPolicy,
        capabilities: LandlockAbiCapabilities,
        *,
        required: bool = True,
    ) -> LandlockPolicyValidationResult:
        """Validate policy requirements against detected capabilities."""

        if not required:
            return LandlockPolicyValidationResult(
                state=LandlockPolicyValidationState.VALID,
                success=True,
                reason="Landlock enforcement is not required.",
            )

        if capabilities.abi_version < policy.minimum_abi:
            return LandlockPolicyValidationResult(
                state=LandlockPolicyValidationState.FAILED,
                success=False,
                reason=(
                    "Landlock ABI requirement is unsupported: "
                    f"required {policy.minimum_abi}, "
                    f"observed {capabilities.abi_version}"
                ),
            )

        supported = capabilities.filesystem_access
        required_access = policy.handled_access_fs

        if required_access & ~supported:
            return LandlockPolicyValidationResult(
                state=LandlockPolicyValidationState.FAILED,
                success=False,
                reason=(
                    "Landlock filesystem access requirement is unsupported "
                    "by the detected ABI"
                ),
            )

        if (
            policy.default_allowed_access_fs
            & ~policy.handled_access_fs
        ):
            return LandlockPolicyValidationResult(
                state=LandlockPolicyValidationState.FAILED,
                success=False,
                reason=(
                    "default allowed filesystem access exceeds "
                    "handled filesystem access"
                ),
            )

        return LandlockPolicyValidationResult(
            state=LandlockPolicyValidationState.VALID,
            success=True,
            reason="Landlock policy is compatible with detected capabilities.",
        )
