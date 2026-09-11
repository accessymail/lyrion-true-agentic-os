"""R1.3.4-C C4 qualification freshness and invalidation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from lyrion.execution.backends.linux.host.contracts import (
    LinuxHostAbstractionSnapshot,
)
from lyrion.execution.backends.linux.host.negotiation.contracts import (
    CapabilityNegotiationResult,
)
from lyrion.execution.backends.linux.host.policy.contracts import (
    LinuxHostQualificationPolicy,
)

from .change_contracts import ChangeImpact, HostChange
from .evidence import (
    QUALIFICATION_RULES_VERSION,
    QualificationEvidence,
    host_fingerprint_digest,
)
from .integrity import QualificationBasis, qualification_basis_digest
from .regression_scope import AdaptiveRegressionPlan, AdaptiveRegressionScopeMapper
from .snapshot_diff import LinuxHostSnapshotDiff


class QualificationFreshness(StrEnum):
    """Current validity of an existing qualification evidence record."""

    FRESH = "fresh"
    STALE = "stale"


class QualificationInvalidationReason(StrEnum):
    """Why an existing qualification can no longer be treated as current."""

    HOST_BASIS_CHANGED = "host_basis_changed"
    POLICY_BASIS_CHANGED = "policy_basis_changed"
    REQUIREMENT_SET_CHANGED = "requirement_set_changed"
    CAPABILITY_EVALUATION_CHANGED = "capability_evaluation_changed"
    QUALIFICATION_RULES_CHANGED = "qualification_rules_changed"


@dataclass(frozen=True, slots=True)
class QualificationInvalidation:
    """Immutable record describing why qualification freshness was lost."""

    qualification_id: str
    previous_basis_digest: str
    current_basis_digest: str
    reason: QualificationInvalidationReason
    affected_components: tuple[str, ...]
    change_impact: ChangeImpact
    regression_plan: AdaptiveRegressionPlan | None

    def __post_init__(self) -> None:
        if not self.qualification_id.strip():
            raise ValueError("qualification_id must not be blank")

        for name, value in (
            ("previous_basis_digest", self.previous_basis_digest),
            ("current_basis_digest", self.current_basis_digest),
        ):
            if len(value) != 64:
                raise ValueError(f"{name} must be a SHA-256 digest")

            try:
                int(value, 16)
            except ValueError as exc:
                raise ValueError(
                    f"{name} must be hexadecimal",
                ) from exc

        if not self.affected_components:
            raise ValueError("affected_components must not be empty")

        if tuple(sorted(self.affected_components)) != self.affected_components:
            raise ValueError(
                "affected_components must be deterministically sorted",
            )


@dataclass(frozen=True, slots=True)
class QualificationFreshnessResult:
    """Immutable C4 freshness evaluation result."""

    status: QualificationFreshness
    current_basis: QualificationBasis
    current_basis_digest: str
    changes: tuple[HostChange, ...]
    regression_plan: AdaptiveRegressionPlan | None
    invalidation: QualificationInvalidation | None

    @property
    def fresh(self) -> bool:
        return self.status is QualificationFreshness.FRESH

    @property
    def stale(self) -> bool:
        return self.status is QualificationFreshness.STALE


class QualificationFreshnessError(ValueError):
    """Raised when a freshness evaluation cannot be performed safely."""


class QualificationFreshnessEvaluator:
    """
    Deterministically evaluates whether qualification evidence remains fresh.

    Boundary:
      - no authorization
      - no execution
      - no enforcement
      - no host mutation
      - no policy mutation

    R5 supplies observed host changes and regression scope.
    C4 determines whether those changes affect the qualification basis.
    """

    def __init__(
        self,
        *,
        snapshot_diff: LinuxHostSnapshotDiff | None = None,
        regression_mapper: AdaptiveRegressionScopeMapper | None = None,
        current_qualification_rules_version: str = QUALIFICATION_RULES_VERSION,
    ) -> None:
        if not current_qualification_rules_version.strip():
            raise ValueError(
                "current_qualification_rules_version must not be blank",
            )

        self._snapshot_diff = snapshot_diff or LinuxHostSnapshotDiff()
        self._regression_mapper = (
            regression_mapper or AdaptiveRegressionScopeMapper()
        )
        self._current_qualification_rules_version = (
            current_qualification_rules_version
        )

    def evaluate(
        self,
        *,
        evidence: QualificationEvidence,
        previous_host_snapshot: LinuxHostAbstractionSnapshot,
        current_host_snapshot: LinuxHostAbstractionSnapshot,
        current_policy: LinuxHostQualificationPolicy,
        current_negotiation: CapabilityNegotiationResult,
    ) -> QualificationFreshnessResult:
        if (
            evidence.host_fingerprint_digest
            != host_fingerprint_digest(
                previous_host_snapshot.fingerprint,
            )
        ):
            raise QualificationFreshnessError(
                "evidence is not bound to the supplied previous host snapshot",
            )

        if current_negotiation.host_snapshot != current_host_snapshot:
            raise QualificationFreshnessError(
                "current negotiation is not bound to the supplied "
                "current host snapshot",
            )

        changes = self._snapshot_diff.diff(
            previous=previous_host_snapshot,
            current=current_host_snapshot,
        )

        current_basis = QualificationBasis(
            host_fingerprint_digest=host_fingerprint_digest(
                current_host_snapshot.fingerprint,
            ),
            policy_id=current_policy.policy_id,
            policy_version=current_policy.policy_version,
            requirement_set_id=current_negotiation.profile_id,
            capability_evaluation_digest=current_negotiation.evidence_digest,
            qualification_rules_version=(
                self._current_qualification_rules_version
            ),
        )

        current_digest = qualification_basis_digest(current_basis)

        if current_digest == evidence.basis_digest:
            return QualificationFreshnessResult(
                status=QualificationFreshness.FRESH,
                current_basis=current_basis,
                current_basis_digest=current_digest,
                changes=changes,
                regression_plan=None,
                invalidation=None,
            )

        reason, affected_components = self._classify_basis_change(
            evidence=evidence,
            current_basis=current_basis,
            changes=changes,
        )

        regression_plan = (
            self._regression_mapper.create_plan(changes=changes)
            if changes
            else None
        )

        change_impact = (
            regression_plan.impact
            if regression_plan is not None
            else ChangeImpact.LOW
        )

        invalidation = QualificationInvalidation(
            qualification_id=evidence.qualification_id,
            previous_basis_digest=evidence.basis_digest,
            current_basis_digest=current_digest,
            reason=reason,
            affected_components=tuple(sorted(affected_components)),
            change_impact=change_impact,
            regression_plan=regression_plan,
        )

        return QualificationFreshnessResult(
            status=QualificationFreshness.STALE,
            current_basis=current_basis,
            current_basis_digest=current_digest,
            changes=changes,
            regression_plan=regression_plan,
            invalidation=invalidation,
        )

    @staticmethod
    def _classify_basis_change(
        *,
        evidence: QualificationEvidence,
        current_basis: QualificationBasis,
        changes: tuple[HostChange, ...],
    ) -> tuple[
        QualificationInvalidationReason,
        tuple[str, ...],
    ]:
        if (
            evidence.basis.host_fingerprint_digest
            != current_basis.host_fingerprint_digest
        ):
            return (
                QualificationInvalidationReason.HOST_BASIS_CHANGED,
                tuple(
                    change.component
                    for change in changes
                    if change.component.startswith(
                        (
                            "host.identity.",
                            "host.primitive.",
                        )
                    )
                )
                or ("host.fingerprint",),
            )

        if evidence.basis.policy_id != current_basis.policy_id:
            return (
                QualificationInvalidationReason.POLICY_BASIS_CHANGED,
                ("policy.id",),
            )

        if evidence.basis.policy_version != current_basis.policy_version:
            return (
                QualificationInvalidationReason.POLICY_BASIS_CHANGED,
                ("policy.version",),
            )

        if evidence.basis.requirement_set_id != current_basis.requirement_set_id:
            return (
                QualificationInvalidationReason.REQUIREMENT_SET_CHANGED,
                ("requirement_set.id",),
            )

        if (
            evidence.basis.capability_evaluation_digest
            != current_basis.capability_evaluation_digest
        ):
            return (
                QualificationInvalidationReason.CAPABILITY_EVALUATION_CHANGED,
                ("capability_evaluation.digest",),
            )

        if (
            evidence.basis.qualification_rules_version
            != current_basis.qualification_rules_version
        ):
            return (
                QualificationInvalidationReason.QUALIFICATION_RULES_CHANGED,
                ("qualification_rules.version",),
            )

        raise QualificationFreshnessError(
            "basis digest changed without a classified basis difference",
        )


__all__ = [
    "QualificationFreshness",
    "QualificationFreshnessError",
    "QualificationFreshnessEvaluator",
    "QualificationFreshnessResult",
    "QualificationInvalidation",
    "QualificationInvalidationReason",
]
