"""R1.3.4-C C3 functional qualification-evidence tests."""

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
from lyrion.execution.backends.linux.host.qualification.evidence import (
    QUALIFICATION_RULES_VERSION,
    QualificationEvidence,
    QualificationIntegrityError,
    evidence_identity,
    host_fingerprint_digest,
    qualification_id,
)
from lyrion.execution.backends.linux.host.qualification.integrity import (
    qualification_basis_digest,
)


def _snapshot(
    *,
    architecture: str = "x86_64",
    kernel: str = "6.18.0",
    primitive_state: CapabilityState = CapabilityState.AVAILABLE,
) -> LinuxHostAbstractionSnapshot:
    identity = LinuxHostIdentity(
        os_name="Ubuntu",
        os_version="26.04",
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
                evidence=("test",),
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


def _policy(*, version: str = "1") -> LinuxHostQualificationPolicy:
    key = LinuxHostPolicyKey(
        distribution=__import__(
            "lyrion.execution.backends.linux.host.profiles.contracts",
            fromlist=["LinuxDistribution"],
        ).LinuxDistribution.UBUNTU,
        architecture=__import__(
            "lyrion.execution.backends.linux.host.profiles.contracts",
            fromlist=["LinuxArchitecture"],
        ).LinuxArchitecture.X86_64,
    )

    requirements = CapabilityRequirementSet(
        requirements=(
            CapabilityRequirement(
                requirement_id="c3-cgroups",
                primitive=HostPrimitive.CGROUPS_V2,
                mode=CapabilityRequirementMode.REQUIRED,
                acceptable_states=(CapabilityState.AVAILABLE,),
                rationale="C3 functional test.",
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


def test_host_fingerprint_digest_is_deterministic() -> None:
    snapshot = _snapshot()

    first = host_fingerprint_digest(snapshot.fingerprint)
    second = host_fingerprint_digest(snapshot.fingerprint)

    assert first == second
    assert len(first) == 64


def test_host_fingerprint_digest_changes_when_kernel_changes() -> None:
    first = host_fingerprint_digest(_snapshot(kernel="6.18.0").fingerprint)
    second = host_fingerprint_digest(_snapshot(kernel="6.18.1").fingerprint)

    assert first != second


def test_evidence_is_constructed_from_actual_negotiation() -> None:
    snapshot = _snapshot()
    policy = _policy()
    negotiation = _negotiation(snapshot, policy)

    evidence = QualificationEvidence.from_qualification(
        host_snapshot=snapshot,
        policy=policy,
        negotiation=negotiation,
        qualification_state="qualified",
    )

    assert evidence.policy_id == policy.policy_id
    assert evidence.policy_version == "1"
    assert evidence.requirement_set_id == negotiation.profile_id
    assert evidence.capability_evaluation_digest == negotiation.evidence_digest
    assert evidence.host_fingerprint_digest == host_fingerprint_digest(
        snapshot.fingerprint
    )
    assert evidence.basis_digest == qualification_basis_digest(evidence.basis)
    assert evidence.basis.qualification_rules_version == (
        QUALIFICATION_RULES_VERSION
    )


def test_evidence_identity_is_deterministic() -> None:
    snapshot = _snapshot()
    policy = _policy()
    negotiation = _negotiation(snapshot, policy)

    first = QualificationEvidence.from_qualification(
        host_snapshot=snapshot,
        policy=policy,
        negotiation=negotiation,
        qualification_state="qualified",
    )
    second = QualificationEvidence.from_qualification(
        host_snapshot=snapshot,
        policy=policy,
        negotiation=negotiation,
        qualification_state="qualified",
    )

    assert first == second
    assert first.qualification_id == second.qualification_id
    assert first.evidence_identity == second.evidence_identity


def test_policy_version_is_bound_to_basis() -> None:
    snapshot = _snapshot()

    first_policy = _policy(version="1")
    second_policy = _policy(version="2")

    first = QualificationEvidence.from_qualification(
        host_snapshot=snapshot,
        policy=first_policy,
        negotiation=_negotiation(snapshot, first_policy),
        qualification_state="qualified",
    )
    second = QualificationEvidence.from_qualification(
        host_snapshot=snapshot,
        policy=second_policy,
        negotiation=_negotiation(snapshot, second_policy),
        qualification_state="qualified",
    )

    assert first.policy_id == second.policy_id
    assert first.policy_version != second.policy_version
    assert first.basis_digest != second.basis_digest
    assert first.qualification_id != second.qualification_id


def test_requirement_set_identity_is_bound_to_evidence() -> None:
    snapshot = _snapshot()
    policy = _policy()
    negotiation = _negotiation(snapshot, policy)

    evidence = QualificationEvidence.from_qualification(
        host_snapshot=snapshot,
        policy=policy,
        negotiation=negotiation,
        qualification_state="qualified",
    )

    assert evidence.requirement_set_id == negotiation.profile_id


def test_capability_evidence_identity_is_bound() -> None:
    snapshot = _snapshot()
    policy = _policy()
    negotiation = _negotiation(snapshot, policy)

    evidence = QualificationEvidence.from_qualification(
        host_snapshot=snapshot,
        policy=policy,
        negotiation=negotiation,
        qualification_state="qualified",
    )

    assert evidence.capability_evaluation_digest == negotiation.evidence_digest


def test_mismatched_snapshot_is_rejected() -> None:
    snapshot = _snapshot()
    different_snapshot = _snapshot(kernel="different")
    policy = _policy()
    negotiation = _negotiation(snapshot, policy)

    with pytest.raises(QualificationIntegrityError):
        QualificationEvidence.from_qualification(
            host_snapshot=different_snapshot,
            policy=policy,
            negotiation=negotiation,
            qualification_state="qualified",
        )


def test_tampered_basis_is_rejected() -> None:
    snapshot = _snapshot()
    policy = _policy()
    negotiation = _negotiation(snapshot, policy)

    evidence = QualificationEvidence.from_qualification(
        host_snapshot=snapshot,
        policy=policy,
        negotiation=negotiation,
        qualification_state="qualified",
    )

    tampered_basis = dataclasses.replace(
        evidence.basis,
        policy_version="999",
    )

    with pytest.raises(QualificationIntegrityError):
        QualificationEvidence(
            qualification_id=evidence.qualification_id,
            qualification_state=evidence.qualification_state,
            basis=tampered_basis,
            basis_digest=evidence.basis_digest,
            host_fingerprint_digest=evidence.host_fingerprint_digest,
            policy_id=evidence.policy_id,
            policy_version=evidence.policy_version,
            requirement_set_id=evidence.requirement_set_id,
            capability_evaluation_digest=evidence.capability_evaluation_digest,
            evidence_identity=evidence.evidence_identity,
        )


def test_tampered_evidence_identity_is_rejected() -> None:
    snapshot = _snapshot()
    policy = _policy()
    negotiation = _negotiation(snapshot, policy)

    evidence = QualificationEvidence.from_qualification(
        host_snapshot=snapshot,
        policy=policy,
        negotiation=negotiation,
        qualification_state="qualified",
    )

    with pytest.raises(QualificationIntegrityError):
        QualificationEvidence(
            qualification_id=evidence.qualification_id,
            qualification_state=evidence.qualification_state,
            basis=evidence.basis,
            basis_digest=evidence.basis_digest,
            host_fingerprint_digest=evidence.host_fingerprint_digest,
            policy_id=evidence.policy_id,
            policy_version=evidence.policy_version,
            requirement_set_id=evidence.requirement_set_id,
            capability_evaluation_digest=evidence.capability_evaluation_digest,
            evidence_identity="0" * 64,
        )


def test_derived_identifiers_are_reproducible() -> None:
    snapshot = _snapshot()
    policy = _policy()
    negotiation = _negotiation(snapshot, policy)

    evidence = QualificationEvidence.from_qualification(
        host_snapshot=snapshot,
        policy=policy,
        negotiation=negotiation,
        qualification_state="qualified",
    )

    assert evidence.qualification_id == qualification_id(
        basis_digest=evidence.basis_digest,
        status="qualified",
    )
    assert evidence.evidence_identity == evidence_identity(
        qualification_id_value=evidence.qualification_id,
        basis_digest=evidence.basis_digest,
    )
