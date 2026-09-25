"""Atomic Opportunity persistence boundary for the PIAE runtime.

This module persists the authoritative Opportunity lifecycle record together
with its immutable R097 recovery context.

The caller MUST supply stores bound to the same PersistenceUnitOfWork
transaction. This component does not create or manage database transactions.
It also contains no authorization, admission, execution, or recovery
authority.
"""

from __future__ import annotations

from datetime import UTC, datetime

from lyrion.piae.contracts import Opportunity
from lyrion.persistence.contracts import (
    PersistentOpportunity,
    PersistentOpportunityState,
)
from lyrion.persistence.opportunity_recovery_context import (
    OpportunityRecoveryContextFactory,
)
from lyrion.persistence.protocols import (
    OpportunityRecoveryContextStore,
    OpportunityStore,
)


class OpportunityPersistenceCoordinator:
    """Persist an Opportunity lifecycle record and R097 recovery context atomically.

    Atomicity is supplied by the caller's shared PersistenceUnitOfWork.
    Both stores MUST therefore be bound to that same active transaction.
    """

    def __init__(
        self,
        opportunity_store: OpportunityStore,
        recovery_context_store: OpportunityRecoveryContextStore,
    ) -> None:
        """Initialize the coordinator with UoW-bound persistence ports."""
        self._opportunity_store = opportunity_store
        self._recovery_context_store = recovery_context_store

    async def persist_queued(
        self,
        opportunity: Opportunity,
        *,
        source_provenance_ref: str,
        context_revision: int = 1,
    ) -> PersistentOpportunity:
        """Persist one newly detected opportunity and its R097 context.

        The caller is responsible for enclosing this operation in the same
        PersistenceUnitOfWork transaction. If either persistence operation
        raises, the surrounding UoW must roll back the complete transaction.
        """
        current_time = datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise RuntimeError("persistence clock must be timezone-aware")

        normalized_provenance = source_provenance_ref.strip()
        if not normalized_provenance:
            raise ValueError(
                "source_provenance_ref must not be empty",
            )

        if context_revision < 1:
            raise ValueError(
                "context_revision must be positive",
            )

        persistent_opportunity = PersistentOpportunity(
            opportunity_id=opportunity.opportunity_id,
            state=PersistentOpportunityState.QUEUED,
            created_at=opportunity.created_at.astimezone(UTC),
            expires_at=(
                opportunity.expires_at.astimezone(UTC)
                if opportunity.expires_at is not None
                else None
            ),
            revision=1,
        )

        recovery_context = OpportunityRecoveryContextFactory.from_opportunity(
            opportunity,
            source_provenance_ref=normalized_provenance,
            context_revision=context_revision,
        )

        if (
            recovery_context.opportunity_id
            != persistent_opportunity.opportunity_id
        ):
            raise RuntimeError(
                "Opportunity and recovery context identity mismatch",
            )

        persisted = await self._opportunity_store.create(
            persistent_opportunity,
        )

        await self._recovery_context_store.create(
            recovery_context,
        )

        return persisted
