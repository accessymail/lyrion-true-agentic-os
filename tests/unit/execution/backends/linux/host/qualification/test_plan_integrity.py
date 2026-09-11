from __future__ import annotations

from dataclasses import replace

import pytest

from lyrion.execution.backends.linux.host.qualification.change_contracts import (
    ChangeImpact,
    HostChange,
    ValidationScope,
)
from lyrion.execution.backends.linux.host.qualification.plan_integrity import (
    AdaptiveRegressionPlanIntegrity,
    PlanIntegrityStatus,
    RegressionPlanIntegrityError,
)
from lyrion.execution.backends.linux.host.qualification.regression_scope import (
    AdaptiveRegressionPlan,
    AdaptiveRegressionScopeMapper,
    ValidationRequirement,
)


def _change(
    component: str,
    impact: ChangeImpact,
) -> HostChange:
    return HostChange(
        component=component,
        previous_value="before",
        current_value="after",
        impact=impact,
        rationale="Controlled R5.4 adversarial validation change.",
    )


def _plan(
    impact: ChangeImpact,
) -> AdaptiveRegressionPlan:
    return AdaptiveRegressionScopeMapper().create_plan(
        changes=(_change(f"component-{impact.value}", impact),),
    )


def test_valid_low_plan_passes() -> None:
    plan = _plan(ChangeImpact.LOW)

    assert (
        AdaptiveRegressionPlanIntegrity().validate(plan)
        is PlanIntegrityStatus.VALID
    )


def test_valid_medium_plan_passes() -> None:
    plan = _plan(ChangeImpact.MEDIUM)

    assert (
        AdaptiveRegressionPlanIntegrity().validate(plan)
        is PlanIntegrityStatus.VALID
    )


def test_valid_high_plan_passes() -> None:
    plan = _plan(ChangeImpact.HIGH)

    assert (
        AdaptiveRegressionPlanIntegrity().validate(plan)
        is PlanIntegrityStatus.VALID
    )


def test_valid_critical_plan_passes() -> None:
    plan = _plan(ChangeImpact.CRITICAL)

    assert (
        AdaptiveRegressionPlanIntegrity().validate(plan)
        is PlanIntegrityStatus.VALID
    )


def test_empty_requirements_fail_closed() -> None:
    class MalformedPlan:
        impact = ChangeImpact.HIGH
        scope = ValidationScope.NATIVE_SECURITY_QUALIFICATION
        requirements = ()
        changes = ()
        rationale = "controlled malformed plan"

    malformed = MalformedPlan()

    with pytest.raises(RegressionPlanIntegrityError):
        AdaptiveRegressionPlanIntegrity().validate(
            malformed,  # type: ignore[arg-type]
        )

    assert AdaptiveRegressionPlanIntegrity.is_valid(
        malformed,  # type: ignore[arg-type]
    ) is False


def test_missing_security_requirement_fails_closed() -> None:
    plan = _plan(ChangeImpact.HIGH)

    tampered = replace(
        plan,
        requirements=(
            ValidationRequirement.HOST_SMOKE,
            ValidationRequirement.AFFECTED_SUBSYSTEM_REGRESSION,
        ),
    )

    with pytest.raises(RegressionPlanIntegrityError):
        AdaptiveRegressionPlanIntegrity().validate(tampered)


def test_missing_full_host_requirement_fails_closed() -> None:
    plan = _plan(ChangeImpact.CRITICAL)

    tampered = replace(
        plan,
        requirements=(
            ValidationRequirement.HOST_SMOKE,
            ValidationRequirement.AFFECTED_SUBSYSTEM_REGRESSION,
            ValidationRequirement.SECURITY_PRIMITIVE_QUALIFICATION,
        ),
    )

    with pytest.raises(RegressionPlanIntegrityError):
        AdaptiveRegressionPlanIntegrity().validate(tampered)


def test_critical_plan_cannot_be_downgraded_to_smoke() -> None:
    plan = _plan(ChangeImpact.CRITICAL)

    tampered = replace(
        plan,
        scope=ValidationScope.SMOKE,
        requirements=(
            ValidationRequirement.HOST_SMOKE,
        ),
    )

    with pytest.raises(RegressionPlanIntegrityError):
        AdaptiveRegressionPlanIntegrity().validate(tampered)


