"""Durable execution lifecycle orchestration."""

from __future__ import annotations

from datetime import UTC, datetime

from lyrion.core.types import OpportunityId
from lyrion.execution.contracts import ExecutionRequest
from lyrion.persistence.contracts import (
    PersistentExecutionRecord,
    PersistentExecutionState,
    RuntimeLease,
)
from lyrion.persistence.protocols import (
    ExecutionStore,
    LeaseStore,
)


class PersistentExecutionLifecycle:
    """Coordinate execution persistence with exclusive runtime ownership."""

    def __init__(
        self,
        execution_store: ExecutionStore,
        lease_store: LeaseStore,
    ) -> None:
        """Initialize durable execution lifecycle orchestration."""
        self._execution_store = execution_store
        self._lease_store = lease_store

    async def create_queued(
        self,
        *,
        request: ExecutionRequest,
        opportunity_id: OpportunityId,
    ) -> PersistentExecutionRecord:
        """Create the initial durable QUEUED execution record."""
        record = PersistentExecutionRecord(
            execution_id=request.execution_id,
            request_id=request.request_id,
            opportunity_id=opportunity_id,
            task_id=request.task_id,
            idempotency_key=request.idempotency_key,
            state=PersistentExecutionState.QUEUED,
            created_at=request.requested_at.astimezone(UTC),
            revision=1,
        )

        return await self._execution_store.create(record)

    async def claim(
        self,
        *,
        execution_id: str,
        worker_id: str,
        lease_id: str,
        claimed_at: datetime,
        expires_at: datetime,
        expected_revision: int = 1,
    ) -> PersistentExecutionRecord:
        """Acquire exclusive ownership and claim the execution."""
        lease = await self._lease_store.acquire(
            resource_id=execution_id,
            worker_id=worker_id,
            lease_id=lease_id,
            acquired_at=claimed_at,
            expires_at=expires_at,
        )

        if lease is None:
            raise RuntimeError(
                "execution ownership could not be acquired"
            )

        claimed = await self._execution_store.claim(
            execution_id=execution_id,
            worker_id=worker_id,
            lease_id=lease.lease_id,
            claimed_at=claimed_at,
            expected_revision=expected_revision,
        )

        if claimed is None:
            await self._lease_store.release(
                lease_id=lease.lease_id,
                worker_id=worker_id,
            )
            raise RuntimeError(
                "execution could not be claimed"
            )

        return claimed

    async def begin(
        self,
        *,
        execution: PersistentExecutionRecord,
        worker_id: str,
        lease_id: str,
        started_at: datetime,
    ) -> PersistentExecutionRecord:
        """Transition a claimed execution into EXECUTING."""
        if execution.state is not PersistentExecutionState.CLAIMED:
            raise ValueError(
                "execution must be CLAIMED before begin"
            )

        return await self._execution_store.transition(
            execution_id=execution.execution_id,
            worker_id=worker_id,
            lease_id=lease_id,
            expected_revision=execution.revision,
            target_state=PersistentExecutionState.EXECUTING,
            occurred_at=started_at,
        )

    async def finish(
        self,
        *,
        execution: PersistentExecutionRecord,
        worker_id: str,
        lease_id: str,
        target_state: PersistentExecutionState,
        occurred_at: datetime,
        checkpoint_ref: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> PersistentExecutionRecord:
        """Transition an executing record to a terminal state."""
        terminal_states = {
            PersistentExecutionState.COMPLETED,
            PersistentExecutionState.FAILED,
            PersistentExecutionState.CANCELLED,
            PersistentExecutionState.ABANDONED,
        }

        if target_state not in terminal_states:
            raise ValueError(
                "finish requires a terminal execution state"
            )

        if execution.state is not PersistentExecutionState.EXECUTING:
            raise ValueError(
                "execution must be EXECUTING before finish"
            )

        result = await self._execution_store.transition(
            execution_id=execution.execution_id,
            worker_id=worker_id,
            lease_id=lease_id,
            expected_revision=execution.revision,
            target_state=target_state,
            occurred_at=occurred_at,
            checkpoint_ref=checkpoint_ref,
            error_code=error_code,
            error_message=error_message,
        )

        await self._lease_store.release(
            lease_id=lease_id,
            worker_id=worker_id,
        )

        return result

    async def get(
        self,
        execution_id: str,
    ) -> PersistentExecutionRecord | None:
        """Return the current durable execution state."""
        return await self._execution_store.get(execution_id)

    async def get_lease(
        self,
        execution_id: str,
    ) -> RuntimeLease | None:
        """Return the ownership lease for an execution."""
        return await self._lease_store.get(execution_id)
