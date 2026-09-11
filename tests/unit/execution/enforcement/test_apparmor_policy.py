"""Tests for deterministic AppArmor policy validation and attestation."""

from __future__ import annotations

from lyrion.execution.backends.linux.enforcement.apparmor_policy import (
    AppArmorMode,
    AppArmorPolicy,
    AppArmorPolicyValidationState,
    AppArmorPolicyValidator,
    attest_policy,
    canonical_policy_bytes,
    verify_policy_attestation,
)


def make_policy(
    *,
    profile_name: str = "lyrion-test",
    mode: AppArmorMode = AppArmorMode.ENFORCE,
) -> AppArmorPolicy:
    return AppArmorPolicy(
        profile_name=profile_name,
        policy_version="1.0.0",
        mode=mode,
        profile_text="""profile lyrion-test {
    /usr/bin/python3 rix,
}
""",
    )


def test_valid_policy_passes() -> None:
    result = AppArmorPolicyValidator().validate(
        make_policy(),
    )

    assert result.state is AppArmorPolicyValidationState.VALID
    assert result.success


def test_optional_policy_can_be_valid_without_enforcement() -> None:
    result = AppArmorPolicyValidator().validate(
        make_policy(mode=AppArmorMode.COMPLAIN),
        required=False,
    )

    assert result.success


def test_required_policy_rejects_complain_mode() -> None:
    result = AppArmorPolicyValidator().validate(
        make_policy(mode=AppArmorMode.COMPLAIN),
        required=True,
    )

    assert result.state is AppArmorPolicyValidationState.FAILED
    assert not result.success


def test_invalid_profile_name_is_rejected() -> None:
    policy = make_policy(profile_name="bad name")

    result = AppArmorPolicyValidator().validate(policy)

    assert not result.success
    assert result.state is AppArmorPolicyValidationState.FAILED


def test_nul_byte_is_rejected() -> None:
    policy = AppArmorPolicy(
        profile_name="lyrion-test",
        policy_version="1.0.0",
        profile_text="profile lyrion-test {\x00}",
    )

    result = AppArmorPolicyValidator().validate(policy)

    assert not result.success


def test_empty_policy_is_rejected() -> None:
    policy = AppArmorPolicy(
        profile_name="lyrion-test",
        policy_version="1.0.0",
        profile_text="   ",
    )

    result = AppArmorPolicyValidator().validate(policy)

    assert not result.success


def test_missing_profile_declaration_is_rejected() -> None:
    policy = AppArmorPolicy(
        profile_name="lyrion-test",
        policy_version="1.0.0",
        profile_text="/usr/bin/python3 rix,",
    )

    result = AppArmorPolicyValidator().validate(policy)

    assert not result.success


def test_canonical_policy_bytes_are_deterministic() -> None:
    policy = make_policy()

    assert canonical_policy_bytes(policy) == canonical_policy_bytes(policy)


def test_policy_attestation_is_deterministic() -> None:
    policy = make_policy()

    first = attest_policy(policy)
    second = attest_policy(policy)

    assert first == second
    assert len(first.policy_digest) == 64


def test_policy_attestation_verifies() -> None:
    policy = make_policy()
    attestation = attest_policy(policy)

    assert verify_policy_attestation(
        policy,
        attestation,
    )


def test_modified_policy_fails_attestation() -> None:
    policy = make_policy()
    attestation = attest_policy(policy)

    modified = AppArmorPolicy(
        profile_name=policy.profile_name,
        policy_version=policy.policy_version,
        profile_text=policy.profile_text.replace(
            "/usr/bin/python3",
            "/usr/bin/python3.12",
        ),
        mode=policy.mode,
    )

    assert not verify_policy_attestation(
        modified,
        attestation,
    )


def test_policy_is_immutable() -> None:
    policy = make_policy()

    try:
        policy.profile_name = "modified"  # type: ignore[misc]
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError("AppArmor policy must be immutable")
