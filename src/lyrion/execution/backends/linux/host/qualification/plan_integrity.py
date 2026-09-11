from __future__ import annotations

from enum import StrEnum

from .change_contracts import ChangeImpact, ValidationScope
from .regression_scope import (
    AdaptiveRegressionPlan,
    ValidationRequirement,
)


class PlanIntegrityStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"


class RegressionPlanIntegrityError(ValueError):
    """Raised when an adaptive regression plan violates R5.4 invariants."""


class AdaptiveRegressionPlanIntegrity:
    """
    Fail-closed integrity validator for R5.3 AdaptiveRegressionPlan objects.

    This validator:
      - validates structure and policy invariants;
      - never executes validation;
      - never authorizes execution;
      - never applies enforcement;
      - never mutates the host.
    """

    _REQUIRED_BY_SCOPE = {
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

    _MINIMUM_SCOPE_BY_IMPACT = {
        ChangeImpact.LOW: ValidationScope.SMOKE,
        ChangeImpact.MEDIUM: ValidationScope.TARGETED_REGRESSION,
        ChangeImpact.HIGH: ValidationScope.NATIVE_SECURITY_QUALIFICATION,
        ChangeImpact.CRITICAL: ValidationScope.FULL_HOST_QUALIFICATION,
    }

    _SCOPE_ORDER = {
        ValidationScope.SMOKE: 0,
        ValidationScope.TARGETED_REGRESSION: 1,
        ValidationScope.NATIVE_SECURITY_QUALIFICATION: 2,
        ValidationScope.FULL_HOST_QUALIFICATION: 3,
    }

    def validate(
        self,
        plan: AdaptiveRegressionPlan,
    ) -> PlanIntegrityStatus:
        """
        Validate a plan and fail closed on any integrity violation.
        """
        self._validate_structure(plan)
        self._validate_impact_scope(plan)
        self._validate_requirements(plan)
        self._validate_changes(plan)
        self._validate_authorization_boundary(plan)

        return PlanIntegrityStatus.VALID

    def _validate_structure(
        self,
        plan: AdaptiveRegressionPlan,
    ) -> None:
        if not isinstance(plan, AdaptiveRegressionPlan):
            raise RegressionPlanIntegrityError(
                "plan must be an AdaptiveRegressionPlan",
            )

        if not isinstance(plan.impact, ChangeImpact):
            raise RegressionPlanIntegrityError(
                "plan impact is invalid",
            )

        if not isinstance(plan.scope, ValidationScope):
            raise RegressionPlanIntegrityError(
                "plan scope is invalid",
            )

        if not plan.rationale.strip():
            raise RegressionPlanIntegrityError(
                "plan rationale must not be blank",
            )

        if not plan.requirements:
            raise RegressionPlanIntegrityError(
                "plan requirements must not be empty",
            )

    def _validate_impact_scope(
        self,
        plan: AdaptiveRegressionPlan,
    ) -> None:
        minimum_scope = self._MINIMUM_SCOPE_BY_IMPACT[plan.impact]

        if (
            self._SCOPE_ORDER[plan.scope]
            < self._SCOPE_ORDER[minimum_scope]
        ):
            raise RegressionPlanIntegrityError(
                "plan scope is weaker than its change impact requires",
            )

    def _validate_requirements(
        self,
        plan: AdaptiveRegressionPlan,
    ) -> None:
        required = self._REQUIRED_BY_SCOPE[plan.scope]
        actual = tuple(plan.requirements)

        if len(set(actual)) != len(actual):
            raise RegressionPlanIntegrityError(
                "plan contains duplicate validation requirements",
            )

        missing = tuple(
            requirement
            for requirement in required
            if requirement not in actual
        )

        if missing:
            raise RegressionPlanIntegrityError(
                "plan is missing required validation requirements: "
                + ",".join(item.value for item in missing),
            )

    @staticmethod
    def _validate_changes(
        plan: AdaptiveRegressionPlan,
    ) -> None:
        previous_key: tuple[str, ...] | None = None

        for change in plan.changes:
            current_key = (
                change.component,
                change.impact.value,
                change.previous_value,
                change.current_value,
            )

            if previous_key is not None and current_key < previous_key:
                raise RegressionPlanIntegrityError(
                    "plan changes are not deterministically ordered",
                )

            previous_key = current_key

    @staticmethod
    def _validate_authorization_boundary(
        plan: AdaptiveRegressionPlan,
    ) -> None:
        if hasattr(plan, "execution_authorized"):
            raise RegressionPlanIntegrityError(
                "regression plan must never expose execution authorization",
            )

        if hasattr(plan, "enforcement_verified"):
            raise RegressionPlanIntegrityError(
                "regression plan must never expose enforcement verification",
            )

    @classmethod
    def is_valid(
        cls,
        plan: AdaptiveRegressionPlan,
    ) -> bool:
        """
        Convenience fail-closed predicate.

        Any integrity exception produces False.
        """
        try:
            cls().validate(plan)
        except (
            RegressionPlanIntegrityError,
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
        ):
            return False

        return True
