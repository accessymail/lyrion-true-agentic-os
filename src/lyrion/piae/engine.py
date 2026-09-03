"""Deterministic PIAE decision engine.

This module selects an admissible decision from bounded candidates.
It does not authorize, execute, access credentials, or perform side effects.
"""

from datetime import UTC, datetime
from uuid import uuid4

from lyrion.core.types import DecisionAction, DecisionId
from lyrion.piae.contracts import (
    DecisionCandidate,
    DecisionContext,
    DecisionReason,
    DecisionResult,
    PolicyResult,
)


class PIAEDecisionEngine:
    """Pure decision-selection engine for bounded proactive assistance."""

    def decide(
        self,
        context: DecisionContext,
        candidates: tuple[DecisionCandidate, ...],
        *,
        decision_id: DecisionId | None = None,
        input_context_ref: str = "runtime",
    ) -> DecisionResult:
        """Evaluate candidates and return a governed decision result."""

        now = context.now

        if context.opportunity.is_expired(now):
            return self._build_result(
                context=context,
                candidates=candidates,
                selected_action=DecisionAction.WAIT,
                rationale=DecisionReason.TIME_SENSITIVITY,
                explanation="The opportunity has expired.",
                utility_estimate=0.0,
                authorization_required=False,
                authorization_result=PolicyResult.NOT_EVALUATED,
                policy_result=PolicyResult.NOT_EVALUATED,
                decision_id=decision_id,
                input_context_ref=input_context_ref,
                decided_at=now,
            )

        if not candidates:
            return self._build_result(
                context=context,
                candidates=candidates,
                selected_action=DecisionAction.WAIT,
                rationale=DecisionReason.INSUFFICIENT_CONFIDENCE,
                explanation="No decision candidates are available.",
                utility_estimate=0.0,
                authorization_required=False,
                authorization_result=PolicyResult.NOT_EVALUATED,
                policy_result=PolicyResult.NOT_EVALUATED,
                decision_id=decision_id,
                input_context_ref=input_context_ref,
                decided_at=now,
            )

        valid_candidates = tuple(
            candidate
            for candidate in candidates
            if self._candidate_is_admissible(context, candidate)
        )

        if not valid_candidates:
            return self._build_result(
                context=context,
                candidates=candidates,
                selected_action=DecisionAction.DENY,
                rationale=DecisionReason.POLICY,
                explanation="No candidate satisfies the current decision constraints.",
                utility_estimate=0.0,
                authorization_required=False,
                authorization_result=PolicyResult.DENIED,
                policy_result=PolicyResult.DENIED,
                decision_id=decision_id,
                input_context_ref=input_context_ref,
                decided_at=now,
            )

        ranked = sorted(
            valid_candidates,
            key=lambda candidate: self._candidate_score(context, candidate),
            reverse=True,
        )

        selected = ranked[0]
        alternatives = tuple(candidate.action for candidate in ranked[1:])

        authorization_required = (
            selected.requires_human_approval
            or selected.has_external_side_effect
            or selected.action is DecisionAction.EXECUTE
        )

        policy_result = (
            PolicyResult.REQUIRES_APPROVAL
            if selected.requires_human_approval
            else PolicyResult.NOT_EVALUATED
        )

        explanation = selected.explanation
        selected_action = selected.action
        reason = selected.rationale

        if (
            selected.has_external_side_effect
            and not context.constraints.allow_external_side_effects
        ):
            selected_action = DecisionAction.ESCALATE
            reason = DecisionReason.POLICY
            explanation = (
                "The candidate has an external side effect that is not "
                "permitted by the current constraints."
            )
            authorization_required = True
            policy_result = PolicyResult.REQUIRES_APPROVAL

        elif selected.requires_network_access and not context.constraints.allow_network_access:
            selected_action = DecisionAction.ESCALATE
            reason = DecisionReason.POLICY
            explanation = (
                "The candidate requires network access that is not "
                "permitted by the current constraints."
            )
            authorization_required = True
            policy_result = PolicyResult.REQUIRES_APPROVAL

        return self._build_result(
            context=context,
            candidates=candidates,
            selected_action=selected_action,
            rationale=reason,
            explanation=explanation,
            utility_estimate=self._utility_estimate(context, selected),
            authorization_required=authorization_required,
            authorization_result=(
                PolicyResult.REQUIRES_APPROVAL
                if authorization_required
                else PolicyResult.NOT_EVALUATED
            ),
            policy_result=policy_result,
            decision_id=decision_id,
            input_context_ref=input_context_ref,
            alternatives=alternatives,
            decided_at=now,
            confidence=selected.confidence,
        )

    @staticmethod
    def _candidate_is_admissible(
        context: DecisionContext,
        candidate: DecisionCandidate,
    ) -> bool:
        """Return whether a candidate stays within declared bounds."""

        risk_order = {
            "LOW": 0,
            "MEDIUM": 1,
            "HIGH": 2,
            "CRITICAL": 3,
        }

        if risk_order[candidate.estimated_risk.value] > risk_order[
            context.constraints.max_risk_level.value
        ]:
            return False

        if candidate.estimated_cost_units > context.constraints.max_cost_units:
            return False

        if candidate.estimated_runtime_seconds > context.constraints.max_runtime_seconds:
            return False

        if (
            candidate.has_external_side_effect
            and not context.constraints.allow_external_side_effects
            and candidate.action is not DecisionAction.EXECUTE
        ):
            return True

        return True

    @staticmethod
    def _candidate_score(
        context: DecisionContext,
        candidate: DecisionCandidate,
    ) -> float:
        """Calculate a bounded deterministic candidate score."""

        opportunity = context.opportunity

        utility = opportunity.expected_benefit * opportunity.user_relevance
        utility += opportunity.urgency * 0.2
        utility += opportunity.confidence * candidate.confidence * 0.2

        interruption_penalty = opportunity.interruption_cost * 0.4
        risk_penalty = opportunity.risk_score * 0.3
        cost_penalty = candidate.estimated_cost_units * 0.01

        return utility - interruption_penalty - risk_penalty - cost_penalty

    @staticmethod
    def _utility_estimate(
        context: DecisionContext,
        candidate: DecisionCandidate,
    ) -> float:
        """Return a bounded utility estimate."""

        score = PIAEDecisionEngine._candidate_score(context, candidate)

        return max(0.0, min(1.0, score))

    @staticmethod
    def _build_result(
        *,
        context: DecisionContext,
        candidates: tuple[DecisionCandidate, ...],
        selected_action: DecisionAction,
        rationale: DecisionReason,
        explanation: str,
        utility_estimate: float,
        authorization_required: bool,
        authorization_result: PolicyResult,
        policy_result: PolicyResult,
        decision_id: DecisionId | None,
        input_context_ref: str,
        decided_at: datetime,
        alternatives: tuple[DecisionAction, ...] = (),
        confidence: float = 0.0,
    ) -> DecisionResult:
        """Build a validated immutable decision result."""

        return DecisionResult(
            decision_id=decision_id or DecisionId(str(uuid4())),
            input_context_ref=input_context_ref,
            opportunity_ref=context.opportunity.opportunity_id,
            selected_action=selected_action,
            alternative_actions=alternatives,
            utility_estimate=utility_estimate,
            interruption_cost=context.opportunity.interruption_cost,
            risk_estimate=context.opportunity.risk_score,
            autonomy_level=context.autonomy_level,
            authorization_result=authorization_result,
            policy_result=policy_result,
            confidence=confidence,
            reason_codes=(rationale,),
            authorization_required=authorization_required,
            authorization_granted=False,
            candidate_count=len(candidates),
            correlation_id=context.opportunity.correlation_id,
            idempotency_key=None,
            expires_at=context.opportunity.expires_at,
            decided_at=decided_at.astimezone(UTC),
        )
