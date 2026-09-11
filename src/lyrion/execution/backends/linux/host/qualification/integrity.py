"""Deterministic qualification-basis integrity primitives.

R1.3.4-C:
- Binds qualification to its exact host/policy/requirements/capability basis.
- Provides deterministic canonicalization and SHA-256 integrity digests.
- Does not authorize, execute, enforce, mutate, or elevate privileges.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Final

_QUALIFICATION_BASIS_SCHEMA: Final[str] = "lyrion.r1.3.4-c.qualification-basis.v1"


class QualificationIntegrityError(ValueError):
    """Raised when qualification-basis integrity requirements are violated."""


@dataclass(frozen=True, slots=True)
class QualificationBasis:
    """Immutable inputs that define a qualification result."""

    host_fingerprint_digest: str
    policy_id: str
    policy_version: str
    requirement_set_id: str
    capability_evaluation_digest: str
    qualification_rules_version: str

    def __post_init__(self) -> None:
        fields = (
            ("host_fingerprint_digest", self.host_fingerprint_digest),
            ("policy_id", self.policy_id),
            ("policy_version", self.policy_version),
            ("requirement_set_id", self.requirement_set_id),
            (
                "capability_evaluation_digest",
                self.capability_evaluation_digest,
            ),
            (
                "qualification_rules_version",
                self.qualification_rules_version,
            ),
        )

        for name, value in fields:
            if not isinstance(value, str) or not value.strip():
                raise QualificationIntegrityError(
                    f"{name} must be a non-empty string"
                )

            if value != value.strip():
                raise QualificationIntegrityError(
                    f"{name} must not contain surrounding whitespace"
                )

    def canonical_payload(self) -> dict[str, str]:
        """Return the stable schema-versioned canonical payload."""
        return {
            "schema": _QUALIFICATION_BASIS_SCHEMA,
            "host_fingerprint_digest": self.host_fingerprint_digest,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "requirement_set_id": self.requirement_set_id,
            "capability_evaluation_digest": self.capability_evaluation_digest,
            "qualification_rules_version": self.qualification_rules_version,
        }


def canonicalize_basis(basis: QualificationBasis) -> bytes:
    """Return deterministic UTF-8 canonical JSON bytes."""
    if not isinstance(basis, QualificationBasis):
        raise TypeError("basis must be a QualificationBasis")

    return json.dumps(
        basis.canonical_payload(),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def qualification_basis_digest(basis: QualificationBasis) -> str:
    """Calculate the deterministic SHA-256 basis digest."""
    return hashlib.sha256(canonicalize_basis(basis)).hexdigest()


def verify_basis_digest(
    basis: QualificationBasis,
    expected_digest: str,
) -> bool:
    """Verify an expected digest against the canonical basis."""
    if not isinstance(expected_digest, str) or not expected_digest.strip():
        return False

    return qualification_basis_digest(basis) == expected_digest


@dataclass(frozen=True, slots=True)
class QualificationEvidenceBinding:
    """Immutable evidence binding for one qualification result."""

    qualification_id: str
    basis: QualificationBasis
    basis_digest: str
    evidence_identity: str

    def __post_init__(self) -> None:
        if not self.qualification_id.strip():
            raise QualificationIntegrityError(
                "qualification_id must be non-empty"
            )

        if not self.evidence_identity.strip():
            raise QualificationIntegrityError(
                "evidence_identity must be non-empty"
            )

        calculated = qualification_basis_digest(self.basis)
        if self.basis_digest != calculated:
            raise QualificationIntegrityError(
                "basis_digest does not match the canonical qualification basis"
            )
