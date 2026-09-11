from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from lyrion.execution.backends.linux.host.qualification.change_contracts import (
    ChangeImpact,
    HostChange,
    ValidationScope,
)
from lyrion.execution.backends.linux.host.qualification.change_engine import (
    ChangeAwareRegressionPlanner,
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
        rationale="Controlled R5 validation change.",
    )


def test_no_changes_selects_low_smoke_scope() -> None:
    result = ChangeAwareRegressionPlanner().classify(changes=())

    assert result.impact is ChangeImpact.LOW
    assert result.validation.scope is ValidationScope.SMOKE
    assert result.changes == ()


@pytest.mark.parametrize(
    ("impact", "scope"),
    (
        (ChangeImpact.LOW, ValidationScope.SMOKE),
        (
            ChangeImpact.MEDIUM,
            ValidationScope.TARGETED_REGRESSION,
        ),
        (
            ChangeImpact.HIGH,
            ValidationScope.NATIVE_SECURITY_QUALIFICATION,
        ),
        (
            ChangeImpact.CRITICAL,
            ValidationScope.FULL_HOST_QUALIFICATION,
        ),
    ),
)
def test_each_impact_maps_to_deterministic_scope(
    impact: ChangeImpact,
    scope: ValidationScope,
) -> None:
    result = ChangeAwareRegressionPlanner().classify(
        changes=(_change("component-a", impact),),
    )

    assert result.impact is impact
    assert result.validation.scope is scope


def test_highest_impact_dominates() -> None:
    result = ChangeAwareRegressionPlanner().classify(
        changes=(
            _change("package-a", ChangeImpact.LOW),
            _change("runtime-a", ChangeImpact.MEDIUM),
            _change("seccomp", ChangeImpact.HIGH),
        ),
    )

    assert result.impact is ChangeImpact.HIGH
    assert result.validation.scope is (
        ValidationScope.NATIVE_SECURITY_QUALIFICATION
    )


def test_critical_change_dominates_all_lower_impacts() -> None:
    result = ChangeAwareRegressionPlanner().classify(
        changes=(
            _change("package-a", ChangeImpact.LOW),
            _change("runtime-a", ChangeImpact.MEDIUM),
            _change("security-a", ChangeImpact.HIGH),
            _change("kernel-a", ChangeImpact.CRITICAL),
        ),
    )

    assert result.impact is ChangeImpact.CRITICAL
    assert result.validation.scope is ValidationScope.FULL_HOST_QUALIFICATION


def test_changes_are_deterministically_ordered() -> None:
    planner = ChangeAwareRegressionPlanner()

    first = planner.classify(
        changes=(
            _change("z-component", ChangeImpact.LOW),
            _change("a-component", ChangeImpact.HIGH),
        ),
    )

    second = planner.classify(
        changes=(
            _change("a-component", ChangeImpact.HIGH),
            _change("z-component", ChangeImpact.LOW),
        ),
    )

    assert first == second
    assert tuple(
        change.component for change in first.changes
    ) == (
        "a-component",
        "z-component",
    )


def test_empty_changes_do_not_trigger_security_qualification() -> None:
    result = ChangeAwareRegressionPlanner().classify(changes=())

    assert result.requires_native_security_qualification is False
    assert result.requires_full_host_qualification is False


def test_high_change_requires_native_security_qualification() -> None:
    result = ChangeAwareRegressionPlanner().classify(
        changes=(_change("landlock", ChangeImpact.HIGH),),
    )

    assert result.requires_native_security_qualification is True
    assert result.requires_full_host_qualification is False


def test_critical_change_requires_full_host_qualification() -> None:
    result = ChangeAwareRegressionPlanner().classify(
        changes=(_change("kernel", ChangeImpact.CRITICAL),),
    )

    assert result.requires_native_security_qualification is True
    assert result.requires_full_host_qualification is True


def test_change_contract_is_immutable() -> None:
    change = _change("kernel", ChangeImpact.CRITICAL)

    with pytest.raises(FrozenInstanceError):
        change.component = "modified"  # type: ignore[misc]


def test_planner_is_observational_only() -> None:
    change = _change("seccomp", ChangeImpact.HIGH)

    before = change

    result = ChangeAwareRegressionPlanner().classify(
        changes=(change,),
    )

    assert change == before
    assert result.changes == (change,)


def test_planning_does_not_authorize_or_enforce() -> None:
    result = ChangeAwareRegressionPlanner().classify(
        changes=(_change("kernel", ChangeImpact.CRITICAL),),
    )

    assert not hasattr(result, "execution_authorized")
    assert not hasattr(result, "enforcement_verified")
