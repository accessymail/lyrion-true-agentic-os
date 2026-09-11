from __future__ import annotations

from lyrion.execution.backends.linux.host.contracts import (
    CapabilityState,
    HostPrimitive,
    HostPrimitiveCapability,
    LinuxHostAbstractionSnapshot,
    LinuxHostFingerprint,
    LinuxHostIdentity,
)
from lyrion.execution.backends.linux.host.negotiation import (
    CapabilityEvaluationDecision,
    CapabilityNegotiationEngine,
    CapabilityNegotiationStatus,
    CapabilityRequirement,
    CapabilityRequirementMode,
    CapabilityRequirementSet,
)


def _identity() -> LinuxHostIdentity:
    return LinuxHostIdentity(
        os_name="Ubuntu",
        os_version="26.04",
        kernel="6.18.0-test",
        architecture="x86_64",
        virtualization="vmware",
        init_system="systemd",
    )


def _snapshot(
    *capabilities: HostPrimitiveCapability,
) -> LinuxHostAbstractionSnapshot:
    identity = _identity()

    return LinuxHostAbstractionSnapshot(
        identity=identity,
        fingerprint=LinuxHostFingerprint(
            identity=identity,
            primitives=tuple(sorted(
                capabilities,
                key=lambda capability: capability.primitive.value,
            )),
        ),
        user_id=1000,
        effective_capabilities=(),
        namespaces=(),
        notes=(),
    )


def _requirement(
    requirement_id: str,
    primitive: HostPrimitive,
    mode: CapabilityRequirementMode,
    states: tuple[CapabilityState, ...],
) -> CapabilityRequirement:
    return CapabilityRequirement(
        requirement_id=requirement_id,
        primitive=primitive,
        mode=mode,
        acceptable_states=states,
        rationale="Test requirement.",
    )


def test_required_acceptable_capability_is_qualified() -> None:
    snapshot = _snapshot(
        HostPrimitiveCapability(
            primitive=HostPrimitive.LANDLOCK,
            state=CapabilityState.AVAILABLE,
            evidence=("runtime_abi=7",),
        ),
    )

    requirements = CapabilityRequirementSet(
        requirements=(
            _requirement(
                "req-landlock",
                HostPrimitive.LANDLOCK,
                CapabilityRequirementMode.REQUIRED,
                (CapabilityState.AVAILABLE,),
            ),
        ),
    )

    result = CapabilityNegotiationEngine().negotiate(
        host_snapshot=snapshot,
        requirements=requirements,
    )

    assert result.status is CapabilityNegotiationStatus.QUALIFIED
    assert result.evaluations[0].decision is (
        CapabilityEvaluationDecision.SATISFIED
    )


def test_required_unavailable_capability_blocks() -> None:
    snapshot = _snapshot(
        HostPrimitiveCapability(
            primitive=HostPrimitive.LANDLOCK,
            state=CapabilityState.UNAVAILABLE,
        ),
    )

    requirements = CapabilityRequirementSet(
        requirements=(
            _requirement(
                "req-landlock",
                HostPrimitive.LANDLOCK,
                CapabilityRequirementMode.REQUIRED,
                (CapabilityState.AVAILABLE,),
            ),
        ),
    )

    result = CapabilityNegotiationEngine().negotiate(
        host_snapshot=snapshot,
        requirements=requirements,
    )

    assert result.status is CapabilityNegotiationStatus.BLOCKED
    assert result.evaluations[0].satisfied is False


def test_required_unknown_capability_blocks() -> None:
    snapshot = _snapshot(
        HostPrimitiveCapability(
            primitive=HostPrimitive.LANDLOCK,
            state=CapabilityState.UNKNOWN,
        ),
    )

    requirements = CapabilityRequirementSet(
        requirements=(
            _requirement(
                "req-landlock",
                HostPrimitive.LANDLOCK,
                CapabilityRequirementMode.REQUIRED,
                (CapabilityState.AVAILABLE,),
            ),
        ),
    )

    result = CapabilityNegotiationEngine().negotiate(
        host_snapshot=snapshot,
        requirements=requirements,
    )

    assert result.status is CapabilityNegotiationStatus.BLOCKED


