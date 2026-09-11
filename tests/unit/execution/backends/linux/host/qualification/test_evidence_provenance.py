from __future__ import annotations

from dataclasses import replace

import pytest

from lyrion.execution.backends.linux.host.qualification.change_contracts import (
    ChangeImpact,
    HostChange,
)
from lyrion.execution.backends.linux.host.qualification.evidence_provenance import (
    EvidenceBinding,
    EvidenceIntegrityStatus,
    EvidenceProvenanceError,
    EvidenceProvenanceValidator,
    HostEvidenceBinding,
    changes_digest,
    create_provenance,
    plan_digest,
)
from lyrion.execution.backends.linux.host.qualification.regression_scope import (
    AdaptiveRegressionPlan,
    AdaptiveRegressionScopeMapper,
    ValidationRequirement,
)

HOST_A = "a" * 64
HOST_B = "b" * 64


def _change(
    component: str,
    impact: ChangeImpact = ChangeImpact.HIGH,
) -> HostChange:
    return HostChange(
        component=component,
        previous_value="before",
        current_value="after",
        impact=impact,
        rationale="Controlled R5.5 provenance validation change.",
    )


def _plan(
    changes: tuple[HostChange, ...] | None = None,
) -> AdaptiveRegressionPlan:
    if changes is None:
        changes = (_change("component-a"),)

    return AdaptiveRegressionScopeMapper().create_plan(
        changes=changes,
    )


def _binding(
    host_digest: str = HOST_A,
    plan: AdaptiveRegressionPlan | None = None,
) -> EvidenceBinding:
    if plan is None:
        plan = _plan()

    host = HostEvidenceBinding(
        host_fingerprint_digest=host_digest,
    )

    provenance = create_provenance(
        host_fingerprint_digest=host_digest,
        plan=plan,
    )

    return EvidenceBinding(
        host=host,
        plan=plan,
        provenance=provenance,
    )


def test_valid_provenance_passes() -> None:
    binding = _binding()

    assert (
        EvidenceProvenanceValidator().validate(binding)
        is EvidenceIntegrityStatus.VALID
    )


def test_valid_provenance_is_deterministic() -> None:
    first = _binding()
    second = _binding()

    assert first.provenance == second.provenance
    assert first.provenance.evidence_id == second.provenance.evidence_id


def test_plan_digest_is_deterministic() -> None:
    plan = _plan()

    assert plan_digest(plan) == plan_digest(plan)


def test_change_digest_is_deterministic() -> None:
    changes = (_change("component-a"),)

    assert changes_digest(changes) == changes_digest(changes)


def test_different_host_is_rejected() -> None:
    binding = _binding(HOST_A)

    tampered = replace(
        binding.provenance,
        host_fingerprint_digest=HOST_B,
    )

    binding = replace(binding, provenance=tampered)

    with pytest.raises(EvidenceProvenanceError):
        EvidenceProvenanceValidator().validate(binding)


def test_different_change_set_is_rejected() -> None:
    binding = _binding()

    tampered = replace(
        binding.provenance,
        changes_digest="c" * 64,
    )

    binding = replace(binding, provenance=tampered)

    with pytest.raises(EvidenceProvenanceError):
        EvidenceProvenanceValidator().validate(binding)


def test_different_plan_is_rejected() -> None:
    binding = _binding()

    tampered = replace(
        binding.provenance,
        regression_plan_digest="d" * 64,
    )

    binding = replace(binding, provenance=tampered)

    with pytest.raises(EvidenceProvenanceError):
        EvidenceProvenanceValidator().validate(binding)


def test_missing_requirement_is_rejected() -> None:
    binding = _binding()

    tampered = replace(
        binding.provenance,
        validation_requirements=(
            ValidationRequirement.HOST_SMOKE,
        ),
    )

    binding = replace(binding, provenance=tampered)

    with pytest.raises(EvidenceProvenanceError):
        EvidenceProvenanceValidator().validate(binding)