def test_high_plan_cannot_be_downgraded_to_targeted() -> None:
    plan = _plan(ChangeImpact.HIGH)

    tampered = replace(
        plan,
        scope=ValidationScope.TARGETED_REGRESSION,
        requirements=(
            ValidationRequirement.HOST_SMOKE,
            ValidationRequirement.AFFECTED_SUBSYSTEM_REGRESSION,
        ),
    )

    with pytest.raises(RegressionPlanIntegrityError):
        AdaptiveRegressionPlanIntegrity().validate(tampered)


def test_duplicate_requirements_fail_closed() -> None:
    plan = _plan(ChangeImpact.HIGH)

    tampered = replace(
        plan,
        requirements=(
            ValidationRequirement.HOST_SMOKE,
            ValidationRequirement.HOST_SMOKE,
            ValidationRequirement.AFFECTED_SUBSYSTEM_REGRESSION,
            ValidationRequirement.SECURITY_PRIMITIVE_QUALIFICATION,
        ),
    )

    with pytest.raises(RegressionPlanIntegrityError):
        AdaptiveRegressionPlanIntegrity().validate(tampered)


def test_unsorted_changes_fail_closed() -> None:
    first = _change("z-component", ChangeImpact.HIGH)
    second = _change("a-component", ChangeImpact.HIGH)

    plan = _plan(ChangeImpact.HIGH)

    tampered = replace(
        plan,
        changes=(first, second),
    )

    with pytest.raises(RegressionPlanIntegrityError):
        AdaptiveRegressionPlanIntegrity().validate(tampered)


def test_sorted_changes_pass() -> None:
    first = _change("a-component", ChangeImpact.HIGH)
    second = _change("z-component", ChangeImpact.HIGH)

    plan = _plan(ChangeImpact.HIGH)

    tampered = replace(
        plan,
        changes=(first, second),
    )

    assert (
        AdaptiveRegressionPlanIntegrity().validate(tampered)
        is PlanIntegrityStatus.VALID
    )


def test_blank_rationale_fails_closed() -> None:
    class MalformedPlan:
        impact = ChangeImpact.MEDIUM
        scope = ValidationScope.TARGETED_REGRESSION
        requirements = (
            ValidationRequirement.HOST_SMOKE,
            ValidationRequirement.AFFECTED_SUBSYSTEM_REGRESSION,
        )
        changes = ()
        rationale = "   "

    malformed = MalformedPlan()

    with pytest.raises(RegressionPlanIntegrityError):
        AdaptiveRegressionPlanIntegrity().validate(
            malformed,  # type: ignore[arg-type]
        )


def test_authorization_attribute_fails_closed() -> None:
    class TamperedPlan:
        execution_authorized = True

    with pytest.raises(RegressionPlanIntegrityError):
        AdaptiveRegressionPlanIntegrity().validate(
            TamperedPlan(),  # type: ignore[arg-type]
        )


def test_enforcement_attribute_fails_closed() -> None:
    class TamperedPlan:
        enforcement_verified = True

    with pytest.raises(RegressionPlanIntegrityError):
        AdaptiveRegressionPlanIntegrity().validate(
            TamperedPlan(),  # type: ignore[arg-type]
        )


def test_non_plan_input_fails_closed() -> None:
    with pytest.raises(RegressionPlanIntegrityError):
        AdaptiveRegressionPlanIntegrity().validate(
            object(),  # type: ignore[arg-type]
        )


def test_is_valid_returns_false_for_invalid_plan() -> None:
    plan = _plan(ChangeImpact.CRITICAL)

    tampered = replace(
        plan,
        requirements=(
            ValidationRequirement.HOST_SMOKE,
        ),
    )

    assert AdaptiveRegressionPlanIntegrity.is_valid(tampered) is False


def test_is_valid_returns_true_for_valid_plan() -> None:
    assert AdaptiveRegressionPlanIntegrity.is_valid(
        _plan(ChangeImpact.CRITICAL),
    )


def test_integrity_validator_has_no_execution_authority() -> None:
    validator = AdaptiveRegressionPlanIntegrity()

    assert not hasattr(validator, "execute")
    assert not hasattr(validator, "authorize")
    assert not hasattr(validator, "apply_enforcement")


def test_integrity_validation_does_not_mutate_plan() -> None:
    plan = _plan(ChangeImpact.HIGH)
    before = plan

    AdaptiveRegressionPlanIntegrity().validate(plan)

    assert plan == before
