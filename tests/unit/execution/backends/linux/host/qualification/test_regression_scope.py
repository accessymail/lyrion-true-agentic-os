from __future__ import annotations

from lyrion.execution.backends.linux.host.qualification.change_contracts import (
    ChangeImpact,
    HostChange,
    ValidationScope,
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
        rationale="Controlled R5.3 validation change.",
    )


def test_low_change_selects_smoke_requirement() -> None:
    plan = AdaptiveRegressionScopeMapper().create_plan(
        changes=(_change("package", ChangeImpact.LOW),),
    )

    assert plan.impact is ChangeImpact.LOW
    assert plan.scope is ValidationScope.SMOKE
    assert plan.requirements == (
        ValidationRequirement.HOST_SMOKE,
    )


def test_medium_change_selects_targeted_regression_requirements() -> None:
    plan = AdaptiveRegressionScopeMapper().create_plan(
        changes=(_change("runtime", ChangeImpact.MEDIUM),),
    )

    assert plan.scope is ValidationScope.TARGETED_REGRESSION
    assert plan.requirements == (
        ValidationRequirement.HOST_SMOKE,
        ValidationRequirement.AFFECTED_SUBSYSTEM_REGRESSION,
    )


def test_high_change_selects_security_qualification() -> None:
    plan = AdaptiveRegressionScopeMapper().create_plan(
        changes=(_change("seccomp", ChangeImpact.HIGH),),
    )

    assert plan.scope is ValidationScope.NATIVE_SECURITY_QUALIFICATION
    assert plan.requirements == (
        ValidationRequirement.HOST_SMOKE,
        ValidationRequirement.AFFECTED_SUBSYSTEM_REGRESSION,
        ValidationRequirement.SECURITY_PRIMITIVE_QUALIFICATION,
    )


def test_critical_change_selects_full_host_qualification() -> None:
    plan = AdaptiveRegressionScopeMapper().create_plan(
        changes=(_change("architecture", ChangeImpact.CRITICAL),),
    )

    assert plan.scope is ValidationScope.FULL_HOST_QUALIFICATION
    assert plan.requirements == (
        ValidationRequirement.HOST_SMOKE,
        ValidationRequirement.AFFECTED_SUBSYSTEM_REGRESSION,
        ValidationRequirement.SECURITY_PRIMITIVE_QUALIFICATION,
        ValidationRequirement.FULL_HOST_QUALIFICATION,
    )


def test_highest_change_impact_controls_scope() -> None:
    plan = AdaptiveRegressionScopeMapper().create_plan(
        changes=(
            _change("package", ChangeImpact.LOW),
            _change("runtime", ChangeImpact.MEDIUM),
            _change("landlock", ChangeImpact.HIGH),
        ),
    )

    assert plan.impact is ChangeImpact.HIGH
    assert plan.scope is ValidationScope.NATIVE_SECURITY_QUALIFICATION


def test_critical_change_controls_scope_over_lower_changes() -> None:
    plan = AdaptiveRegressionScopeMapper().create_plan(
        changes=(
            _change("package", ChangeImpact.LOW),
            _change("seccomp", ChangeImpact.HIGH),
            _change("architecture", ChangeImpact.CRITICAL),
        ),
    )

    assert plan.impact is ChangeImpact.CRITICAL
    assert plan.scope is ValidationScope.FULL_HOST_QUALIFICATION


def test_no_changes_selects_safe_baseline_smoke() -> None:
    plan = AdaptiveRegressionScopeMapper().create_plan(
        changes=(),
    )

    assert plan.impact is ChangeImpact.LOW
    assert plan.scope is ValidationScope.SMOKE
    assert plan.requirements == (
        ValidationRequirement.HOST_SMOKE,
    )


def test_plan_preserves_deterministic_change_order() -> None:
    mapper = AdaptiveRegressionScopeMapper()

    first = mapper.create_plan(
        changes=(
            _change("z-component", ChangeImpact.LOW),
            _change("a-component", ChangeImpact.HIGH),
        ),
    )

    second = mapper.create_plan(
        changes=(
            _change("a-component", ChangeImpact.HIGH),
            _change("z-component", ChangeImpact.LOW),
        ),
    )

    assert first == second


def test_plan_preserves_changes() -> None:
    changes = (
        _change("kernel", ChangeImpact.HIGH),
        _change("landlock", ChangeImpact.HIGH),
    )

    plan = AdaptiveRegressionScopeMapper().create_plan(
        changes=changes,
    )

    assert plan.changes == tuple(
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


def test_plan_is_explicitly_planning_only() -> None:
    plan = AdaptiveRegressionScopeMapper().create_plan(
        changes=(_change("kernel", ChangeImpact.HIGH),),
    )

    assert AdaptiveRegressionScopeMapper.planning_only(plan) is True
    assert not hasattr(plan, "execution_authorized")
    assert not hasattr(plan, "enforcement_verified")


def test_plan_is_immutable() -> None:
    plan = AdaptiveRegressionScopeMapper().create_plan(
        changes=(_change("kernel", ChangeImpact.HIGH),),
    )

    try:
        plan.scope = ValidationScope.SMOKE  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        raise AssertionError("AdaptiveRegressionPlan must be immutable")


def test_all_scopes_have_requirements() -> None:
    mapper = AdaptiveRegressionScopeMapper()

    for impact in ChangeImpact:
        plan = mapper.create_plan(
            changes=(_change(f"component-{impact.value}", impact),),
        )

        assert plan.requirements
        assert all(
            isinstance(
                requirement,
                ValidationRequirement,
            )
            for requirement in plan.requirements
        )


def test_security_scope_contains_security_requirement() -> None:
    plan = AdaptiveRegressionScopeMapper().create_plan(
        changes=(_change("apparmor", ChangeImpact.HIGH),),
    )

    assert (
        ValidationRequirement.SECURITY_PRIMITIVE_QUALIFICATION
        in plan.requirements
    )


def test_full_scope_contains_every_required_layer() -> None:
    plan = AdaptiveRegressionScopeMapper().create_plan(
        changes=(_change("os_version", ChangeImpact.CRITICAL),),
    )

    assert plan.requirements == (
        ValidationRequirement.HOST_SMOKE,
        ValidationRequirement.AFFECTED_SUBSYSTEM_REGRESSION,
        ValidationRequirement.SECURITY_PRIMITIVE_QUALIFICATION,
        ValidationRequirement.FULL_HOST_QUALIFICATION,
    )


def test_plan_is_dataclass_contract() -> None:
    plan = AdaptiveRegressionScopeMapper().create_plan(
        changes=(_change("kernel", ChangeImpact.HIGH),),
    )

    assert isinstance(plan, AdaptiveRegressionPlan)
