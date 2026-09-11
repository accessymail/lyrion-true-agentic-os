from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .change_contracts import (
    ChangeClassification,
    ChangeImpact,
    HostChange,
    ValidationScope,
)
from .change_engine import ChangeAwareRegressionPlanner


class ValidationRequirement(StrEnum):
    """
    LYRION-defined validation requirements.

    These values describe what validation must be performed. They are not
    claims about an external Linux, Debian, Ubuntu, or industry standard.
    """

    HOST_SMOKE = "host_smoke"
    AFFECTED_SUBSYSTEM_REGRESSION = "affected_subsystem_regression"
    SECURITY_PRIMITIVE_QUALIFICATION = "security_primitive_qualification"
    FULL_HOST_QUALIFICATION = "full_host_qualification"


@dataclass(frozen=True, slots=True)
class AdaptiveRegressionPlan:
    """
    Immutable, deterministic R5.3 regression-selection result.

    This is a planning artifact only. It does not execute validation,
    authorize execution, apply enforcement, or modify the host.
    """

    impact: ChangeImpact
    scope: ValidationScope
    requirements: tuple[ValidationRequirement, ...]
    changes: tuple[HostChange, ...]
    rationale: str

    def __post_init__(self) -> None:
        if not self.rationale.strip():
            raise ValueError("rationale must not be blank")

        if not self.requirements:
            raise ValueError("requirements must not be empty")


class AdaptiveRegressionScopeMapper:
    """
    Converts R5.1 change classification into an explicit R5.3 validation plan.

    The mapper is deterministic and observational.
    """

    _REQUIREMENTS_BY_SCOPE = {
        ValidationScope.SMOKE: (
            ValidationRequirement.HOST_SMOKE,
        ),
        ValidationScope.TARGETED_REGRESSION: (
            ValidationRequirement.HOST_SMOKE,
            ValidationRequirement.AFFECTED_SUBSYSTEM_REGRESSION,
        ),
        ValidationScope.NATIVE_SECURITY_QUALIFICATION: (
            ValidationRequirement.HOST_SMOKE,
            ValidationRequirement.AFFECTED_SUBSYSTEM_REGRESSION,
            ValidationRequirement.SECURITY_PRIMITIVE_QUALIFICATION,
        ),
        ValidationScope.FULL_HOST_QUALIFICATION: (
            ValidationRequirement.HOST_SMOKE,
            ValidationRequirement.AFFECTED_SUBSYSTEM_REGRESSION,
            ValidationRequirement.SECURITY_PRIMITIVE_QUALIFICATION,
            ValidationRequirement.FULL_HOST_QUALIFICATION,
        ),
    }

    def __init__(
        self,
        *,
        planner: ChangeAwareRegressionPlanner | None = None,
    ) -> None:
        self._planner = planner or ChangeAwareRegressionPlanner()

    def create_plan(
        self,
        *,
        changes: tuple[HostChange, ...],
    ) -> AdaptiveRegressionPlan:
        classification = self._planner.classify(changes=changes)
        return self.from_classification(classification)

    def from_classification(
        self,
        classification: ChangeClassification,
    ) -> AdaptiveRegressionPlan:
        scope = classification.validation.scope
        requirements = self._REQUIREMENTS_BY_SCOPE[scope]

        return AdaptiveRegressionPlan(
            impact=classification.impact,
            scope=scope,
            requirements=requirements,
            changes=classification.changes,
            rationale=(
                f"R5.3 selected {scope.value} from "
                f"{classification.impact.value} observed impact."
            ),
        )

    @staticmethod
    def planning_only(plan: AdaptiveRegressionPlan) -> bool:
        """
        Explicit architectural boundary assertion.

        A regression plan is never execution authorization or enforcement
        verification.
        """
        return (
            not hasattr(plan, "execution_authorized")
            and not hasattr(plan, "enforcement_verified")
        )
