from __future__ import annotations

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
    CapabilityNegotiationStatus,
    CapabilityRequirement,
    CapabilityRequirementMode,
    CapabilityRequirementSet,
)
from lyrion.execution.backends.linux.host.qualification import (
    AdaptiveQualificationEngine,
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
            primitives=tuple(
                sorted(
                    capabilities,
                    key=lambda capability: capability.primitive.value,
                )
            ),
        ),
        user_id=1000,
        effective_capabilities=(),
        namespaces=(),
        notes=(),
    )


def _requirements(
    *,
    primitive: HostPrimitive = HostPrimitive.LANDLOCK,
    mode: CapabilityRequirementMode = CapabilityRequirementMode.REQUIRED,
    acceptable_states: tuple[CapabilityState, ...] = (
        CapabilityState.AVAILABLE,
    ),
) -> CapabilityRequirementSet:
    return CapabilityRequirementSet(
        requirements=(
            CapabilityRequirement(
                requirement_id="qualification-landlock",
                primitive=primitive,
                mode=mode,
                acceptable_states=acceptable_states,
                rationale="Adaptive qualification validation.",
            ),
        ),
    )


def test_available_required_capability_qualifies_host() -> None:
    result = AdaptiveQualificationEngine().qualify(
        host_snapshot=_snapshot(
            HostPrimitiveCapability(
                primitive=HostPrimitive.LANDLOCK,
                state=CapabilityState.AVAILABLE,
                evidence=("runtime_abi=7",),
            ),
        ),
        requirements=_requirements(),
    )

    assert result.status is CapabilityNegotiationStatus.QUALIFIED
    assert result.qualified is True
    assert result.degraded is False
    assert result.blocked is False
    assert result.execution_authorized is False
    assert result.enforcement_verified is False
    assert len(result.profile_id) == 64
    assert len(result.evidence_digest) == 64


def test_missing_required_capability_blocks_host() -> None:
    result = AdaptiveQualificationEngine().qualify(
        host_snapshot=_snapshot(),
        requirements=_requirements(),
    )

    assert result.status is CapabilityNegotiationStatus.BLOCKED
    assert result.blocked is True
    assert result.execution_authorized is False
    assert result.enforcement_verified is False


def test_optional_missing_capability_degrades_host() -> None:
    result = AdaptiveQualificationEngine().qualify(
        host_snapshot=_snapshot(),
        requirements=_requirements(
            mode=CapabilityRequirementMode.OPTIONAL,
        ),
    )

    assert result.status is CapabilityNegotiationStatus.DEGRADED
    assert result.degraded is True
    assert result.execution_authorized is False
    assert result.enforcement_verified is False


def test_supported_is_not_implicitly_available() -> None:
    result = AdaptiveQualificationEngine().qualify(
        host_snapshot=_snapshot(
            HostPrimitiveCapability(
                primitive=HostPrimitive.LANDLOCK,
                state=CapabilityState.SUPPORTED,
                evidence=("kernel_supported=True",),
            ),
        ),
        requirements=_requirements(),
    )

    assert result.status is CapabilityNegotiationStatus.BLOCKED


def test_observed_is_not_implicitly_available() -> None:
    result = AdaptiveQualificationEngine().qualify(
        host_snapshot=_snapshot(
            HostPrimitiveCapability(
                primitive=HostPrimitive.LANDLOCK,
                state=CapabilityState.OBSERVED,
                evidence=("observed=True",),
            ),
        ),
        requirements=_requirements(),
    )

    assert result.status is CapabilityNegotiationStatus.BLOCKED


def test_qualification_preserves_negotiation_identity() -> None:
    result = AdaptiveQualificationEngine().qualify(
        host_snapshot=_snapshot(
            HostPrimitiveCapability(
                primitive=HostPrimitive.LANDLOCK,
                state=CapabilityState.AVAILABLE,
                evidence=("runtime_abi=7",),
            ),
        ),
        requirements=_requirements(),
    )

    assert result.profile_id == result.negotiation.profile_id
    assert result.evidence_digest == result.negotiation.evidence_digest
    assert result.status is result.negotiation.status


