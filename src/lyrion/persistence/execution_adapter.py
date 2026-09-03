"""Bridge secure execution results into durable execution persistence."""

from __future__ import annotations

from datetime import UTC

from lyrion.core.types import OpportunityId
from lyrion.execution.contracts import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)
from lyrion.persistence.contracts import (
    PersistentExecutionRecord,
    PersistentExecutionState,
)
from lyrion.persistence.protocols import ExecutionStore


class ExecutionPersistenceAdapter:
    """Persist execution outcomes without inventing execution identity."""

    def __init__(
        self,
        store: ExecutionStore,
    ) -> None:
        """Initialize the persistence adapter."""
        self._store = store

    @property
    def store(self) -> ExecutionStore:
        """Return the underlying execution store."""
        return self._store

    async def record_result(
        self,
        *,
        opportunity_id: OpportunityId,
        request: ExecutionRequest,
        result: ExecutionResult,
    ) -> PersistentExecutionRecord:
        """Create a durable terminal execution record."""
        if request.execution_id != result.execution_id:
            raise ValueError(
                "request and result execution_id must match"
            )

        if request.request_id != result.request_id:
            raise ValueError(
                "request and result request_id must match"
            )

        if result.started_at < request.requested_at:
            raise ValueError(
                "execution result cannot start before request"
            )

        state = self._map_status(result.status)

        record = PersistentExecutionRecord(
            execution_id=request.execution_id,
            request_id=request.request_id,
            opportunity_id=opportunity_id,
            task_id=request.task_id,
            idempotency_key=request.idempotency_key,
            state=state,
            created_at=request.requested_at.astimezone(UTC),
            started_at=result.started_at.astimezone(UTC),
            completed_at=(
                result.completed_at.astimezone(UTC)
                if result.completed_at is not None
                else None
            ),
            checkpoint_ref=result.checkpoint_ref,
            error_code=result.error_code,
            error_message=result.error_message,
            revision=1,
        )

        return await self._store.create(record)

    @staticmethod
    def _map_status(
        status: ExecutionStatus,
    ) -> PersistentExecutionState:
        """Map known execution outcomes to durable states."""
        mapping = {
            ExecutionStatus.COMPLETED: (
                PersistentExecutionState.COMPLETED
            ),
            ExecutionStatus.FAILED: (
                PersistentExecutionState.FAILED
            ),
            ExecutionStatus.CANCELLED: (
                PersistentExecutionState.CANCELLED
            ),
            ExecutionStatus.TERMINATED: (
                PersistentExecutionState.ABANDONED
            ),
            ExecutionStatus.TIMED_OUT: (
                PersistentExecutionState.FAILED
            ),
            ExecutionStatus.DENIED: (
                PersistentExecutionState.FAILED
            ),
            ExecutionStatus.ADMITTED: (
                PersistentExecutionState.EXECUTING
            ),
            ExecutionStatus.RUNNING: (
                PersistentExecutionState.EXECUTING
            ),
        }

        try:
            return mapping[status]
        except KeyError as exc:
            raise ValueError(
                f"unsupported execution status: {status}"
            ) from exc
