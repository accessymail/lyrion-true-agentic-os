"""Deterministic recovery analysis for persistent Lyrion executions."""

from __future__ import annotations

from datetime import UTC, datetime

from lyrion.persistence.contracts import (
    PersistentExecutionRecord,
    PersistentExecutionState,
    RecoveryAction,
    RecoveryDecision,
    RuntimeLease,
)


class RecoveryManager:
    """Analyze durable execution state without performing recovery."""

    def decide(
        self,
        *,
        record: PersistentExecutionRecord,
        lease: RuntimeLease | None,
        now: datetime,
    ) -> RecoveryDecision:
        """Return a deterministic recovery decision."""
        current_time = self._normalize_now(now)

        state = record.state

        if state is PersistentExecutionState.QUEUED:
            return self._decision(
                record,
                RecoveryAction.NOOP,
                "Execution is still queued.",
                current_time,
            )

        if state is PersistentExecutionState.ABANDONED:
            return self._decision(
                record,
                RecoveryAction.QUARANTINE,
                "Execution was explicitly abandoned.",
                current_time,
            )

        if state in {
            PersistentExecutionState.COMPLETED,
            PersistentExecutionState.FAILED,
            PersistentExecutionState.CANCELLED,
        }:
            return self._decision(
                record,
                RecoveryAction.NOOP,
                "Execution is already terminal.",
                current_time,
            )

        if state is PersistentExecutionState.UNKNOWN:
            return self._decision(
                record,
                RecoveryAction.RECONCILE,
                "Execution outcome is unresolved.",
                current_time,
            )

        if lease is not None and not lease.is_expired(current_time):
            return self._decision(
                record,
                RecoveryAction.NOOP,
                "Execution still has an active ownership lease.",
                current_time,
            )

        if state is PersistentExecutionState.CLAIMED:
            return self._decision(
                record,
                RecoveryAction.REQUEUE,
                "Execution claim lost ownership before execution began.",
                current_time,
            )

        if state is PersistentExecutionState.EXECUTING:
            return self._decision(
                record,
                RecoveryAction.RECONCILE,
                "Execution lost ownership while execution outcome may be unknown.",
                current_time,
            )

        raise ValueError(
            f"unsupported recovery state: {state}",
        )

    @staticmethod
    def _normalize_now(
        now: datetime,
    ) -> datetime:
        """Normalize and validate recovery evaluation time."""
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError(
                "now must be timezone-aware"
            )

        return now.astimezone(UTC)

    @staticmethod
    def _decision(
        record: PersistentExecutionRecord,
        action: RecoveryAction,
        reason: str,
        evaluated_at: datetime,
    ) -> RecoveryDecision:
        """Build an explicit immutable recovery decision."""
        return RecoveryDecision(
            execution_id=record.execution_id,
            action=action,
            reason=reason,
            evaluated_at=evaluated_at,
            source_revision=record.revision,
        )
