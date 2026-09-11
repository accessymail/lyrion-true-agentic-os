"""R1.3.4-C immutable qualification evidence contracts.

This module binds a qualification result to the exact host, policy,
requirement set, capability evaluation, and qualification-rule basis
that produced it.

This is integrity/binding evidence only. It does not authenticate a
signer, authorize execution, enforce controls, or mutate the host.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Final

from lyrion.execution.backends.linux.host.contracts import (
    LinuxHostAbstractionSnapshot,
    LinuxHostFingerprint,
)
from lyrion.execution.backends.linux.host.negotiation.contracts import (
    CapabilityNegotiationResult,
)
from lyrion.execution.backends.linux.host.policy.contracts import (
    LinuxHostQualificationPolicy,
)

from .integrity import (
    QualificationBasis,
    QualificationIntegrityError,
    qualification_basis_digest,
)

QUALIFICATION_RULES_VERSION: Final[str] = "r1.3.4-c.v1"
_QUALIFICATION_EVIDENCE_SCHEMA: Final[str] = (
    "lyrion.r1.3.4-c.qualification-evidence.v1"
)


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def host_fingerprint_digest(
    fingerprint: LinuxHostFingerprint,
) -> str:
    """Return the deterministic identity digest of an observed host."""
    payload = {
        "identity": {
            "architecture": fingerprint.identity.architecture,
            "init_system": fingerprint.identity.init_system,
            "kernel": fingerprint.identity.kernel,
            "os_name": fingerprint.identity.os_name,
            "os_version": fingerprint.identity.os_version,
            "virtualization": fingerprint.identity.virtualization,
        },
        "primitives": [
            {
                "primitive": capability.primitive.value,
                "state": capability.state.value,
                "evidence": capability.evidence,
            }
            for capability in sorted(
                fingerprint.primitives,
                key=lambda item: item.primitive.value,
            )
        ],
    }

    return _digest(payload)


def qualification_id(
    *,
    basis_digest: str,
    status: str,
) -> str:
    """Return deterministic identity for one qualification outcome."""
    return _digest(
        {
            "basis_digest": basis_digest,
            "schema": _QUALIFICATION_EVIDENCE_SCHEMA,
            "status": status,
        }
    )


def evidence_identity(
    *,
    qualification_id_value: str,
    basis_digest: str,
) -> str:
    """Return deterministic identity for qualification evidence."""
    return _digest(
        {
            "basis_digest": basis_digest,
            "qualification_id": qualification_id_value,
            "schema": _QUALIFICATION_EVIDENCE_SCHEMA,
        }
    )


@dataclass(frozen=True, slots=True)
class QualificationEvidence:
    """Immutable evidence produced from a qualification result."""

    qualification_id: str
    qualification_state: str
    basis: QualificationBasis
    basis_digest: str
    host_fingerprint_digest: str
    policy_id: str
    policy_version: str
    requirement_set_id: str
    capability_evaluation_digest: str
    evidence_identity: str

    def __post_init__(self) -> None:
        if not self.qualification_id.strip():
            raise QualificationIntegrityError(
                "qualification_id must be non-empty"
            )

        if not self.qualification_state.strip():
            raise QualificationIntegrityError(
                "qualification_state must be non-empty"
            )

        expected_basis_digest = qualification_basis_digest(self.basis)

        if self.basis_digest != expected_basis_digest:
            raise QualificationIntegrityError(
                "qualification evidence basis digest does not match basis"
            )

        if self.host_fingerprint_digest != (
            self.basis.host_fingerprint_digest
        ):
            raise QualificationIntegrityError(
                "host fingerprint does not match qualification basis"
            )

        if self.policy_id != self.basis.policy_id:
            raise QualificationIntegrityError(
                "policy_id does not match qualification basis"
            )

        if self.policy_version != self.basis.policy_version:
            raise QualificationIntegrityError(
                "policy_version does not match qualification basis"
            )

        if self.requirement_set_id != self.basis.requirement_set_id:
            raise QualificationIntegrityError(
                "requirement_set_id does not match qualification basis"
            )

        if self.capability_evaluation_digest != (
            self.basis.capability_evaluation_digest
        ):
            raise QualificationIntegrityError(
                "capability evaluation digest does not match basis"
            )

        expected_identity = evidence_identity(
            qualification_id_value=self.qualification_id,
            basis_digest=self.basis_digest,
        )

        if self.evidence_identity != expected_identity:
            raise QualificationIntegrityError(
                "evidence identity does not match evidence inputs"
            )

    @classmethod
    def from_qualification(
        cls,
        *,
        host_snapshot: LinuxHostAbstractionSnapshot,
        policy: LinuxHostQualificationPolicy,
        negotiation: CapabilityNegotiationResult,
        qualification_state: str,
    ) -> QualificationEvidence:
        """Construct immutable evidence from an actual qualification result."""

        if negotiation.host_snapshot != host_snapshot:
            raise QualificationIntegrityError(
                "negotiation snapshot does not match evidence snapshot"
            )

        host_digest = host_fingerprint_digest(
            host_snapshot.fingerprint
        )

        requirement_set_id = negotiation.profile_id
        capability_digest = negotiation.evidence_digest

        basis = QualificationBasis(
            host_fingerprint_digest=host_digest,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            requirement_set_id=requirement_set_id,
            capability_evaluation_digest=capability_digest,
            qualification_rules_version=QUALIFICATION_RULES_VERSION,
        )

        basis_digest = qualification_basis_digest(basis)

        qualification_id_value = qualification_id(
            basis_digest=basis_digest,
            status=qualification_state,
        )

        return cls(
            qualification_id=qualification_id_value,
            qualification_state=qualification_state,
            basis=basis,
            basis_digest=basis_digest,
            host_fingerprint_digest=host_digest,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            requirement_set_id=requirement_set_id,
            capability_evaluation_digest=capability_digest,
            evidence_identity=evidence_identity(
                qualification_id_value=qualification_id_value,
                basis_digest=basis_digest,
            ),
        )