def test_required_missing_observation_blocks() -> None:
    snapshot = _snapshot()

    requirements = CapabilityRequirementSet(
        requirements=(
            _requirement(
                "req-landlock",
                HostPrimitive.LANDLOCK,
                CapabilityRequirementMode.REQUIRED,
                (CapabilityState.AVAILABLE,),
            ),
        ),
    )

    result = CapabilityNegotiationEngine().negotiate(
        host_snapshot=snapshot,
        requirements=requirements,
    )

    assert result.status is CapabilityNegotiationStatus.BLOCKED
    assert result.evaluations[0].observed_state is CapabilityState.UNKNOWN


def test_optional_unsatisfied_capability_degrades() -> None:
    snapshot = _snapshot(
        HostPrimitiveCapability(
            primitive=HostPrimitive.APPARMOR,
            state=CapabilityState.SUPPORTED,
        ),
    )

    requirements = CapabilityRequirementSet(
        requirements=(
            _requirement(
                "req-apparmor",
                HostPrimitive.APPARMOR,
                CapabilityRequirementMode.OPTIONAL,
                (CapabilityState.AVAILABLE,),
            ),
        ),
    )

    result = CapabilityNegotiationEngine().negotiate(
        host_snapshot=snapshot,
        requirements=requirements,
    )

    assert result.status is CapabilityNegotiationStatus.DEGRADED
    assert result.evaluations[0].decision is (
        CapabilityEvaluationDecision.DEGRADED
    )


def test_optional_missing_observation_degrades() -> None:
    snapshot = _snapshot()

    requirements = CapabilityRequirementSet(
        requirements=(
            _requirement(
                "req-apparmor",
                HostPrimitive.APPARMOR,
                CapabilityRequirementMode.OPTIONAL,
                (CapabilityState.AVAILABLE,),
            ),
        ),
    )

    result = CapabilityNegotiationEngine().negotiate(
        host_snapshot=snapshot,
        requirements=requirements,
    )

    assert result.status is CapabilityNegotiationStatus.DEGRADED


def test_observed_does_not_become_available() -> None:
    snapshot = _snapshot(
        HostPrimitiveCapability(
            primitive=HostPrimitive.LINUX_CAPABILITIES,
            state=CapabilityState.OBSERVED,
        ),
    )

    requirements = CapabilityRequirementSet(
        requirements=(
            _requirement(
                "req-capabilities",
                HostPrimitive.LINUX_CAPABILITIES,
                CapabilityRequirementMode.REQUIRED,
                (CapabilityState.AVAILABLE,),
            ),
        ),
    )

    result = CapabilityNegotiationEngine().negotiate(
        host_snapshot=snapshot,
        requirements=requirements,
    )

    assert result.status is CapabilityNegotiationStatus.BLOCKED
    assert result.evaluations[0].observed_state is CapabilityState.OBSERVED


def test_supported_is_not_implicitly_available() -> None:
    snapshot = _snapshot(
        HostPrimitiveCapability(
            primitive=HostPrimitive.SECCOMP,
            state=CapabilityState.SUPPORTED,
        ),
    )

    requirements = CapabilityRequirementSet(
        requirements=(
            _requirement(
                "req-seccomp",
                HostPrimitive.SECCOMP,
                CapabilityRequirementMode.REQUIRED,
                (CapabilityState.AVAILABLE,),
            ),
        ),
    )

    result = CapabilityNegotiationEngine().negotiate(
        host_snapshot=snapshot,
        requirements=requirements,
    )

    assert result.status is CapabilityNegotiationStatus.BLOCKED


def test_explicitly_accepted_supported_state_is_satisfied() -> None:
    snapshot = _snapshot(
        HostPrimitiveCapability(
            primitive=HostPrimitive.SECCOMP,
            state=CapabilityState.SUPPORTED,
        ),
    )

    requirements = CapabilityRequirementSet(
        requirements=(
            _requirement(
                "req-seccomp",
                HostPrimitive.SECCOMP,
                CapabilityRequirementMode.REQUIRED,
                (CapabilityState.SUPPORTED,),
            ),
        ),
    )

    result = CapabilityNegotiationEngine().negotiate(
        host_snapshot=snapshot,
        requirements=requirements,
    )

    assert result.status is CapabilityNegotiationStatus.QUALIFIED


