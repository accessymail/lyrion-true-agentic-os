"""Persistence-aware execution lifecycle runner."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol

from lyrion.capabilities.gateway import ExecutionAdmission
from lyrion.core.types import OpportunityId
from lyrion.execution.contracts import (
    ExecutionPlan,
    ExecutionResult,
    ExecutionStatus,
)
from lyrion.execution.sandbox import SandboxConfig
from lyrion.persistence.contracts import (
    PersistentExecutionState,
)
from lyrion.persistence.execution_lifecycle import (
    PersistentExecutionLifecycle,
)
from lyrion.persistence.protocols import ExecutionStore, LeaseStore


class ExecutionBackend(Protocol):
    """Minimal execution backend required by the persistence runner."""

    def execute(
        self,
        admission: ExecutionAdmission,
        plan: ExecutionPlan,
        sandbox: SandboxConfig,
        *,
        now: datetime | None = None,
    ) -> ExecutionResult:
        """Execute one admitted request."""
        

class PersistentExecutionRunner:
    """Run admitted execution with durable lifecycle state."""

    def __init__(
        self,
        coordinator: ExecutionBackend,
        lifecycle: PersistentExecutionLifecycle,
    ) -> None:
        """Initialize the persistent execution runner."""
        self._coordinator = coordinator
        self._lifecycle = lifecycle

    @classmethod
    def from_stores(
        cls,
        coordinator: ExecutionBackend,
        *,
        execution_store: ExecutionStore,
        lease_store: LeaseStore,
    ) -> PersistentExecutionRunner:
        """Create a runner backed by already-bound persistence stores."""
        return cls(
            coordinator,
            PersistentExecutionLifecycle(
                execution_store,
                lease_store,
            ),
        )

    async def run(
        self,
        *,
        opportunity_id: OpportunityId,
        admission: ExecutionAdmission,
        plan: ExecutionPlan,
        sandbox: SandboxConfig,
        worker_id: str,
        lease_id: str,
        now: datetime,
        lease_duration: timedelta = timedelta(minutes=5),
    ) -> ExecutionResult:
        """Execute one admitted request through the durable lifecycle."""
        current_time = self._normalize_now(now)

        request = admission.execution_request

        queued = await self._lifecycle.create_queued(
            request=request,
            opportunity_id=opportunity_id,
        )

        claimed = await self._lifecycle.claim(
            execution_id=queued.execution_id,
            worker_id=worker_id,
            lease_id=lease_id,
            claimed_at=current_time,
            expires_at=current_time + lease_duration,
            expected_revision=queued.revision,
        )

        executing = await self._lifecycle.begin(
            execution=claimed,
            worker_id=worker_id,
            lease_id=lease_id,
            started_at=current_time,
        )

        try:
            result = self._coordinator.execute(
                admission,
                plan,
                sandbox,
                now=current_time,
            )
        except Exception:
            await self._lifecycle.finish(
                execution=executing,
                worker_id=worker_id,
                lease_id=lease_id,
                target_state=PersistentExecutionState.FAILED,
                occurred_at=current_time,
                error_code="EXECUTION_EXCEPTION",
                error_message="Execution raised an unexpected exception.",
            )
            raise

        terminal_state = self._map_result_status(
            result.status,
        )

        current_record = await self._lifecycle.get(
            request.execution_id,
        )

        if current_record is None:
            raise RuntimeError(
                "durable execution disappeared during execution"
            )

        await self._lifecycle.finish(
            execution=current_record,
            worker_id=worker_id,
            lease_id=lease_id,
            target_state=terminal_state,
            occurred_at=(
                result.completed_at or current_time
            ),
            checkpoint_ref=result.checkpoint_ref,
            error_code=result.error_code,
            error_message=result.error_message,
        )

        return result

    @staticmethod
    def _map_result_status(
        status: ExecutionStatus,
    ) -> PersistentExecutionState:
        """Map known execution results to durable terminal states."""
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
        }

        try:
            return mapping[status]
        except KeyError as exc:
            raise ValueError(
                f"unsupported terminal execution status: {status}"
            ) from exc

    @staticmethod
    def _normalize_now(
        now: datetime,
    ) -> datetime:
        """Require and normalize a timezone-aware execution clock."""
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError(
                "now must be timezone-aware"
            )

        return now.astimezone(UTC)
