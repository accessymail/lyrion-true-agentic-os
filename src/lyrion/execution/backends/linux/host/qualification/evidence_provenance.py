from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum

from .change_contracts import HostChange
from .regression_scope import (
    AdaptiveRegressionPlan,
    ValidationRequirement,
)


class EvidenceIntegrityStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"


class EvidenceProvenanceError(ValueError):
    """Raised when qualification evidence provenance is invalid."""


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _change_record(change: HostChange) -> dict[str, str]:
    return {
        "component": change.component,
        "current_value": change.current_value,
        "impact": change.impact.value,
        "previous_value": change.previous_value,
        "rationale": change.rationale,
    }


def _plan_record(plan: AdaptiveRegressionPlan) -> dict[str, object]:
    return {
        "changes": [
            _change_record(change)
            for change in plan.changes
        ],
        "impact": plan.impact.value,
        "rationale": plan.rationale,
        "requirements": [
            requirement.value
            for requirement in plan.requirements
        ],
        "scope": plan.scope.value,
    }


def changes_digest(changes: tuple[HostChange, ...]) -> str:
    """Return the deterministic digest for an ordered change set."""
    return _sha256(
        [_change_record(change) for change in changes],
    )


def plan_digest(plan: AdaptiveRegressionPlan) -> str:
    """Return the deterministic digest for an adaptive regression plan."""
    return _sha256(_plan_record(plan))


@dataclass(frozen=True, slots=True)
class HostEvidenceBinding:
    """
    Immutable identity of the host context used for qualification.

    host_fingerprint_digest is intentionally supplied by the host
    qualification layer rather than reconstructed here.
    """

    host_fingerprint_digest: str

    def __post_init__(self) -> None:
        if not self._valid_digest(self.host_fingerprint_digest):
            raise ValueError(
                "host_fingerprint_digest must be a SHA-256 digest",
            )

    @staticmethod
    def _valid_digest(value: str) -> bool:
        if len(value) != 64:
            return False

        try:
            int(value, 16)
        except ValueError:
            return False

        return True


@dataclass(frozen=True, slots=True)
class EvidenceProvenance:
    """
    Immutable qualification-evidence provenance record.

    This record establishes integrity/binding only. It does not establish
    signer authenticity and it cannot authorize, execute, or enforce work.
    """

    host_fingerprint_digest: str
    changes_digest: str
    regression_plan_digest: str
    validation_requirements: tuple[ValidationRequirement, ...]
    evidence_id: str

    def __post_init__(self) -> None:
        for name, value in (
            ("host_fingerprint_digest", self.host_fingerprint_digest),
            ("changes_digest", self.changes_digest),
            ("regression_plan_digest", self.regression_plan_digest),
            ("evidence_id", self.evidence_id),
        ):
            if not HostEvidenceBinding._valid_digest(value):
                raise ValueError(
                    f"{name} must be a SHA-256 digest",
                )

        if not self.validation_requirements:
            raise ValueError(
                "validation_requirements must not be empty",
            )

        if len(set(self.validation_requirements)) != len(
            self.validation_requirements,
        ):
            raise ValueError(
                "validation_requirements must not contain duplicates",
            )


@dataclass(frozen=True, slots=True)
class EvidenceBinding:
    """
    Immutable binding between a regression plan and qualification evidence.
    """

    host: HostEvidenceBinding
    plan: AdaptiveRegressionPlan
    provenance: EvidenceProvenance

    @property
    def expected_changes_digest(self) -> str:
        return changes_digest(self.plan.changes)

    @property
    def expected_plan_digest(self) -> str:
        return plan_digest(self.plan)

    @property
    def expected_evidence_id(self) -> str:
        return _sha256(
            {
                "changes_digest": self.expected_changes_digest,
                "host_fingerprint_digest": (
                    self.host.host_fingerprint_digest
                ),
                "plan_digest": self.expected_plan_digest,
                "requirements": [
                    requirement.value
                    for requirement in self.plan.requirements
                ],
            },
        )