def test_requirement_reordering_is_rejected() -> None:
    plan = _plan()

    if len(plan.requirements) < 2:
        pytest.fail("R5.5 test requires multiple plan requirements")

    binding = _binding(plan=plan)

    tampered = replace(
        binding.provenance,
        validation_requirements=tuple(
            reversed(binding.provenance.validation_requirements),
        ),
    )

    binding = replace(binding, provenance=tampered)

    with pytest.raises(EvidenceProvenanceError):
        EvidenceProvenanceValidator().validate(binding)


def test_evidence_identity_tampering_is_rejected() -> None:
    binding = _binding()

    tampered = replace(
        binding.provenance,
        evidence_id="e" * 64,
    )

    binding = replace(binding, provenance=tampered)

    with pytest.raises(EvidenceProvenanceError):
        EvidenceProvenanceValidator().validate(binding)


def test_plan_change_after_provenance_creation_is_rejected() -> None:
    original = _plan()
    binding = _binding(plan=original)

    changed_plan = _plan(
        changes=(
            _change("component-different"),
        ),
    )

    tampered = replace(binding, plan=changed_plan)

    with pytest.raises(EvidenceProvenanceError):
        EvidenceProvenanceValidator().validate(tampered)


def test_cross_plan_evidence_reuse_is_rejected() -> None:
    plan_a = _plan(
        changes=(_change("component-a"),),
    )
    plan_b = _plan(
        changes=(_change("component-b"),),
    )

    binding_a = _binding(plan=plan_a)

    tampered = replace(binding_a, plan=plan_b)

    with pytest.raises(EvidenceProvenanceError):
        EvidenceProvenanceValidator().validate(tampered)


def test_cross_host_evidence_reuse_is_rejected() -> None:
    binding_a = _binding(HOST_A)

    tampered_host = HostEvidenceBinding(
        host_fingerprint_digest=HOST_B,
    )

    tampered = replace(
        binding_a,
        host=tampered_host,
    )

    with pytest.raises(EvidenceProvenanceError):
        EvidenceProvenanceValidator().validate(tampered)


def test_invalid_host_digest_is_rejected() -> None:
    with pytest.raises(ValueError):
        HostEvidenceBinding("not-a-digest")


def test_invalid_digest_length_is_rejected() -> None:
    with pytest.raises(ValueError):
        HostEvidenceBinding("a" * 63)


def test_invalid_digest_character_is_rejected() -> None:
    with pytest.raises(ValueError):
        HostEvidenceBinding("g" * 64)


def test_duplicate_requirements_are_rejected() -> None:
    plan = _plan()

    with pytest.raises(ValueError):
        replace(
            create_provenance(
                host_fingerprint_digest=HOST_A,
                plan=plan,
            ),
            validation_requirements=(
                ValidationRequirement.HOST_SMOKE,
                ValidationRequirement.HOST_SMOKE,
            ),
        )


def test_provenance_is_immutable() -> None:
    binding = _binding()

    with pytest.raises(AttributeError):
        binding.provenance.evidence_id = "f" * 64  # type: ignore[misc]


def test_validator_is_planning_only() -> None:
    validator = EvidenceProvenanceValidator()

    assert not hasattr(validator, "execute")
    assert not hasattr(validator, "authorize")
    assert not hasattr(validator, "apply_enforcement")


def test_provenance_has_no_authorization_boundary() -> None:
    provenance = create_provenance(
        host_fingerprint_digest=HOST_A,
        plan=_plan(),
    )

    assert not hasattr(provenance, "execution_authorized")
    assert not hasattr(provenance, "enforcement_verified")


def test_is_valid_returns_false_for_tampering() -> None:
    binding = _binding()

    tampered = replace(
        binding.provenance,
        evidence_id="f" * 64,
    )

    binding = replace(binding, provenance=tampered)

    assert EvidenceProvenanceValidator.is_valid(binding) is False


def test_is_valid_returns_true_for_valid_binding() -> None:
    assert EvidenceProvenanceValidator.is_valid(_binding())


def test_empty_changes_have_deterministic_digest() -> None:
    assert changes_digest(()) == changes_digest(())


def test_different_changes_have_different_digest() -> None:
    first = changes_digest((_change("component-a"),))
    second = changes_digest((_change("component-b"),))

    assert first != second
