from __future__ import annotations

from lyrion.execution.backends.linux.host.contracts import (
    CapabilityState,
    LinuxHostAbstractionSnapshot,
)
from lyrion.execution.backends.linux.host.negotiation.contracts import (
    CapabilityEvaluation,
    CapabilityEvaluationDecision,
    CapabilityNegotiationResult,
    CapabilityNegotiationStatus,
    CapabilityRequirement,
    CapabilityRequirementSet,
    compute_evidence_digest,
    compute_profile_id,
)


class CapabilityNegotiationEngine:
    """
    Deterministic, read-only capability negotiation engine.

    The engine evaluates host observations against an explicit requirement
    set. It does not authorize execution, apply controls, or mutate the host.
    """

    def negotiate(
        self,
        *,
        host_snapshot: LinuxHostAbstractionSnapshot,
        requirements: CapabilityRequirementSet,
    ) -> CapabilityNegotiationResult:
        evaluations = tuple(
            self._evaluate_requirement(
                host_snapshot=host_snapshot,
                requirement=requirement,
            )
            for requirement in requirements.requirements
        )

        status = self._aggregate_status(evaluations)

        return CapabilityNegotiationResult(
            status=status,
            host_snapshot=host_snapshot,
            requirements=requirements,
            evaluations=evaluations,
            profile_id=compute_profile_id(requirements),
            evidence_digest=compute_evidence_digest(evaluations),
        )

    @staticmethod
    def _evaluate_requirement(
        *,
        host_snapshot: LinuxHostAbstractionSnapshot,
        requirement: CapabilityRequirement,
    ) -> CapabilityEvaluation:
        try:
            capability = host_snapshot.fingerprint.primitive(
                requirement.primitive
            )
        except KeyError:
            return CapabilityEvaluation(
                requirement_id=requirement.requirement_id,
                primitive=requirement.primitive,
                mode=requirement.mode,
                observed_state=CapabilityState.UNKNOWN,
                decision=(
                    CapabilityEvaluationDecision.BLOCKED
                    if requirement.mode.value == "required"
                    else CapabilityEvaluationDecision.DEGRADED
                ),
                satisfied=False,
                evidence=("observation=missing",),
                reason=(
                    "Required host primitive observation is missing."
                    if requirement.mode.value == "required"
                    else "Optional host primitive observation is missing."
                ),
            )

        observed_state = capability.state
        satisfied = observed_state in requirement.acceptable_states

        if satisfied:
            return CapabilityEvaluation(
                requirement_id=requirement.requirement_id,
                primitive=requirement.primitive,
                mode=requirement.mode,
                observed_state=observed_state,
                decision=CapabilityEvaluationDecision.SATISFIED,
                satisfied=True,
                evidence=capability.evidence,
                reason=(
                    "Observed capability state is explicitly accepted "
                    "by the requirement."
                ),
            )

        if requirement.mode.value == "required":
            return CapabilityEvaluation(
                requirement_id=requirement.requirement_id,
                primitive=requirement.primitive,
                mode=requirement.mode,
                observed_state=observed_state,
                decision=CapabilityEvaluationDecision.BLOCKED,
                satisfied=False,
                evidence=capability.evidence,
                reason=(
                    "Required capability does not satisfy the declared "
                    "acceptable states; negotiation fails closed."
                ),
            )

        return CapabilityEvaluation(
            requirement_id=requirement.requirement_id,
            primitive=requirement.primitive,
            mode=requirement.mode,
            observed_state=observed_state,
            decision=CapabilityEvaluationDecision.DEGRADED,
            satisfied=False,
            evidence=capability.evidence,
            reason=(
                "Optional capability does not satisfy the declared "
                "acceptable states; host remains usable but degraded."
            ),
        )

    @staticmethod
    def _aggregate_status(
        evaluations: tuple[CapabilityEvaluation, ...],
    ) -> CapabilityNegotiationStatus:
        if any(
            evaluation.decision
            is CapabilityEvaluationDecision.BLOCKED
            for evaluation in evaluations
        ):
            return CapabilityNegotiationStatus.BLOCKED

        if any(
            evaluation.decision
            is CapabilityEvaluationDecision.DEGRADED
            for evaluation in evaluations
        ):
            return CapabilityNegotiationStatus.DEGRADED

        return CapabilityNegotiationStatus.QUALIFIED
