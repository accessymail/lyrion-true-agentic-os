from __future__ import annotations

from .change_contracts import (
    ChangeClassification,
    ChangeImpact,
    HostChange,
    ValidationScope,
    ValidationSelection,
)


class ChangeAwareRegressionPlanner:
    """
    Deterministically maps observed host changes to a LYRION validation scope.

    This is a planning component only.

    It does NOT:
      - execute tests;
      - mutate the Linux host;
      - authorize execution;
      - apply enforcement;
      - alter system configuration.
    """

    _SCOPE_BY_IMPACT = {
        ChangeImpact.LOW: ValidationScope.SMOKE,
        ChangeImpact.MEDIUM: ValidationScope.TARGETED_REGRESSION,
        ChangeImpact.HIGH: ValidationScope.NATIVE_SECURITY_QUALIFICATION,
        ChangeImpact.CRITICAL: ValidationScope.FULL_HOST_QUALIFICATION,
    }

    def classify(
        self,
        *,
        changes: tuple[HostChange, ...],
    ) -> ChangeClassification:
        ordered_changes = tuple(
            sorted(
                changes,
                key=lambda change: (
                    change.component,
                    change.impact.value,
                    change.previous_value,
                    change.current_value,
                ),
            )
        )

        impact = self._highest_impact(ordered_changes)
        scope = self._SCOPE_BY_IMPACT[impact]

        rationale = self._rationale(impact, scope)

        validation = ValidationSelection(
            scope=scope,
            changes=ordered_changes,
            rationale=rationale,
        )

        return ChangeClassification(
            impact=impact,
            changes=ordered_changes,
            validation=validation,
        )

    @staticmethod
    def _highest_impact(
        changes: tuple[HostChange, ...],
    ) -> ChangeImpact:
        if not changes:
            return ChangeImpact.LOW

        priority = {
            ChangeImpact.LOW: 0,
            ChangeImpact.MEDIUM: 1,
            ChangeImpact.HIGH: 2,
            ChangeImpact.CRITICAL: 3,
        }

        return max(
            (change.impact for change in changes),
            key=priority.__getitem__,
        )

    @staticmethod
    def _rationale(
        impact: ChangeImpact,
        scope: ValidationScope,
    ) -> str:
        return (
            f"Highest observed LYRION change impact is "
            f"{impact.value}; selected validation scope is {scope.value}."
        )
