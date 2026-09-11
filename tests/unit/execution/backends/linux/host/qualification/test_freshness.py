"""R1.3.4-C C4 qualification freshness and invalidation tests."""

from __future__ import annotations

import dataclasses

import pytest

from lyrion.execution.backends.linux.host.contracts import (
    CapabilityState,
    HostPrimitive,
    HostPrimitiveCapability,
    LinuxHostAbstractionSnapshot,
    LinuxHostFingerprint,
    LinuxHostIdentity,
)
from lyrion.execution.backends.linux.host.negotiation.contracts import (
    CapabilityRequirement,
    CapabilityRequirementMode,
    CapabilityRequirementSet,
)
from lyrion.execution.backends.linux.host.negotiation.engine import (
    CapabilityNegotiationEngine,
)
from lyrion.execution.backends.linux.host.policy.contracts import (
    LinuxHostPolicyKey,
    LinuxHostQualificationPolicy,
)
from lyrion.execution.backends.linux.host.profiles.contracts import (
    LinuxArchitecture,
    LinuxDistribution,
)
from lyrion.execution.backends.linux.host.qualification.evidence import (
    QualificationEvidence,
)
from lyrion.execution.backends.linux.host.qualification.freshness import (
    QualificationFreshness,
    QualificationFreshnessError,
    QualificationFreshnessEvaluator,
    QualificationInvalidationReason,
)


def _snapshot(
    *,
    os_name: str = "Ubuntu",
    os_version: str = "26.04",
    kernel: str = "6.18.0",
    architecture: str = "x86_64",
    primitive_state: CapabilityState = CapabilityState.AVAILABLE,
    primitive_evidence: tuple[str, ...] = ("test",),
) -> LinuxHostAbstractionSnapshot:
    identity = LinuxHostIdentity(
        os_name=os_name,
        os_version=os_version,
        kernel=kernel,
        architecture=architecture,
        virtualization="vmware",
        init_system="systemd",
    )

    fingerprint = LinuxHostFingerprint(
        identity=identity,
        primitives=(
            HostPrimitiveCapability(
                primitive=HostPrimitive.CGROUPS_V2,
                state=primitive_state,
                evidence=primitive_evidence,
            ),
            HostPrimitiveCapability(
                primitive=HostPrimitive.NO_NEW_PRIVS,
                state=CapabilityState.AVAILABLE,
                evidence=("test",),
            ),
        ),
    )

    return LinuxHostAbstractionSnapshot(
        identity=identity,
        fingerprint=fingerprint,
        user_id=1000,
        effective_capabilities=(),
        namespaces=("pid", "mount"),
        notes=(),
    )


def _policy(
    *,
    version: str = "1",
    requirement_id: str = "c4-cgroups",
    primitive: HostPrimitive = HostPrimitive.CGROUPS_V2,
) -> LinuxHostQualificationPolicy:
    key = LinuxHostPolicyKey(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
    )

    requirements = CapabilityRequirementSet(
        requirements=(
            CapabilityRequirement(
                requirement_id=requirement_id,
                primitive=primitive,
                mode=CapabilityRequirementMode.REQUIRED,
                acceptable_states=(CapabilityState.AVAILABLE,),
                rationale="C4 freshness test.",
            ),
        ),
    )

    return LinuxHostQualificationPolicy(
        key=key,
        requirements=requirements,
        policy_id=key.policy_id,
        policy_version=version,
    )


def _negotiation(
    snapshot: LinuxHostAbstractionSnapshot,
    policy: LinuxHostQualificationPolicy,
):
    return CapabilityNegotiationEngine().negotiate(
        host_snapshot=snapshot,
        requirements=policy.requirements,
    )


def _evidence(
    snapshot: LinuxHostAbstractionSnapshot,
    policy: LinuxHostQualificationPolicy,
):
    negotiation = _negotiation(snapshot, policy)

    return QualificationEvidence.from_qualification(
        host_snapshot=snapshot,
        policy=policy,
        negotiation=negotiation,
        qualification_state="qualified",
    )


def _evaluate(
    *,
    evidence: QualificationEvidence,
    previous: LinuxHostAbstractionSnapshot,
    current: LinuxHostAbstractionSnapshot,
    policy: LinuxHostQualificationPolicy,
    negotiation=None,
    rules_version: str | None = None,
):
    evaluator = QualificationFreshnessEvaluator(
        current_qualification_rules_version=(
            rules_version
            if rules_version is not None
            else evidence.basis.qualification_rules_version
        ),
    )

    return evaluator.evaluate(
        evidence=evidence,
        previous_host_snapshot=previous,
        current_host_snapshot=current,
        current_policy=policy,
        current_negotiation=(
            negotiation
            if negotiation is not None
            else _negotiation(current, policy)
        ),
    )


