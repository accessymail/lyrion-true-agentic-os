"""Deterministic construction of durable opportunity recovery context."""

from __future__ import annotations

import hashlib
import json

from lyrion.piae.contracts import Opportunity
from lyrion.persistence.contracts import OpportunityRecoveryContext


class OpportunityRecoveryContextFactory:
    """Create immutable recovery context from an authoritative Opportunity."""

    SCHEMA_VERSION = "1.0.0"

    @classmethod
    def from_opportunity(
        cls,
        opportunity: Opportunity,
        *,
        source_provenance_ref: str,
        context_revision: int = 1,
    ) -> OpportunityRecoveryContext:
        """Create recovery context without authorization or admission state."""
        if not source_provenance_ref.strip():
            raise ValueError("source_provenance_ref must not be empty")

        if context_revision < 1:
            raise ValueError("context_revision must be positive")

        payload = {
            "opportunity_id": str(opportunity.opportunity_id),
            "correlation_id": (
                str(opportunity.correlation_id)
                if opportunity.correlation_id is not None
                else None
            ),
            "trigger_event_ids": [
                str(value) for value in opportunity.trigger_event_ids
            ],
            "source_provenance_ref": source_provenance_ref,
            "relevant_state_ids": list(opportunity.relevant_state_ids),
            "goal_context": list(opportunity.goal_context),
            "title": opportunity.title,
            "description": opportunity.description,
            "user_relevance": opportunity.user_relevance,
            "expected_benefit": opportunity.expected_benefit,
            "interruption_cost": opportunity.interruption_cost,
            "risk_score": opportunity.risk_score,
            "reversibility": opportunity.reversibility,
            "urgency": opportunity.urgency,
            "confidence": opportunity.confidence,
            "required_capabilities": list(opportunity.required_capabilities),
            "required_autonomy_level": opportunity.required_autonomy_level.value,
            "sensitivity": opportunity.sensitivity.value,
            "trust_level": opportunity.trust_level.value,
            "original_status": opportunity.status.value,
            "created_at": opportunity.created_at.isoformat(),
            "expires_at": (
                opportunity.expires_at.isoformat()
                if opportunity.expires_at is not None
                else None
            ),
            "schema_version": cls.SCHEMA_VERSION,
            "context_revision": context_revision,
        }

        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

        integrity_digest = hashlib.sha256(canonical).hexdigest()

        return OpportunityRecoveryContext(
            opportunity_id=opportunity.opportunity_id,
            correlation_id=opportunity.correlation_id,
            trigger_event_ids=opportunity.trigger_event_ids,
            source_provenance_ref=source_provenance_ref,
            relevant_state_ids=opportunity.relevant_state_ids,
            goal_context=opportunity.goal_context,
            title=opportunity.title,
            description=opportunity.description,
            user_relevance=opportunity.user_relevance,
            expected_benefit=opportunity.expected_benefit,
            interruption_cost=opportunity.interruption_cost,
            risk_score=opportunity.risk_score,
            reversibility=opportunity.reversibility,
            urgency=opportunity.urgency,
            confidence=opportunity.confidence,
            required_capabilities=opportunity.required_capabilities,
            required_autonomy_level=opportunity.required_autonomy_level,
            sensitivity=opportunity.sensitivity,
            trust_level=opportunity.trust_level,
            original_status=opportunity.status.value,
            created_at=opportunity.created_at,
            expires_at=opportunity.expires_at,
            schema_version=cls.SCHEMA_VERSION,
            context_revision=context_revision,
            integrity_digest=integrity_digest,
        )
