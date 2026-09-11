"""Tests for deterministic Seccomp policy attestation."""

from __future__ import annotations

from lyrion.execution.backends.linux.enforcement.seccomp_attestation import (
    attest_policy,
    canonical_policy_bytes,
    verify_policy_attestation,
)
from lyrion.execution.backends.linux.enforcement.seccomp_policy import (
    SeccompArchitecture,
    SeccompDefaultAction,
    SeccompPolicy,
)


def _policy() -> SeccompPolicy:
    return SeccompPolicy(
        policy_id="LYRION-TEST-ATTESTATION",
        policy_version="1.0.0",
        architecture=SeccompArchitecture.X86_64,
        default_action=SeccompDefaultAction.ERRNO,
        allowed_syscalls=(
            "close",
            "exit",
            "exit_group",
            "write",
        ),
    )


def test_canonical_policy_serialization_is_deterministic() -> None:
    policy = _policy()

    assert canonical_policy_bytes(policy) == canonical_policy_bytes(policy)


def test_attestation_is_deterministic() -> None:
    first = attest_policy(_policy())
    second = attest_policy(_policy())

    assert first == second
    assert len(first.policy_digest) == 64


def test_attestation_matches_exact_policy() -> None:
    policy = _policy()
    attestation = attest_policy(policy)

    assert verify_policy_attestation(policy, attestation) is True


def test_modified_policy_fails_attestation() -> None:
    policy = _policy()
    attestation = attest_policy(policy)

    modified = SeccompPolicy(
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        architecture=policy.architecture,
        default_action=policy.default_action,
        allowed_syscalls=(
            "close",
            "exit",
            "exit_group",
            "read",
            "write",
        ),
    )

    assert verify_policy_attestation(modified, attestation) is False


def test_modified_policy_id_fails_attestation() -> None:
    policy = _policy()
    attestation = attest_policy(policy)

    modified = SeccompPolicy(
        policy_id="LYRION-MODIFIED",
        policy_version=policy.policy_version,
        architecture=policy.architecture,
        default_action=policy.default_action,
        allowed_syscalls=policy.allowed_syscalls,
    )

    assert verify_policy_attestation(modified, attestation) is False