def test_unchanged_basis_is_fresh() -> None:
    snapshot = _snapshot()
    policy = _policy()
    evidence = _evidence(snapshot, policy)

    result = _evaluate(
        evidence=evidence,
        previous=snapshot,
        current=snapshot,
        policy=policy,
    )

    assert result.status is QualificationFreshness.FRESH
    assert result.fresh is True
    assert result.stale is False
    assert result.current_basis_digest == evidence.basis_digest
    assert result.changes == ()
    assert result.regression_plan is None
    assert result.invalidation is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("kernel", "6.18.1"),
        ("os_name", "Debian"),
        ("os_version", "13"),
        ("architecture", "aarch64"),
    ],
)
def test_host_identity_change_invalidates_qualification(
    field: str,
    value: str,
) -> None:
    previous = _snapshot()
    policy = _policy()
    evidence = _evidence(previous, policy)

    current_kwargs = {field: value}
    current = _snapshot(**current_kwargs)

    result = _evaluate(
        evidence=evidence,
        previous=previous,
        current=current,
        policy=policy,
    )

    assert result.status is QualificationFreshness.STALE
    assert result.invalidation is not None
    assert (
        result.invalidation.reason
        is QualificationInvalidationReason.HOST_BASIS_CHANGED
    )
    assert result.regression_plan is not None
    assert result.regression_plan.changes == result.changes


def test_security_primitive_change_invalidates_qualification() -> None:
    previous = _snapshot(
        primitive_state=CapabilityState.AVAILABLE,
        primitive_evidence=("available",),
    )
    policy = _policy()
    evidence = _evidence(previous, policy)

    current = _snapshot(
        primitive_state=CapabilityState.UNAVAILABLE,
        primitive_evidence=("unavailable",),
    )

    result = _evaluate(
        evidence=evidence,
        previous=previous,
        current=current,
        policy=policy,
    )

    assert result.stale is True
    assert result.invalidation is not None
    assert (
        result.invalidation.reason
        is QualificationInvalidationReason.HOST_BASIS_CHANGED
    )
    assert result.regression_plan is not None
    assert result.regression_plan.impact.value == "high"


def test_policy_id_change_invalidates_without_r5_host_plan() -> None:
    snapshot = _snapshot()
    original_policy = _policy()

    evidence = _evidence(snapshot, original_policy)

    changed_key = dataclasses.replace(
        original_policy.key,
        architecture=LinuxArchitecture.AARCH64,
    )

    changed_policy = dataclasses.replace(
        original_policy,
        key=changed_key,
        policy_id=changed_key.policy_id,
    )

    # The policy identity changes through its deterministic policy key.
    # The host remains unchanged, so this is a policy-only invalidation.
    negotiation = _negotiation(snapshot, changed_policy)

    result = _evaluate(
        evidence=evidence,
        previous=snapshot,
        current=snapshot,
        policy=changed_policy,
        negotiation=negotiation,
    )

    assert result.stale is True
    assert result.changes == ()
    assert result.regression_plan is None
    assert result.invalidation is not None
    assert (
        result.invalidation.reason
        is QualificationInvalidationReason.POLICY_BASIS_CHANGED
    )
    assert result.invalidation.regression_plan is None
    assert result.invalidation.affected_components == ("policy.id",)


def test_policy_version_change_invalidates_without_r5_host_plan() -> None:
    snapshot = _snapshot()
    original_policy = _policy(version="1")
    evidence = _evidence(snapshot, original_policy)

    changed_policy = _policy(version="2")
    negotiation = _negotiation(snapshot, changed_policy)

    result = _evaluate(
        evidence=evidence,
        previous=snapshot,
        current=snapshot,
        policy=changed_policy,
        negotiation=negotiation,
    )

    assert result.stale is True
    assert result.changes == ()
    assert result.regression_plan is None
    assert result.invalidation is not None
    assert (
        result.invalidation.reason
        is QualificationInvalidationReason.POLICY_BASIS_CHANGED
    )
    assert result.invalidation.affected_components == ("policy.version",)


def test_requirement_set_change_invalidates() -> None:
    snapshot = _snapshot()
    original_policy = _policy(requirement_id="requirement-v1")
    evidence = _evidence(snapshot, original_policy)

    changed_policy = _policy(requirement_id="requirement-v2")
    negotiation = _negotiation(snapshot, changed_policy)

    result = _evaluate(
        evidence=evidence,
        previous=snapshot,
        current=snapshot,
        policy=original_policy,
        negotiation=negotiation,
    )

    assert result.stale is True
    assert result.changes == ()
    assert result.regression_plan is None
    assert result.invalidation is not None
    assert (
        result.invalidation.reason
        is QualificationInvalidationReason.REQUIREMENT_SET_CHANGED
    )
    assert result.invalidation.affected_components == (
        "requirement_set.id",
    )


def test_capability_evaluation_change_invalidates() -> None:
    snapshot = _snapshot()
    policy = _policy()
    evidence = _evidence(snapshot, policy)
    negotiation = _negotiation(snapshot, policy)

    changed_negotiation = dataclasses.replace(
        negotiation,
        evidence_digest="f" * 64,
    )

    result = _evaluate(
        evidence=evidence,
        previous=snapshot,
        current=snapshot,
        policy=policy,
        negotiation=changed_negotiation,
    )

    assert result.stale is True
    assert result.changes == ()
    assert result.regression_plan is None
    assert result.invalidation is not None
    assert (
        result.invalidation.reason
        is QualificationInvalidationReason.CAPABILITY_EVALUATION_CHANGED
    )
    assert result.invalidation.affected_components == (
        "capability_evaluation.digest",
    )


