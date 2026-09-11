"""Seccomp policy attestation and canonical policy identity."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from lyrion.execution.backends.linux.enforcement.seccomp_policy import (
    SeccompPolicy,
)

_SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


@dataclass(frozen=True, slots=True)
class SeccompPolicyAttestation:
    """Immutable identity for the exact LYRION policy supplied to libseccomp."""

    policy_id: str
    policy_version: str
    policy_digest: str
    architecture: str

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise ValueError("policy_id must not be empty")

        if not _SEMVER_RE.fullmatch(self.policy_version):
            raise ValueError(
                "policy_version must use semantic versioning"
            )

        if not re.fullmatch(r"[0-9a-f]{64}", self.policy_digest):
            raise ValueError(
                "policy_digest must be a lowercase SHA-256 hexadecimal digest"
            )

        if not self.architecture:
            raise ValueError("architecture must not be empty")


def canonical_policy_bytes(policy: SeccompPolicy) -> bytes:
    """Serialize the policy deterministically for attestation."""
    payload = {
        "architecture": policy.architecture.value,
        "allowed_syscalls": list(policy.allowed_syscalls),
        "default_action": policy.default_action.value,
        "policy_id": policy.policy_id,
        "policy_version": policy.policy_version,
    }

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def attest_policy(policy: SeccompPolicy) -> SeccompPolicyAttestation:
    """Create a deterministic SHA-256 attestation for a policy."""
    digest = hashlib.sha256(
        canonical_policy_bytes(policy)
    ).hexdigest()

    return SeccompPolicyAttestation(
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        policy_digest=digest,
        architecture=policy.architecture.value,
    )


def verify_policy_attestation(
    policy: SeccompPolicy,
    attestation: SeccompPolicyAttestation,
) -> bool:
    """Verify that an attestation corresponds exactly to the supplied policy."""
    expected = attest_policy(policy)

    return (
        expected.policy_id == attestation.policy_id
        and expected.policy_version == attestation.policy_version
        and expected.policy_digest == attestation.policy_digest
        and expected.architecture == attestation.architecture
    )
