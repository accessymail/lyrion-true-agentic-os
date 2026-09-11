from __future__ import annotations

import pytest

from lyrion.execution.backends.linux.host.contracts import (
    CapabilityState,
    HostPrimitive,
    LinuxHostAbstractionSnapshot,
    LinuxHostFingerprint,
    LinuxHostIdentity,
)
from lyrion.execution.backends.linux.host.negotiation.contracts import (
    CapabilityEvaluation,
    CapabilityEvaluationDecision,
    CapabilityNegotiationResult,
    CapabilityNegotiationStatus,
    CapabilityRequirement,
    CapabilityRequirementMode,
    CapabilityRequirementSet,
    compute_evidence_digest,
    compute_profile_id,
)


def _snapshot() -> LinuxHostAbstractionSnapshot:
    identity = LinuxHostIdentity(
        os_name="Ubuntu",
        os_version="26.04",
        kernel="6.18.0-test",
        architecture="x86_64",
        virtualization="vmware",
        init_system="systemd",
    )

    fingerprint = LinuxHostFingerprint(
        identity=identity,
        primitives=(
            # Deliberately ordered by primitive identity.
            # The negotiation contract does not infer authorization.
        ),
    )

    return LinuxHostAbstractionSnapshot(
        identity=identity,
        fingerprint=fingerprint,
        user_id=1000,
        effective_capabilities=(),
        namespaces=(),
        notes=(),
    )


def _requirement_set() -> CapabilityRequirementSet:
    requirements = (
        CapabilityRequirement(
            requirement_id="req-landlock",
            primitive=HostPrimitive.LANDLOCK,
            mode=CapabilityRequirementMode.REQUIRED,
            acceptable_states=(CapabilityState.AVAILABLE,),
            rationale="Filesystem isolation requires usable Landlock.",
        ),
        CapabilityRequirement(
            requirement_id="req-seccomp",
            primitive=HostPrimitive.SECCOMP,
            mode=CapabilityRequirementMode.OPTIONAL,
            acceptable_states=(
                CapabilityState.AVAILABLE,
                CapabilityState.SUPPORTED,
            ),
            rationale="Seccomp strengthens process syscall isolation.",
        ),
    )

    return CapabilityRequirementSet(requirements=requirements)


def _evaluations() -> tuple[CapabilityEvaluation, ...]:
    return (
        CapabilityEvaluation(
            requirement_id="req-landlock",
            primitive=HostPrimitive.LANDLOCK,
            mode=CapabilityRequirementMode.REQUIRED,
            observed_state=CapabilityState.AVAILABLE,
            decision=CapabilityEvaluationDecision.SATISFIED,
            satisfied=True,
            evidence=("runtime_abi=7",),
            reason="Runtime Landlock ABI is available.",
        ),
        CapabilityEvaluation(
            requirement_id="req-seccomp",
            primitive=HostPrimitive.SECCOMP,
            mode=CapabilityRequirementMode.OPTIONAL,
            observed_state=CapabilityState.SUPPORTED,
            decision=CapabilityEvaluationDecision.SATISFIED,
            satisfied=True,
            evidence=("kernel_supported=True",),
            reason="Seccomp support is available for negotiation.",
        ),
    )


def test_requirement_is_immutable() -> None:
    requirement = CapabilityRequirement(
        requirement_id="req-test",
        primitive=HostPrimitive.LANDLOCK,
        mode=CapabilityRequirementMode.REQUIRED,
        acceptable_states=(CapabilityState.AVAILABLE,),
        rationale="test",
    )

    with pytest.raises(AttributeError):
        requirement.requirement_id = "changed"  # type: ignore[misc]


def test_requirement_rejects_blank_id() -> None:
    with pytest.raises(ValueError, match="requirement_id"):
        CapabilityRequirement(
            requirement_id=" ",
            primitive=HostPrimitive.LANDLOCK,
            mode=CapabilityRequirementMode.REQUIRED,
            acceptable_states=(CapabilityState.AVAILABLE,),
            rationale="test",
        )


def test_requirement_rejects_empty_acceptable_states() -> None:
    with pytest.raises(ValueError, match="acceptable_states"):
        CapabilityRequirement(
            requirement_id="req-test",
            primitive=HostPrimitive.LANDLOCK,
            mode=CapabilityRequirementMode.REQUIRED,
            acceptable_states=(),
            rationale="test",
        )


