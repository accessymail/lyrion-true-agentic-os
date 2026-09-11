"""Apply deterministic recovery decisions to durable execution state."""

from __future__ import annotations

from datetime import UTC, datetime

from lyrion.persistence.contracts import (
    PersistentExecutionState,
    RecoveryAction,
)
from lyrion.persistence.protocols import (
    ExecutionStore,
    LeaseStore,
    RecoveryStore,
)
from lyrion.persistence.recovery import RecoveryManager


class PersistentRecoveryOrchestrator:
    """Evaluate and apply bounded execution recovery decisions."""

    def __init__(
        self,
        execution_store: ExecutionStore,
        lease_store: LeaseStore,
        recovery_store: RecoveryStore,
        *,
        manager: RecoveryManager | None = None,
    ) -> None:
        """Initialize the recovery orchestrator."""
        self._execution_store = execution_store
        self._lease_store = lease_store
        self._recovery_store = recovery_store
        self._manager = manager or RecoveryManager()

    async def recover_one(
        self,
        *,
        execution_id: str,
        now: datetime,
    ) -> RecoveryAction:
        """Evaluate and apply recovery for one execution."""
        current_time = self._normalize_now(now)

        record = await self._execution_store.get(
            execution_id,
        )

        if record is None:
            raise ValueError(
                "execution does not exist"
            )

        lease = await self._lease_store.get(
            execution_id,
        )

        decision = self._manager.decide(
            record=record,
            lease=lease,
            now=current_time,
        )

        await self._recovery_store.record(
            decision,
        )

        if decision.action is RecoveryAction.NOOP:
            return decision.action

        if decision.action is RecoveryAction.QUARANTINE:
            if record.state is not PersistentExecutionState.ABANDONED:
                raise ValueError(
                    "QUARANTINE requires ABANDONED execution"
                )

            return decision.action

        if decision.action is RecoveryAction.RECONCILE:
            return decision.action

        if decision.action is RecoveryAction.REQUEUE:
            if lease is not None:
                if not lease.is_expired(current_time):
                    raise ValueError(
                        "cannot requeue while ownership is active"
                    )

                await self._lease_store.release(
                    lease_id=lease.lease_id,
                    worker_id=lease.worker_id,
                )

            await self._execution_store.requeue(
                execution_id=record.execution_id,
                expected_revision=record.revision,
                occurred_at=current_time,
            )

            return decision.action

        raise ValueError(
            f"unsupported recovery action: {decision.action}"
        )

    @staticmethod
    def _normalize_now(
        now: datetime,
    ) -> datetime:
        """Require and normalize a timezone-aware recovery clock."""
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError(
                "now must be timezone-aware"
            )

        return now.astimezone(UTC)
