"""Deterministic AppArmor policy model and attestation."""

from __future__ import annotations

import hashlib
import json
import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

_PROFILE_NAME_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,254}$"
)


class AppArmorMode(StrEnum):
    """Supported AppArmor profile modes."""

    ENFORCE = "enforce"
    COMPLAIN = "complain"


class AppArmorPolicyValidationState(StrEnum):
    """Policy validation outcome."""

    VALID = "valid"
    FAILED = "failed"


class AppArmorPolicyValidationResult(BaseModel):
    """Immutable AppArmor policy validation result."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    state: AppArmorPolicyValidationState
    success: bool
    reason: str = Field(min_length=1, max_length=1000)


class AppArmorPolicyAttestation(BaseModel):
    """Deterministic application-level identity for an AppArmor policy."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    profile_name: str
    policy_version: str
    policy_digest: str
    mode: AppArmorMode


class AppArmorPolicy(BaseModel):
    """
    Immutable AppArmor profile policy.

    This model represents application-owned policy identity and source.
    It does not load policy into the kernel and does not claim enforcement.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    profile_name: str = Field(min_length=1, max_length=255)
    policy_version: str = Field(
        min_length=1,
        max_length=64,
    )
    profile_text: str = Field(
        min_length=1,
        max_length=1_000_000,
    )
    mode: AppArmorMode = AppArmorMode.ENFORCE


def canonical_policy_bytes(policy: AppArmorPolicy) -> bytes:
    """Return deterministic bytes used for policy attestation."""

    payload = {
        "mode": policy.mode.value,
        "policy_version": policy.policy_version,
        "profile_name": policy.profile_name,
        "profile_text": policy.profile_text,
    }

    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def attest_policy(policy: AppArmorPolicy) -> AppArmorPolicyAttestation:
    """Create deterministic SHA-256 attestation for an AppArmor policy."""

    digest = hashlib.sha256(
        canonical_policy_bytes(policy)
    ).hexdigest()

    return AppArmorPolicyAttestation(
        profile_name=policy.profile_name,
        policy_version=policy.policy_version,
        policy_digest=digest,
        mode=policy.mode,
    )


def verify_policy_attestation(
    policy: AppArmorPolicy,
    attestation: AppArmorPolicyAttestation,
) -> bool:
    """Verify policy identity against a previously generated attestation."""

    expected = attest_policy(policy)

    return expected == attestation


class AppArmorPolicyValidator:
    """Validate AppArmor policy structure without kernel mutation."""

    def validate(
        self,
        policy: AppArmorPolicy,
        *,
        required: bool = True,
    ) -> AppArmorPolicyValidationResult:
        """Validate policy structure and security invariants."""

        if not required:
            return AppArmorPolicyValidationResult(
                state=AppArmorPolicyValidationState.VALID,
                success=True,
                reason="AppArmor is not required by the execution plan.",
            )

        profile_name = policy.profile_name

        if not _PROFILE_NAME_RE.fullmatch(profile_name):
            return AppArmorPolicyValidationResult(
                state=AppArmorPolicyValidationState.FAILED,
                success=False,
                reason="AppArmor profile name contains unsupported characters.",
            )

        if "\x00" in policy.profile_text:
            return AppArmorPolicyValidationResult(
                state=AppArmorPolicyValidationState.FAILED,
                success=False,
                reason="AppArmor policy contains a NUL byte.",
            )

        if not policy.profile_text.strip():
            return AppArmorPolicyValidationResult(
                state=AppArmorPolicyValidationState.FAILED,
                success=False,
                reason="AppArmor policy cannot be empty.",
            )

        if policy.mode is AppArmorMode.COMPLAIN:
            return AppArmorPolicyValidationResult(
                state=AppArmorPolicyValidationState.FAILED,
                success=False,
                reason=(
                    "Required AppArmor enforcement cannot use complain mode."
                ),
            )

        if "profile " not in policy.profile_text:
            return AppArmorPolicyValidationResult(
                state=AppArmorPolicyValidationState.FAILED,
                success=False,
                reason="AppArmor policy does not contain a profile declaration.",
            )

        return AppArmorPolicyValidationResult(
            state=AppArmorPolicyValidationState.VALID,
            success=True,
            reason="AppArmor policy passed structural validation.",
        )