def test_qualification_rules_version_change_invalidates() -> None:
    snapshot = _snapshot()
    policy = _policy()
    evidence = _evidence(snapshot, policy)

    result = _evaluate(
        evidence=evidence,
        previous=snapshot,
        current=snapshot,
        policy=policy,
        rules_version="r1.3.4-c.v2",
    )

    assert result.stale is True
    assert result.changes == ()
    assert result.regression_plan is None
    assert result.invalidation is not None
    assert (
        result.invalidation.reason
        is QualificationInvalidationReason.QUALIFICATION_RULES_CHANGED
    )
    assert result.invalidation.affected_components == (
        "qualification_rules.version",
    )


def test_evidence_mismatch_with_previous_snapshot_fails_closed() -> None:
    snapshot = _snapshot()
    different_snapshot = _snapshot(kernel="6.19.0")
    policy = _policy()
    evidence = _evidence(snapshot, policy)

    with pytest.raises(QualificationFreshnessError):
        _evaluate(
            evidence=evidence,
            previous=different_snapshot,
            current=different_snapshot,
            policy=policy,
        )


def test_current_negotiation_must_be_bound_to_current_host() -> None:
    previous = _snapshot()
    current = _snapshot(kernel="6.18.1")
    policy = _policy()
    evidence = _evidence(previous, policy)

    stale_negotiation = _negotiation(previous, policy)

    evaluator = QualificationFreshnessEvaluator()

    # This assertion documents the C4 contract that must be enforced:
    # a capability evaluation from a different host snapshot cannot be
    # treated as evidence for the current host.
    with pytest.raises(QualificationFreshnessError):
        evaluator.evaluate(
            evidence=evidence,
            previous_host_snapshot=previous,
            current_host_snapshot=current,
            current_policy=policy,
            current_negotiation=stale_negotiation,
        )


def test_stale_invalidation_is_deterministic() -> None:
    previous = _snapshot()
    current = _snapshot(kernel="6.18.1")
    policy = _policy()
    evidence = _evidence(previous, policy)

    first = _evaluate(
        evidence=evidence,
        previous=previous,
        current=current,
        policy=policy,
    )
    second = _evaluate(
        evidence=evidence,
        previous=previous,
        current=current,
        policy=policy,
    )

    assert first == second
    assert first.invalidation == second.invalidation


def test_invalidation_is_immutable() -> None:
    previous = _snapshot()
    current = _snapshot(kernel="6.18.1")
    policy = _policy()
    evidence = _evidence(previous, policy)

    result = _evaluate(
        evidence=evidence,
        previous=previous,
        current=current,
        policy=policy,
    )

    assert result.invalidation is not None

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.invalidation.qualification_id = "tampered"  # type: ignore[misc]


def test_original_evidence_is_not_mutated() -> None:
    previous = _snapshot()
    current = _snapshot(kernel="6.18.1")
    policy = _policy()
    evidence = _evidence(previous, policy)
    before = evidence

    _evaluate(
        evidence=evidence,
        previous=previous,
        current=current,
        policy=policy,
    )

    assert evidence == before


def test_host_change_preserves_r5_regression_scope() -> None:
    previous = _snapshot()
    current = _snapshot(
        kernel="6.18.1",
        primitive_state=CapabilityState.UNAVAILABLE,
        primitive_evidence=("changed",),
    )
    policy = _policy()
    evidence = _evidence(previous, policy)

    result = _evaluate(
        evidence=evidence,
        previous=previous,
        current=current,
        policy=policy,
    )

    assert result.stale is True
    assert result.regression_plan is not None
    assert result.regression_plan.scope.value == (
        "native_security_qualification"
    )


def test_no_authorization_or_execution_state_is_created() -> None:
    snapshot = _snapshot()
    policy = _policy()
    evidence = _evidence(snapshot, policy)

    result = _evaluate(
        evidence=evidence,
        previous=snapshot,
        current=snapshot,
        policy=policy,
    )

    assert result.fresh is True
    assert not hasattr(result, "authorization")
    assert not hasattr(result, "execution")
    assert not hasattr(result, "enforcement")


def test_policy_only_invalidation_has_no_host_change() -> None:
    snapshot = _snapshot()
    original_policy = _policy(version="1")
    evidence = _evidence(snapshot, original_policy)

    changed_policy = _policy(version="2")
    result = _evaluate(
        evidence=evidence,
        previous=snapshot,
        current=snapshot,
        policy=changed_policy,
        negotiation=_negotiation(snapshot, changed_policy),
    )

    assert result.changes == ()
    assert result.regression_plan is None
    assert result.invalidation is not None
    assert result.invalidation.change_impact.value == "low"