class EvidenceProvenanceValidator:
    """
    Fail-closed validator for adaptive regression evidence provenance.

    Boundary:
      - no execution
      - no authorization
      - no enforcement
      - no host mutation
    """

    def validate(
        self,
        binding: EvidenceBinding,
    ) -> EvidenceIntegrityStatus:
        if not isinstance(binding, EvidenceBinding):
            raise EvidenceProvenanceError(
                "binding must be an EvidenceBinding",
            )

        self._validate_host(binding)
        self._validate_changes(binding)
        self._validate_plan(binding)
        self._validate_requirements(binding)
        self._validate_evidence_identity(binding)
        self._validate_boundary(binding)

        return EvidenceIntegrityStatus.VALID

    @staticmethod
    def _validate_host(binding: EvidenceBinding) -> None:
        if (
            binding.provenance.host_fingerprint_digest
            != binding.host.host_fingerprint_digest
        ):
            raise EvidenceProvenanceError(
                "evidence is bound to a different host fingerprint",
            )

    @staticmethod
    def _validate_changes(binding: EvidenceBinding) -> None:
        expected = binding.expected_changes_digest

        if binding.provenance.changes_digest != expected:
            raise EvidenceProvenanceError(
                "evidence is bound to a different change set",
            )

    @staticmethod
    def _validate_plan(binding: EvidenceBinding) -> None:
        expected = binding.expected_plan_digest

        if binding.provenance.regression_plan_digest != expected:
            raise EvidenceProvenanceError(
                "evidence is bound to a different regression plan",
            )

    @staticmethod
    def _validate_requirements(binding: EvidenceBinding) -> None:
        expected = tuple(binding.plan.requirements)
        actual = tuple(binding.provenance.validation_requirements)

        if actual != expected:
            raise EvidenceProvenanceError(
                "evidence requirements do not match the regression plan",
            )

    @staticmethod
    def _validate_evidence_identity(
        binding: EvidenceBinding,
    ) -> None:
        if binding.provenance.evidence_id != binding.expected_evidence_id:
            raise EvidenceProvenanceError(
                "evidence identity digest does not match its inputs",
            )

    @staticmethod
    def _validate_boundary(binding: EvidenceBinding) -> None:
        provenance = binding.provenance

        if hasattr(provenance, "execution_authorized"):
            raise EvidenceProvenanceError(
                "evidence provenance must not expose execution authorization",
            )

        if hasattr(provenance, "enforcement_verified"):
            raise EvidenceProvenanceError(
                "evidence provenance must not expose enforcement verification",
            )

    @classmethod
    def is_valid(
        cls,
        binding: EvidenceBinding,
    ) -> bool:
        try:
            cls().validate(binding)
        except (
            EvidenceProvenanceError,
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
        ):
            return False

        return True


def create_provenance(
    *,
    host_fingerprint_digest: str,
    plan: AdaptiveRegressionPlan,
) -> EvidenceProvenance:
    """
    Construct deterministic provenance for a validated host/plan context.

    This function does not execute validation and does not authorize
    execution.
    """
    host = HostEvidenceBinding(
        host_fingerprint_digest=host_fingerprint_digest,
    )

    temporary = EvidenceBinding(
        host=host,
        plan=plan,
        provenance=EvidenceProvenance(
            host_fingerprint_digest=host.host_fingerprint_digest,
            changes_digest=changes_digest(plan.changes),
            regression_plan_digest=plan_digest(plan),
            validation_requirements=tuple(plan.requirements),
            evidence_id=(
                "0" * 64
            ),
        ),
    )

    return EvidenceProvenance(
        host_fingerprint_digest=host.host_fingerprint_digest,
        changes_digest=temporary.expected_changes_digest,
        regression_plan_digest=temporary.expected_plan_digest,
        validation_requirements=tuple(plan.requirements),
        evidence_id=temporary.expected_evidence_id,
    )


__all__ = [
    "EvidenceBinding",
    "EvidenceIntegrityStatus",
    "EvidenceProvenance",
    "EvidenceProvenanceError",
    "EvidenceProvenanceValidator",
    "HostEvidenceBinding",
    "changes_digest",
    "create_provenance",
    "plan_digest",
]
