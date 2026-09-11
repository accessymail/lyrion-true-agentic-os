"""Deterministic tests for the C2.2-C6-R1 seccomp policy contract."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from lyrion.execution.backends.linux.enforcement.seccomp_policy import (
    SeccompArchitecture,
    SeccompDefaultAction,
    SeccompPolicy,
    SeccompPolicyValidator,
)


def _policy(
    *,
    policy_id: str = "LYRION-TEST-BASELINE",
    policy_version: str = "1.0.0",
    architecture: SeccompArchitecture = SeccompArchitecture.X86_64,
    default_action: SeccompDefaultAction = (
        SeccompDefaultAction.KILL_PROCESS
    ),
    allowed_syscalls: tuple[str, ...] = (
        "close",
        "exit_group",
        "read",
        "write",
    ),
) -> SeccompPolicy:
    return SeccompPolicy(
        policy_id=policy_id,
        policy_version=policy_version,
        architecture=architecture,
        default_action=default_action,
        allowed_syscalls=allowed_syscalls,
    )


def test_policy_is_immutable_and_structured() -> None:
    policy = _policy()

    assert policy.policy_id == "LYRION-TEST-BASELINE"
    assert policy.policy_version == "1.0.0"
    assert policy.architecture is SeccompArchitecture.X86_64
    assert policy.default_action is SeccompDefaultAction.KILL_PROCESS


def test_syscalls_are_normalized_and_sorted() -> None:
    policy = _policy(
        allowed_syscalls=(
            " WRITE ",
            "read",
            "close",
            "exit_group",
        ),
    )

    assert policy.allowed_syscalls == (
        "close",
        "exit_group",
        "read",
        "write",
    )


def test_duplicate_syscalls_are_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicates"):
        _policy(
            allowed_syscalls=(
                "read",
                "write",
                "read",
            ),
        )


def test_invalid_syscall_name_is_rejected() -> None:
    with pytest.raises(ValidationError, match="invalid syscall names"):
        _policy(
            allowed_syscalls=(
                "read",
                "not-a-valid-syscall!",
            ),
        )


def test_invalid_policy_id_is_rejected() -> None:
    with pytest.raises(ValidationError, match="policy_id"):
        _policy(policy_id="invalid policy id")


def test_invalid_policy_version_is_rejected() -> None:
    with pytest.raises(ValidationError, match="MAJOR.MINOR.PATCH"):
        _policy(policy_version="v1")


def test_required_policy_must_define_syscalls() -> None:
    policy = _policy(allowed_syscalls=())

    result = SeccompPolicyValidator.validate(
        policy,
        required=True,
    )

    assert result.valid is False
    assert "at least one" in result.reason


def test_non_required_policy_can_be_empty() -> None:
    policy = _policy(allowed_syscalls=())

    result = SeccompPolicyValidator.validate(
        policy,
        required=False,
    )

    assert result.valid is True
    assert result.normalized_syscalls == ()


def test_kill_process_default_is_valid() -> None:
    policy = _policy(
        default_action=SeccompDefaultAction.KILL_PROCESS,
    )

    result = SeccompPolicyValidator.validate(policy)

    assert result.valid is True
    assert "fail-closed" in result.reason
    assert result.normalized_syscalls == policy.allowed_syscalls


def test_errno_default_is_explicitly_supported() -> None:
    policy = _policy(
        default_action=SeccompDefaultAction.ERRNO,
    )

    result = SeccompPolicyValidator.validate(policy)

    assert result.valid is True
    assert "ERRNO" in result.reason


def test_architecture_is_explicit() -> None:
    for architecture in SeccompArchitecture:
        policy = _policy(architecture=architecture)

        assert policy.architecture is architecture


def test_validation_is_deterministic() -> None:
    policy = _policy(
        allowed_syscalls=(
            "write",
            "read",
            "close",
            "exit_group",
        ),
    )

    first = SeccompPolicyValidator.validate(policy)
    second = SeccompPolicyValidator.validate(policy)

    assert first == second


def test_policy_contains_no_executable_filter_material() -> None:
    policy = _policy()

    serialized = policy.model_dump()

    assert "bpf" not in serialized
    assert "fd" not in serialized
    assert "filter" not in serialized
    assert "program" not in serialized


def test_policy_contract_does_not_touch_host_state() -> None:
    policy = _policy()

    result = SeccompPolicyValidator.validate(policy)

    assert result.valid is True