def test_requirement_set_requires_deterministic_order() -> None:
    first = CapabilityRequirement(
        requirement_id="z-requirement",
        primitive=HostPrimitive.LANDLOCK,
        mode=CapabilityRequirementMode.REQUIRED,
        acceptable_states=(CapabilityState.AVAILABLE,),
        rationale="test",
    )

    second = CapabilityRequirement(
        requirement_id="a-requirement",
        primitive=HostPrimitive.SECCOMP,
        mode=CapabilityRequirementMode.OPTIONAL,
        acceptable_states=(CapabilityState.SUPPORTED,),
        rationale="test",
    )

    with pytest.raises(ValueError, match="deterministically ordered"):
        CapabilityRequirementSet(requirements=(first, second))


def test_requirement_set_rejects_duplicate_ids() -> None:
    requirement = CapabilityRequirement(
        requirement_id="req-duplicate",
        primitive=HostPrimitive.LANDLOCK,
        mode=CapabilityRequirementMode.REQUIRED,
        acceptable_states=(CapabilityState.AVAILABLE,),
        rationale="test",
    )

    with pytest.raises(ValueError, match="unique"):
        CapabilityRequirementSet(
            requirements=(requirement, requirement),
        )


def test_evaluation_satisfaction_is_consistent() -> None:
    with pytest.raises(ValueError, match="satisfied"):
        CapabilityEvaluation(
            requirement_id="req-test",
            primitive=HostPrimitive.LANDLOCK,
            mode=CapabilityRequirementMode.REQUIRED,
            observed_state=CapabilityState.UNAVAILABLE,
            decision=CapabilityEvaluationDecision.BLOCKED,
            satisfied=True,
            evidence=(),
            reason="blocked",
        )


def test_negotiation_result_requires_exact_evaluation_order() -> None:
    requirements = _requirement_set()
    evaluations = _evaluations()

    result = CapabilityNegotiationResult(
        status=CapabilityNegotiationStatus.QUALIFIED,
        host_snapshot=_snapshot(),
        requirements=requirements,
        evaluations=evaluations,
        profile_id=compute_profile_id(requirements),
        evidence_digest=compute_evidence_digest(evaluations),
    )

    assert result.execution_authorized is False
    assert result.enforcement_verified is False


def test_profile_id_is_deterministic() -> None:
    requirements = _requirement_set()

    assert compute_profile_id(requirements) == compute_profile_id(
        CapabilityRequirementSet(
            requirements=tuple(requirements.requirements),
        )
    )


def test_evidence_digest_is_deterministic() -> None:
    evaluations = _evaluations()

    assert compute_evidence_digest(evaluations) == compute_evidence_digest(
        tuple(evaluations)
    )


def test_required_available_capability_is_not_authorization() -> None:
    requirements = _requirement_set()
    evaluations = _evaluations()

    result = CapabilityNegotiationResult(
        status=CapabilityNegotiationStatus.QUALIFIED,
        host_snapshot=_snapshot(),
        requirements=requirements,
        evaluations=evaluations,
        profile_id=compute_profile_id(requirements),
        evidence_digest=compute_evidence_digest(evaluations),
    )

    assert result.status is CapabilityNegotiationStatus.QUALIFIED
    assert result.execution_authorized is False
    assert result.enforcement_verified is False


def test_observed_state_can_be_recorded_without_claiming_enforcement() -> None:
    requirement = CapabilityRequirement(
        requirement_id="req-capability-observation",
        primitive=HostPrimitive.LINUX_CAPABILITIES,
        mode=CapabilityRequirementMode.OPTIONAL,
        acceptable_states=(CapabilityState.OBSERVED,),
        rationale="Observe capability state for host qualification.",
    )

    requirements = CapabilityRequirementSet(
        requirements=(requirement,),
    )

    evaluations = (
        CapabilityEvaluation(
            requirement_id=requirement.requirement_id,
            primitive=requirement.primitive,
            mode=requirement.mode,
            observed_state=CapabilityState.OBSERVED,
            decision=CapabilityEvaluationDecision.SATISFIED,
            satisfied=True,
            evidence=("effective=",),
            reason="Capability state was observed.",
        ),
    )

    result = CapabilityNegotiationResult(
        status=CapabilityNegotiationStatus.QUALIFIED,
        host_snapshot=_snapshot(),
        requirements=requirements,
        evaluations=evaluations,
        profile_id=compute_profile_id(requirements),
        evidence_digest=compute_evidence_digest(evaluations),
    )

    assert result.execution_authorized is False
    assert result.enforcement_verified is False
