"""Tests for persistence-aware secure execution orchestration."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest

from lyrion.capabilities.contracts import (
    AuthorizationDecision,
    CapabilityOperation,
)
from lyrion.capabilities.gateway import ExecutionAdmission
from lyrion.core.types import (
    AutonomyLevel,
    CorrelationId,
    ExecutionTarget,
    IdempotencyKey,
    OpportunityId,
    RiskLevel,
    TaskId,
)
from lyrion.execution.contracts import (
    ExecutionPlan,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ResourceLimits,
)
from lyrion.execution.sandbox import (
    EnvironmentMode,
    FilesystemMode,
    IsolationLevel,
    NetworkMode,
    SandboxConfig,
)
from lyrion.persistence.contracts import (
    PersistentExecutionRecord,
    PersistentExecutionState,
    RuntimeLease,
)
from lyrion.persistence.execution_lifecycle import (
    PersistentExecutionLifecycle,
)
from lyrion.persistence.execution_runner import (
    PersistentExecutionRunner,
)

BASE_TIME = datetime(
    2026,
    8,
    31,
    12,
    0,
    tzinfo=UTC,
)


class FakeExecutionStore:
    """Execution-store test double."""

    def __init__(self) -> None:
        """Initialize state."""
        self.record: PersistentExecutionRecord | None = None

    async def create(
        self,
        record: PersistentExecutionRecord,
    ) -> PersistentExecutionRecord:
        """Persist initial execution."""
        self.record = record
        return record

    async def get(
        self,
        execution_id: str,
    ) -> PersistentExecutionRecord | None:
        """Return the execution."""
        if self.record is None:
            return None

        if self.record.execution_id != execution_id:
            return None

        return self.record

    async def claim(
        self,
        *,
        execution_id: str,
        worker_id: str,
        lease_id: str,
        claimed_at: datetime,
        expected_revision: int,
    ) -> PersistentExecutionRecord | None:
        """Claim the execution."""
        if self.record is None:
            return None

        if self.record.execution_id != execution_id:
            return None

        if self.record.revision != expected_revision:
            return None

        self.record = self.record.model_copy(
            update={
                "state": PersistentExecutionState.CLAIMED,
                "worker_id": worker_id,
                "lease_id": lease_id,
                "claimed_at": claimed_at,
                "revision": expected_revision + 1,
            }
        )

        return self.record

    async def transition(
        self,
        *,
        execution_id: str,
        worker_id: str,
        lease_id: str,
        expected_revision: int,
        target_state: PersistentExecutionState,
        occurred_at: datetime,
        checkpoint_ref: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> PersistentExecutionRecord:
        """Transition the execution."""
        assert self.record is not None
        assert self.record.execution_id == execution_id
        assert self.record.worker_id == worker_id
        assert self.record.lease_id == lease_id
        assert self.record.revision == expected_revision

        update: dict[str, object] = {
            "state": target_state,
            "revision": expected_revision + 1,
        }

        if target_state is PersistentExecutionState.EXECUTING:
            update["started_at"] = occurred_at

        if target_state in {
            PersistentExecutionState.COMPLETED,
            PersistentExecutionState.FAILED,
            PersistentExecutionState.CANCELLED,
            PersistentExecutionState.ABANDONED,
        }:
            update["completed_at"] = occurred_at

        if checkpoint_ref is not None:
            update["checkpoint_ref"] = checkpoint_ref

        if error_code is not None:
            update["error_code"] = error_code

        if error_message is not None:
            update["error_message"] = error_message

        self.record = self.record.model_copy(
            update=update
        )

        return self.record

    async def requeue(
        self,
        *,
        execution_id: str,
        expected_revision: int,
        occurred_at: datetime,
    ) -> PersistentExecutionRecord:
        """Unused protocol operation."""
        del execution_id
        del expected_revision
        del occurred_at
        raise NotImplementedError

    async def find_recoverable(
        self,
        *,
        states: Sequence[PersistentExecutionState],
        now: datetime,
        limit: int,
    ) -> Sequence[PersistentExecutionRecord]:
        """Unused protocol operation."""
        del states
        del now
        del limit
        raise NotImplementedError


class FakeLeaseStore:
    """Lease-store test double."""

    def __init__(self) -> None:
        """Initialize lease state."""
        self.released: tuple[str, str] | None = None

    async def acquire(
        self,
        *,
        resource_id: str,
        worker_id: str,
        lease_id: str,
        acquired_at: datetime,
        expires_at: datetime,
    ) -> RuntimeLease | None:
        """Return a deterministic lease."""

        return RuntimeLease(
            lease_id=lease_id,
            resource_id=resource_id,
            worker_id=worker_id,
            acquired_at=acquired_at,
            expires_at=expires_at,
        )

    async def get(
        self,
        resource_id: str,
    ) -> RuntimeLease | None:
        """Unused lease lookup."""
        del resource_id
        return None

    async def renew(
        self,
        *,
        lease_id: str,
        worker_id: str,
        expected_revision: int,
        expires_at: datetime,
    ) -> RuntimeLease:
        """Unused lease renewal."""
        del lease_id
        del worker_id
        del expected_revision
        del expires_at
        raise NotImplementedError

    async def release(
        self,
        *,
        lease_id: str,
        worker_id: str,
    ) -> None:
        """Release the lease."""
        self.released = (lease_id, worker_id)

    async def find_expired(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> Sequence[RuntimeLease]:
        """Unused expired lookup."""
        del now
        del limit
        raise NotImplementedError


class FakeExecutionCoordinator:
    """Deterministic secure-execution coordinator."""

    def __init__(
        self,
        result: ExecutionResult,
    ) -> None:
        """Initialize the configured result."""
        self.result = result

    def execute(
        self,
        admission: ExecutionAdmission,
        plan: ExecutionPlan,
        sandbox: SandboxConfig,
        *,
        now: datetime | None = None,
    ) -> ExecutionResult:
        """Return the configured result."""
        del admission
        del plan
        del sandbox
        del now
        return self.result


def make_request() -> ExecutionRequest:
    """Create a valid request."""
    return ExecutionRequest(
        execution_id="execution:runner:001",
        request_id="request:runner:001",
        task_id=TaskId("task:runner:001"),
        capability_id="development.prepare",
        target_scope="lyrion/project/runner",
        operation=CapabilityOperation.READ.value,
        authorization_reference="authorization:runner:001",
        policy_version="aegis-policy-v1",
        principal_id="lyrion-test",
        autonomy_level=AutonomyLevel.L1,
        risk_level=RiskLevel.LOW,
        resource_limits=ResourceLimits(),
        idempotency_key=IdempotencyKey(
            "idem:runner:001",
        ),
        correlation_id=CorrelationId("corr:runner:001"),
        requested_at=BASE_TIME,
        expires_at=BASE_TIME + timedelta(minutes=5),
    )


def make_admission() -> ExecutionAdmission:
    """Create a valid execution admission."""
    request = make_request()

    return ExecutionAdmission(
        request_id=request.request_id,
        capability_id=request.capability_id,
        target_scope=request.target_scope,
        admitted=True,
        authorization_decision=AuthorizationDecision.ALLOWED,
        authorization_reason="test",
        policy_version=request.policy_version,
        admitted_at=BASE_TIME,
        execution_request=request,
    )


def make_result(
    *,
    status: ExecutionStatus = ExecutionStatus.COMPLETED,
) -> ExecutionResult:
    """Create a deterministic execution result."""
    completed_at = (
        BASE_TIME + timedelta(seconds=3)
        if status in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.TERMINATED,
        }
        else None
    )

    return ExecutionResult(
        execution_id="execution:runner:001",
        request_id="request:runner:001",
        status=status,
        started_at=BASE_TIME + timedelta(seconds=2),
        completed_at=completed_at,
        exit_code=0 if status is ExecutionStatus.COMPLETED else None,
        output_ref=None,
        error_code=(
            "EXECUTION_FAILED"
            if status is ExecutionStatus.FAILED
            else None
        ),
        error_message=(
            "execution failed"
            if status is ExecutionStatus.FAILED
            else None
        ),
        checkpoint_ref=None,
    )


def make_plan() -> ExecutionPlan:
    """Create a valid execution plan."""
    return ExecutionPlan(
        execution_id="execution:runner:001",
        execution_target=ExecutionTarget.REMOTE_SANDBOX,
        resource_limits=ResourceLimits(),
        network_access_allowed=False,
        external_side_effects_allowed=False,
        checkpoint_required=False,
    )


def make_sandbox() -> SandboxConfig:
    """Create a conservative sandbox."""
    return SandboxConfig(
        execution_target=ExecutionTarget.REMOTE_SANDBOX,
        filesystem_mode=FilesystemMode.ISOLATED,
        network_mode=NetworkMode.DISABLED,
        environment_mode=EnvironmentMode.EMPTY,
        isolation_level=IsolationLevel.STRICT,
        writable_paths=(),
        read_only_paths=(),
        allowed_environment_keys=(),
        resource_limits=ResourceLimits(),
        allow_process_creation=False,
        allow_privileged_operations=False,
    )


@pytest.mark.asyncio
async def test_runner_persists_full_execution_lifecycle() -> None:
    """Runner must persist QUEUED through terminal execution."""
    execution_store = FakeExecutionStore()
    lease_store = FakeLeaseStore()

    lifecycle = PersistentExecutionLifecycle(
        execution_store,
        lease_store,
    )

    coordinator = FakeExecutionCoordinator(
        make_result(),
    )

    runner = PersistentExecutionRunner(
        coordinator,
        lifecycle,
    )

    result = await runner.run(
        opportunity_id=OpportunityId(
            "opportunity:runner:001"
        ),
        admission=make_admission(),
        plan=make_plan(),
        sandbox=make_sandbox(),
        worker_id="worker:runner:001",
        lease_id="lease:runner:001",
        now=BASE_TIME,
    )

    assert result.status is ExecutionStatus.COMPLETED
    assert execution_store.record is not None
    assert execution_store.record.state is (
        PersistentExecutionState.COMPLETED
    )
    assert execution_store.record.revision == 4
    assert execution_store.record.worker_id == "worker:runner:001"
    assert execution_store.record.lease_id == "lease:runner:001"
    assert execution_store.record.started_at == BASE_TIME
    assert execution_store.record.completed_at == (
        BASE_TIME + timedelta(seconds=3)
    )
    assert lease_store.released == (
        "lease:runner:001",
        "worker:runner:001",
    )


@pytest.mark.asyncio
async def test_runner_persists_failed_execution_before_reraising() -> None:
    """Executor exceptions must produce durable FAILED state."""
    class RaisingCoordinator:
        """Secure execution coordinator that raises."""

        def execute(
            self,
            admission: ExecutionAdmission,
            plan: ExecutionPlan,
            sandbox: SandboxConfig,
            *,
            now: datetime | None = None,
        ) -> ExecutionResult:
            """Raise a deterministic execution error."""
            del admission
            del plan
            del sandbox
            del now
            raise RuntimeError("executor failure")

    execution_store = FakeExecutionStore()
    lease_store = FakeLeaseStore()

    runner = PersistentExecutionRunner(
        RaisingCoordinator(),
        PersistentExecutionLifecycle(
            execution_store,
            lease_store,
        ),
    )

    with pytest.raises(RuntimeError, match="executor failure"):
        await runner.run(
            opportunity_id=OpportunityId(
                "opportunity:runner:001"
            ),
            admission=make_admission(),
            plan=make_plan(),
            sandbox=make_sandbox(),
            worker_id="worker:runner:001",
            lease_id="lease:runner:001",
            now=BASE_TIME,
        )

    assert execution_store.record is not None
    assert execution_store.record.state is (
        PersistentExecutionState.FAILED
    )
    assert execution_store.record.revision == 4
    assert execution_store.record.error_code == (
        "EXECUTION_EXCEPTION"
    )
    assert lease_store.released == (
        "lease:runner:001",
        "worker:runner:001",
    )