def test_repeated_qualification_is_deterministic() -> None:
    snapshot = _snapshot(
        HostPrimitiveCapability(
            primitive=HostPrimitive.LANDLOCK,
            state=CapabilityState.AVAILABLE,
            evidence=("runtime_abi=7",),
        ),
    )
    requirements = _requirements()

    engine = AdaptiveQualificationEngine()

    first = engine.qualify(
        host_snapshot=snapshot,
        requirements=requirements,
    )
    second = engine.qualify(
        host_snapshot=snapshot,
        requirements=requirements,
    )

    assert first == second


def test_qualification_does_not_mutate_snapshot() -> None:
    snapshot = _snapshot(
        HostPrimitiveCapability(
            primitive=HostPrimitive.LANDLOCK,
            state=CapabilityState.AVAILABLE,
            evidence=("runtime_abi=7",),
        ),
    )

    before = snapshot

    AdaptiveQualificationEngine().qualify(
        host_snapshot=snapshot,
        requirements=_requirements(),
    )

    assert snapshot == before


def test_authorization_boundary_is_fail_closed() -> None:
    engine = AdaptiveQualificationEngine()

    qualified = engine.qualify(
        host_snapshot=_snapshot(
            HostPrimitiveCapability(
                primitive=HostPrimitive.LANDLOCK,
                state=CapabilityState.AVAILABLE,
                evidence=("runtime_abi=7",),
            ),
        ),
        requirements=_requirements(),
    )

    assert qualified.qualified is True
    assert qualified.execution_authorized is False
    assert qualified.enforcement_verified is False


def test_tampered_authorization_flag_is_rejected() -> None:
    class TamperingEngine:
        def negotiate(
            self,
            *,
            host_snapshot: LinuxHostAbstractionSnapshot,
            requirements: CapabilityRequirementSet,
        ):
            from lyrion.execution.backends.linux.host.negotiation.engine import (
                CapabilityNegotiationEngine,
            )

            original = CapabilityNegotiationEngine().negotiate(
                host_snapshot=host_snapshot,
                requirements=requirements,
            )

            class TamperedResult:
                status = original.status
                profile_id = original.profile_id
                evidence_digest = original.evidence_digest
                execution_authorized = True
                enforcement_verified = False

            return TamperedResult()

    with pytest.raises(
        RuntimeError,
        match="cannot authorize execution",
    ):
        AdaptiveQualificationEngine(
            negotiation_engine=TamperingEngine(),
        ).qualify(
            host_snapshot=_snapshot(
                HostPrimitiveCapability(
                    primitive=HostPrimitive.LANDLOCK,
                    state=CapabilityState.AVAILABLE,
                    evidence=("runtime_abi=7",),
                ),
            ),
            requirements=_requirements(),
        )


def test_tampered_enforcement_flag_is_rejected() -> None:
    class TamperingEngine:
        def negotiate(
            self,
            *,
            host_snapshot: LinuxHostAbstractionSnapshot,
            requirements: CapabilityRequirementSet,
        ):
            from lyrion.execution.backends.linux.host.negotiation.engine import (
                CapabilityNegotiationEngine,
            )

            original = CapabilityNegotiationEngine().negotiate(
                host_snapshot=host_snapshot,
                requirements=requirements,
            )

            class TamperedResult:
                status = original.status
                profile_id = original.profile_id
                evidence_digest = original.evidence_digest
                execution_authorized = False
                enforcement_verified = True

            return TamperedResult()

    with pytest.raises(
        RuntimeError,
        match="cannot claim enforcement verification",
    ):
        AdaptiveQualificationEngine(
            negotiation_engine=TamperingEngine(),
        ).qualify(
            host_snapshot=_snapshot(
                HostPrimitiveCapability(
                    primitive=HostPrimitive.LANDLOCK,
                    state=CapabilityState.AVAILABLE,
                    evidence=("runtime_abi=7",),
                ),
            ),
            requirements=_requirements(),
        )
