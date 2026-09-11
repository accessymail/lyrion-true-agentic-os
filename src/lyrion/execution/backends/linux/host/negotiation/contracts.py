from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum

from lyrion.execution.backends.linux.host.contracts import (
    CapabilityState,
    HostPrimitive,
    LinuxHostAbstractionSnapshot,
)


class CapabilityRequirementMode(StrEnum):
    REQUIRED = "required"
    OPTIONAL = "optional"


class CapabilityEvaluationDecision(StrEnum):
    SATISFIED = "satisfied"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


class CapabilityNegotiationStatus(StrEnum):
    QUALIFIED = "qualified"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class CapabilityRequirement:
    """
    Immutable declaration of a host capability requirement.

    This is a requirement contract only. It does not grant authorization,
    activate a primitive, or claim that enforcement has been applied.
    """

    requirement_id: str
    primitive: HostPrimitive
    mode: CapabilityRequirementMode
    acceptable_states: tuple[CapabilityState, ...]
    rationale: str

    def __post_init__(self) -> None:
        if not self.requirement_id.strip():
            raise ValueError("requirement_id must not be blank")

        if not self.acceptable_states:
            raise ValueError(
                "acceptable_states must contain at least one state"
            )

        if len(set(self.acceptable_states)) != len(self.acceptable_states):
            raise ValueError(
                "acceptable_states must not contain duplicates"
            )

        if not self.rationale.strip():
            raise ValueError("rationale must not be blank")


@dataclass(frozen=True, slots=True)
class CapabilityRequirementSet:
    """
    Immutable, deterministically ordered capability requirements.
    """

    requirements: tuple[CapabilityRequirement, ...]

    def __post_init__(self) -> None:
        requirement_ids = tuple(
            requirement.requirement_id
            for requirement in self.requirements
        )

        if len(set(requirement_ids)) != len(requirement_ids):
            raise ValueError("requirement_id values must be unique")

        if requirement_ids != tuple(sorted(requirement_ids)):
            raise ValueError(
                "requirements must be deterministically ordered "
                "by requirement_id"
            )

    @property
    def requirement_ids(self) -> tuple[str, ...]:
        return tuple(
            requirement.requirement_id
            for requirement in self.requirements
        )


@dataclass(frozen=True, slots=True)
class CapabilityEvaluation:
    """
    Immutable evaluation record for one capability requirement.

    This records an observation and a contract-level decision only.
    It is not execution authorization and does not prove enforcement.
    """

    requirement_id: str
    primitive: HostPrimitive
    mode: CapabilityRequirementMode
    observed_state: CapabilityState
    decision: CapabilityEvaluationDecision
    satisfied: bool
    evidence: tuple[str, ...]
    reason: str

    def __post_init__(self) -> None:
        if not self.requirement_id.strip():
            raise ValueError("requirement_id must not be blank")

        if not self.reason.strip():
            raise ValueError("reason must not be blank")

        if self.satisfied != (
            self.decision == CapabilityEvaluationDecision.SATISFIED
        ):
            raise ValueError(
                "satisfied must agree with the evaluation decision"
            )

        for item in self.evidence:
            if not isinstance(item, str):
                raise TypeError("evaluation evidence must contain strings")


@dataclass(frozen=True, slots=True)
class CapabilityNegotiationResult:
    """
    Immutable capability-negotiation result.

    The result describes compatibility between a host observation and a
    declared requirement set. It is deliberately non-authorizing.
    """

    status: CapabilityNegotiationStatus
    host_snapshot: LinuxHostAbstractionSnapshot
    requirements: CapabilityRequirementSet
    evaluations: tuple[CapabilityEvaluation, ...]
    profile_id: str
    evidence_digest: str

    def __post_init__(self) -> None:
        evaluation_ids = tuple(
            evaluation.requirement_id
            for evaluation in self.evaluations
        )

        expected_ids = self.requirements.requirement_ids

        if evaluation_ids != expected_ids:
            raise ValueError(
                "evaluations must correspond exactly to requirement_ids "
                "in deterministic order"
            )

        if not self.profile_id.strip():
            raise ValueError("profile_id must not be blank")

        if len(self.evidence_digest) != 64:
            raise ValueError("evidence_digest must be a SHA-256 hex digest")

        try:
            int(self.evidence_digest, 16)
        except ValueError as exc:
            raise ValueError(
                "evidence_digest must be hexadecimal"
            ) from exc

    @property
    def execution_authorized(self) -> bool:
        """
        Explicitly remains false.

        Capability negotiation never becomes an authorization authority.
        """

        return False

    @property
    def enforcement_verified(self) -> bool:
        """
        Capability negotiation does not prove enforcement.
        """

        return False


def canonical_requirement_payload(
    requirements: CapabilityRequirementSet,
) -> tuple[dict[str, object], ...]:
    """
    Produce deterministic, JSON-safe requirement material.
    """

    return tuple(
        {
            "requirement_id": requirement.requirement_id,
            "primitive": requirement.primitive.value,
            "mode": requirement.mode.value,
            "acceptable_states": tuple(
                state.value
                for state in requirement.acceptable_states
            ),
            "rationale": requirement.rationale,
        }
        for requirement in requirements.requirements
    )


def canonical_evaluation_payload(
    evaluations: tuple[CapabilityEvaluation, ...],
) -> tuple[dict[str, object], ...]:
    """
    Produce deterministic, JSON-safe evaluation material.
    """

    return tuple(
        {
            "requirement_id": evaluation.requirement_id,
            "primitive": evaluation.primitive.value,
            "mode": evaluation.mode.value,
            "observed_state": evaluation.observed_state.value,
            "decision": evaluation.decision.value,
            "satisfied": evaluation.satisfied,
            "evidence": evaluation.evidence,
            "reason": evaluation.reason,
        }
        for evaluation in evaluations
    )


def compute_profile_id(
    requirements: CapabilityRequirementSet,
) -> str:
    """
    Deterministically identify a requirement profile.
    """

    payload = json.dumps(
        canonical_requirement_payload(requirements),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


def compute_evidence_digest(
    evaluations: tuple[CapabilityEvaluation, ...],
) -> str:
    """
    Deterministically hash negotiation evidence.

    This is an evidence identity, not a cryptographic trust assertion.
    """

    payload = json.dumps(
        canonical_evaluation_payload(evaluations),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()
