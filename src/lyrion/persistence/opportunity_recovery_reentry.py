"""Controlled R097 recovery re-entry into the existing PIAE queue.

Recovery restores durable work context only. This module reconstructs a
fresh Opportunity from the immutable R097 recovery context and places it
back into the existing OpportunityQueue.

Authorization, admission, delegated authority, and execution authority
are intentionally absent from this module. The existing PIAE action path
must perform fresh decision, CapabilityRequest creation, Aegis
authorization, and ExecutionAdmission.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from lyrion.piae.contracts import Opportunity
from lyrion.piae.opportunity_queue import OpportunityQueue
from lyrion.persistence.opportunity_recovery_context_resolver import (
    OpportunityRecoveryContextResolver,
)


@dataclass(frozen=True)
class RecoveryReentryResult:
    """Result of one controlled R097 recovery re-entry attempt."""

    opportunity_id: str
    enqueued: bool


class OpportunityRecoveryReentryCoordinator:
    """Re-enter recovered work through the existing PIAE queue."""

    def __init__(
        self,
        *,
        resolver: OpportunityRecoveryContextResolver,
        opportunity_queue: OpportunityQueue,
    ) -> None:
        self._resolver = resolver
        self._opportunity_queue = opportunity_queue

    async def reenter(
        self,
        opportunity_id: str,
        *,
        current_time: datetime,
    ) -> RecoveryReentryResult:
        """Resolve recovery context and enqueue a fresh Opportunity.

        This method never creates or restores authorization, admission,
        delegated authority, leases, or execution authority.
        """
        now = self._normalize_now(current_time)

        normalized_id = opportunity_id.strip()
        if not normalized_id:
            raise ValueError("opportunity_id must not be empty")

        opportunity = await self._resolver.resolve(
            normalized_id,
            current_time=now,
        )

        self._validate_reconstructed_opportunity(
            opportunity,
            normalized_id,
        )

        already_queued = self._opportunity_queue.contains(
            opportunity.opportunity_id,
        )

        if already_queued:
            return RecoveryReentryResult(
                opportunity_id=normalized_id,
                enqueued=False,
            )

        accepted = self._opportunity_queue.enqueue(
            opportunity,
            now=now,
        )

        if not accepted:
            raise RuntimeError(
                "R097 recovery OpportunityQueue rejected "
                "the reconstructed Opportunity",
            )

        return RecoveryReentryResult(
            opportunity_id=normalized_id,
            enqueued=True,
        )

    @staticmethod
    def _validate_reconstructed_opportunity(
        opportunity: Opportunity,
        expected_opportunity_id: str,
    ) -> None:
        if str(opportunity.opportunity_id) != expected_opportunity_id:
            raise ValueError(
                "R097 reconstructed Opportunity identity mismatch",
            )

        if opportunity.expires_at is not None:
            if (
                opportunity.expires_at.tzinfo is None
                or opportunity.expires_at.utcoffset() is None
            ):
                raise ValueError(
                    "R097 Opportunity expiry must be timezone-aware",
                )

        if not opportunity.required_capabilities:
            raise ValueError(
                "R097 recovered Opportunity has no required capabilities",
            )

    @staticmethod
    def _normalize_now(now: datetime) -> datetime:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError(
                "current_time must be timezone-aware",
            )

        return now.astimezone(UTC)