def test_blocked_takes_precedence_over_degraded() -> None:
    snapshot = _snapshot(
        HostPrimitiveCapability(
            primitive=HostPrimitive.APPARMOR,
            state=CapabilityState.SUPPORTED,
        ),
        HostPrimitiveCapability(
            primitive=HostPrimitive.LANDLOCK,
            state=CapabilityState.UNAVAILABLE,
        ),
    )

    requirements = CapabilityRequirementSet(
        requirements=(
            _requirement(
                "req-apparmor",
                HostPrimitive.APPARMOR,
                CapabilityRequirementMode.OPTIONAL,
                (CapabilityState.AVAILABLE,),
            ),
            _requirement(
                "req-landlock",
                HostPrimitive.LANDLOCK,
                CapabilityRequirementMode.REQUIRED,
                (CapabilityState.AVAILABLE,),
            ),
        ),
    )

    result = CapabilityNegotiationEngine().negotiate(
        host_snapshot=snapshot,
        requirements=requirements,
    )

    assert result.status is CapabilityNegotiationStatus.BLOCKED


def test_evaluation_order_is_requirement_id_order() -> None:
    snapshot = _snapshot(
        HostPrimitiveCapability(
            primitive=HostPrimitive.LANDLOCK,
            state=CapabilityState.AVAILABLE,
        ),
        HostPrimitiveCapability(
            primitive=HostPrimitive.SECCOMP,
            state=CapabilityState.AVAILABLE,
        ),
    )

    requirements = CapabilityRequirementSet(
        requirements=(
            _requirement(
                "a-seccomp",
                HostPrimitive.SECCOMP,
                CapabilityRequirementMode.REQUIRED,
                (CapabilityState.AVAILABLE,),
            ),
            _requirement(
                "z-landlock",
                HostPrimitive.LANDLOCK,
                CapabilityRequirementMode.REQUIRED,
                (CapabilityState.AVAILABLE,),
            ),
        ),
    )

    result = CapabilityNegotiationEngine().negotiate(
        host_snapshot=snapshot,
        requirements=requirements,
    )

    assert tuple(
        evaluation.requirement_id
        for evaluation in result.evaluations
    ) == ("a-seccomp", "z-landlock")


def test_engine_does_not_authorize_or_verify_enforcement() -> None:
    snapshot = _snapshot(
        HostPrimitiveCapability(
            primitive=HostPrimitive.LANDLOCK,
            state=CapabilityState.AVAILABLE,
        ),
    )

    requirements = CapabilityRequirementSet(
        requirements=(
            _requirement(
                "req-landlock",
                HostPrimitive.LANDLOCK,
                CapabilityRequirementMode.REQUIRED,
                (CapabilityState.AVAILABLE,),
            ),
        ),
    )

    result = CapabilityNegotiationEngine().negotiate(
        host_snapshot=snapshot,
        requirements=requirements,
    )

    assert result.execution_authorized is False
    assert result.enforcement_verified is False


def test_engine_is_repeatable() -> None:
    snapshot = _snapshot(
        HostPrimitiveCapability(
            primitive=HostPrimitive.LANDLOCK,
            state=CapabilityState.AVAILABLE,
            evidence=("runtime_abi=7",),
        ),
    )

    requirements = CapabilityRequirementSet(
        requirements=(
            _requirement(
                "req-landlock",
                HostPrimitive.LANDLOCK,
                CapabilityRequirementMode.REQUIRED,
                (CapabilityState.AVAILABLE,),
            ),
        ),
    )

    engine = CapabilityNegotiationEngine()

    first = engine.negotiate(
        host_snapshot=snapshot,
        requirements=requirements,
    )
    second = engine.negotiate(
        host_snapshot=snapshot,
        requirements=requirements,
    )

    assert first == second
    assert first.profile_id == second.profile_id
    assert first.evidence_digest == second.evidence_digest
