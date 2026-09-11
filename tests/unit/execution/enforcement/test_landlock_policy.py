"""Deterministic tests for the C2.2-C7-R1 Landlock policy contract."""

from __future__ import annotations

from lyrion.execution.backends.linux.enforcement.landlock_policy import (
    LandlockAbiCapabilities,
    LandlockFilesystemAccess,
    LandlockPolicy,
    LandlockPolicyValidationState,
    LandlockPolicyValidator,
    attest_policy,
    canonical_policy_bytes,
    filesystem_access_for_abi,
    verify_policy_attestation,
)


def _policy() -> LandlockPolicy:
    handled = (
        LandlockFilesystemAccess.EXECUTE
        | LandlockFilesystemAccess.READ_FILE
        | LandlockFilesystemAccess.READ_DIR
        | LandlockFilesystemAccess.WRITE_FILE
        | LandlockFilesystemAccess.TRUNCATE
    )

    return LandlockPolicy(
        policy_id="LYRION-TEST-LANDLOCK",
        policy_version="1.0.0",
        minimum_abi=3,
        handled_access_fs=handled,
        default_allowed_access_fs=(
            LandlockFilesystemAccess.EXECUTE
            | LandlockFilesystemAccess.READ_FILE
            | LandlockFilesystemAccess.READ_DIR
        ),
    )


def test_abi_capability_mapping_is_deterministic() -> None:
    assert (
        filesystem_access_for_abi(1)
        & LandlockFilesystemAccess.REFER
    ) == 0

    assert (
        filesystem_access_for_abi(2)
        & LandlockFilesystemAccess.REFER
    )

    assert (
        filesystem_access_for_abi(3)
        & LandlockFilesystemAccess.TRUNCATE
    )

    assert (
        filesystem_access_for_abi(5)
        & LandlockFilesystemAccess.IOCTL_DEV
    )


def test_policy_is_immutable() -> None:
    policy = _policy()

    try:
        policy.policy_id = "modified"  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        raise AssertionError("LandlockPolicy must be immutable")


def test_default_allowed_access_must_be_handled() -> None:
    try:
        LandlockPolicy(
            policy_id="LYRION-INVALID",
            policy_version="1.0.0",
            minimum_abi=1,
            handled_access_fs=LandlockFilesystemAccess.READ_FILE,
            default_allowed_access_fs=(
                LandlockFilesystemAccess.READ_FILE
                | LandlockFilesystemAccess.WRITE_FILE
            ),
        )
    except ValueError as exc:
        assert "subset" in str(exc)
    else:
        raise AssertionError(
            "Invalid Landlock access relationship was accepted"
        )


def test_validator_accepts_supported_policy() -> None:
    policy = _policy()

    capabilities = LandlockAbiCapabilities(
        abi_version=7,
        filesystem_access=filesystem_access_for_abi(7),
    )

    result = LandlockPolicyValidator().validate(
        policy,
        capabilities,
    )

    assert result.state is LandlockPolicyValidationState.VALID
    assert result.success is True


def test_validator_rejects_insufficient_abi() -> None:
    policy = _policy()

    capabilities = LandlockAbiCapabilities(
        abi_version=2,
        filesystem_access=filesystem_access_for_abi(2),
    )

    result = LandlockPolicyValidator().validate(
        policy,
        capabilities,
    )

    assert result.state is LandlockPolicyValidationState.FAILED
    assert result.success is False
    assert "ABI requirement" in result.reason


def test_validator_rejects_unsupported_right() -> None:
    policy = LandlockPolicy(
        policy_id="LYRION-TEST-LANDLOCK",
        policy_version="1.0.0",
        minimum_abi=1,
        handled_access_fs=(
            LandlockFilesystemAccess.READ_FILE
            | LandlockFilesystemAccess.TRUNCATE
        ),
        default_allowed_access_fs=LandlockFilesystemAccess.READ_FILE,
    )

    capabilities = LandlockAbiCapabilities(
        abi_version=2,
        filesystem_access=filesystem_access_for_abi(2),
    )

    result = LandlockPolicyValidator().validate(
        policy,
        capabilities,
    )

    assert result.state is LandlockPolicyValidationState.FAILED
    assert result.success is False
    assert "unsupported" in result.reason


def test_non_required_policy_is_valid_without_capability() -> None:
    policy = _policy()

    capabilities = LandlockAbiCapabilities(
        abi_version=0,
        filesystem_access=LandlockFilesystemAccess(0),
    )

    result = LandlockPolicyValidator().validate(
        policy,
        capabilities,
        required=False,
    )

    assert result.state is LandlockPolicyValidationState.VALID
    assert result.success is True


def test_canonical_policy_bytes_are_deterministic() -> None:
    policy = _policy()

    assert canonical_policy_bytes(policy) == canonical_policy_bytes(
        policy
    )


def test_policy_attestation_is_deterministic() -> None:
    policy = _policy()

    first = attest_policy(policy)
    second = attest_policy(policy)

    assert first == second
    assert len(first.policy_digest) == 64


def test_policy_attestation_verifies_exact_policy() -> None:
    policy = _policy()
    attestation = attest_policy(policy)

    assert verify_policy_attestation(
        policy,
        attestation,
    ) is True


def test_policy_attestation_rejects_modified_policy() -> None:
    policy = _policy()
    attestation = attest_policy(policy)

    modified = LandlockPolicy(
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        minimum_abi=policy.minimum_abi,
        handled_access_fs=(
            policy.handled_access_fs
            | LandlockFilesystemAccess.REMOVE_FILE
        ),
        default_allowed_access_fs=policy.default_allowed_access_fs,
    )

    assert verify_policy_attestation(
        modified,
        attestation,
    ) is False


def test_policy_attestation_rejects_modified_identity() -> None:
    policy = _policy()
    attestation = attest_policy(policy)

    modified = LandlockPolicy(
        policy_id="OTHER-POLICY",
        policy_version=policy.policy_version,
        minimum_abi=policy.minimum_abi,
        handled_access_fs=policy.handled_access_fs,
        default_allowed_access_fs=policy.default_allowed_access_fs,
    )

    assert verify_policy_attestation(
        modified,
        attestation,
    ) is False
