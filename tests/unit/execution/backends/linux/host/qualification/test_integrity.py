"""R1.3.4-C qualification-basis integrity tests."""

from __future__ import annotations

import dataclasses

import pytest

from lyrion.execution.backends.linux.host.qualification.integrity import (
    QualificationBasis,
    QualificationEvidenceBinding,
    QualificationIntegrityError,
    canonicalize_basis,
    qualification_basis_digest,
    verify_basis_digest,
)


def make_basis() -> QualificationBasis:
    return QualificationBasis(
        host_fingerprint_digest="host-" + "a" * 64,
        policy_id="ubuntu-x86_64",
        policy_version="1",
        requirement_set_id="security-baseline-v1",
        capability_evaluation_digest="cap-" + "b" * 64,
        qualification_rules_version="r1.3.4-c.v1",
    )


def test_basis_is_immutable() -> None:
    basis = make_basis()

    with pytest.raises(dataclasses.FrozenInstanceError):
        basis.policy_id = "changed"  # type: ignore[misc]


def test_canonicalization_is_deterministic() -> None:
    basis = make_basis()

    assert canonicalize_basis(basis) == canonicalize_basis(basis)
    assert qualification_basis_digest(basis) == qualification_basis_digest(basis)


def test_digest_is_sha256_hex() -> None:
    digest = qualification_basis_digest(make_basis())

    assert len(digest) == 64
    assert all(character in "0123456789abcdef" for character in digest)


def test_digest_changes_when_policy_version_changes() -> None:
    original = make_basis()
    changed = dataclasses.replace(original, policy_version="2")

    assert qualification_basis_digest(original) != qualification_basis_digest(
        changed
    )


def test_digest_changes_when_host_basis_changes() -> None:
    original = make_basis()
    changed = dataclasses.replace(
        original,
        host_fingerprint_digest="host-" + "c" * 64,
    )

    assert qualification_basis_digest(original) != qualification_basis_digest(
        changed
    )


def test_digest_changes_when_requirement_set_changes() -> None:
    original = make_basis()
    changed = dataclasses.replace(
        original,
        requirement_set_id="security-baseline-v2",
    )

    assert qualification_basis_digest(original) != qualification_basis_digest(
        changed
    )


def test_verify_basis_digest_accepts_matching_digest() -> None:
    basis = make_basis()
    digest = qualification_basis_digest(basis)

    assert verify_basis_digest(basis, digest) is True


def test_verify_basis_digest_rejects_mismatched_digest() -> None:
    basis = make_basis()

    assert verify_basis_digest(basis, "0" * 64) is False


@pytest.mark.parametrize(
    "field",
    (
        "host_fingerprint_digest",
        "policy_id",
        "policy_version",
        "requirement_set_id",
        "capability_evaluation_digest",
        "qualification_rules_version",
    ),
)
def test_basis_rejects_empty_fields(field: str) -> None:
    values = {
        field_name: getattr(make_basis(), field_name)
        for field_name in (
            "host_fingerprint_digest",
            "policy_id",
            "policy_version",
            "requirement_set_id",
            "capability_evaluation_digest",
            "qualification_rules_version",
        )
    }
    values[field] = ""

    with pytest.raises(QualificationIntegrityError):
        QualificationBasis(**values)


def test_evidence_binding_requires_correct_basis_digest() -> None:
    basis = make_basis()

    with pytest.raises(QualificationIntegrityError):
        QualificationEvidenceBinding(
            qualification_id="qualification-1",
            basis=basis,
            basis_digest="0" * 64,
            evidence_identity="evidence-1",
        )


def test_evidence_binding_accepts_matching_basis_digest() -> None:
    basis = make_basis()

    binding = QualificationEvidenceBinding(
        qualification_id="qualification-1",
        basis=basis,
        basis_digest=qualification_basis_digest(basis),
        evidence_identity="evidence-1",
    )

    assert binding.basis == basis
