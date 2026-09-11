"""PostgreSQL integration tests for persistent execution runner."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from lyrion.capabilities.contracts import AuthorizationDecision
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
    PersistentExecutionState,
)
from lyrion.persistence.execution_lifecycle import (
    PersistentExecutionLifecycle,
)
from lyrion.persistence.execution_runner import (
    PersistentExecutionRunner,
)
from lyrion.persistence.sqlalchemy.execution_store import (
    SQLAlchemyExecutionStore,
)
from lyrion.persistence.sqlalchemy.lease_store import (
    SQLAlchemyLeaseStore,
)
from lyrion.persistence.sqlalchemy.models import (
    PersistentExecutionModel,
    RuntimeLeaseModel,
)

pytestmark = pytest.mark.integration


BASE_TIME = datetime(
    2026,
    8,
    31,
    12,
    0,
    tzinfo=UTC,
)


class FakeExecutionBackend:
    """Deterministic execution backend for integration testing."""

    def __init__(
        self,
        *,
        result: ExecutionResult,
    ) -> None:
        """Initialize the backend result."""
        self._result = result

    def execute(
        self,
        admission: ExecutionAdmission,
        plan: ExecutionPlan,
        sandbox: SandboxConfig,
        *,
        now: datetime | None = None,
    ) -> ExecutionResult:
        """Return the deterministic execution result."""
        del admission
        del plan
        del sandbox
        del now

        return self._result


class RaisingExecutionBackend:
    """Execution backend that raises before returning a result."""

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


def make_session_factory(
    database_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create a PostgreSQL session factory."""
    return async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


def make_request(
    *,
    execution_id: str,
    request_id: str,
) -> ExecutionRequest:
    """Create a valid execution request."""
    return ExecutionRequest(
        execution_id=execution_id,
        request_id=request_id,
        task_id=TaskId(
            f"task:{request_id}",
        ),
        capability_id="development.prepare",
        target_scope="lyrion/project/runner",
        operation="READ",
        authorization_reference=(
            f"authorization:{request_id}"
        ),
        policy_version="aegis-policy-v1",
        principal_id="lyrion-test",
        autonomy_level=AutonomyLevel.L1,
        risk_level=RiskLevel.LOW,
        resource_limits=ResourceLimits(),
        idempotency_key=IdempotencyKey(
            f"idem:{request_id}",
        ),
        correlation_id=CorrelationId(
            f"corr:{request_id}",
        ),
        requested_at=BASE_TIME,
        expires_at=BASE_TIME + timedelta(minutes=5),
    )


def make_admission(
    request: ExecutionRequest,
) -> ExecutionAdmission:
    """Create an admitted execution envelope."""
    return ExecutionAdmission(
        request_id=request.request_id,
        capability_id=request.capability_id,
        target_scope=request.target_scope,
        admitted=True,
        authorization_decision=AuthorizationDecision.ALLOWED,
        authorization_reason="integration test",
        policy_version=request.policy_version,
        admitted_at=BASE_TIME,
        execution_request=request,
    )


def make_plan(
    execution_id: str,
) -> ExecutionPlan:
    """Create an execution plan."""
    return ExecutionPlan(
        execution_id=execution_id,
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


def make_result(
    *,
    execution_id: str,
    request_id: str,
) -> ExecutionResult:
    """Create a completed execution result."""
    return ExecutionResult(
        execution_id=execution_id,
        request_id=request_id,
        status=ExecutionStatus.COMPLETED,
        started_at=BASE_TIME + timedelta(seconds=2),
        completed_at=BASE_TIME + timedelta(seconds=3),
        exit_code=0,
        output_ref=None,
        error_code=None,
        error_message=None,
        checkpoint_ref=None,
    )


def make_runner(
    database_engine: AsyncEngine,
    backend: FakeExecutionBackend | RaisingExecutionBackend,
) -> PersistentExecutionRunner:
    """Create a PostgreSQL-backed execution runner."""
    session_factory = make_session_factory(
        database_engine,
    )

    lifecycle = PersistentExecutionLifecycle(
        SQLAlchemyExecutionStore(session_factory),
        SQLAlchemyLeaseStore(session_factory),
    )

    return PersistentExecutionRunner(
        backend,
        lifecycle,
    )


@pytest.mark.asyncio
async def test_postgresql_runner_persists_full_lifecycle(
    database_engine: AsyncEngine,
) -> None:
    """The real runner must persist the complete lifecycle."""
    execution_id = (
        "execution:postgres:runner:001"
    )
    request_id = "request:postgres:runner:001"

    request = make_request(
        execution_id=execution_id,
        request_id=request_id,
    )

    runner = make_runner(
        database_engine,
        FakeExecutionBackend(
            result=make_result(
                execution_id=execution_id,
                request_id=request_id,
            ),
        ),
    )

    result = await runner.run(
        opportunity_id=OpportunityId(
            "opportunity:postgres:runner:001"
        ),
        admission=make_admission(request),
        plan=make_plan(execution_id),
        sandbox=make_sandbox(),
        worker_id="worker:postgres:runner:001",
        lease_id="lease:postgres:runner:001",
        now=BASE_TIME,
    )

    assert result.status is ExecutionStatus.COMPLETED

    async with make_session_factory(
        database_engine,
    )() as session:
        execution = await session.scalar(
            select(PersistentExecutionModel).where(
                PersistentExecutionModel.execution_id
                == execution_id,
            )
        )
        lease = await session.scalar(
            select(RuntimeLeaseModel).where(
                RuntimeLeaseModel.resource_id
                == execution_id,
            )
        )

    assert execution is not None
    assert execution.state == (
        PersistentExecutionState.COMPLETED.value
    )
    assert execution.revision == 4
    assert execution.worker_id == (
        "worker:postgres:runner:001"
    )
    assert execution.lease_id == (
        "lease:postgres:runner:001"
    )
    assert execution.started_at == BASE_TIME
    assert execution.completed_at == (
        BASE_TIME + timedelta(seconds=3)
    )
    assert lease is None


@pytest.mark.asyncio
async def test_postgresql_runner_persists_failure_then_reraises(
    database_engine: AsyncEngine,
) -> None:
    """Executor failure must leave durable FAILED state."""
    execution_id = (
        "execution:postgres:runner:002"
    )
    request_id = "request:postgres:runner:002"

    request = make_request(
        execution_id=execution_id,
        request_id=request_id,
    )

    runner = make_runner(
        database_engine,
        RaisingExecutionBackend(),
    )

    with pytest.raises(
        RuntimeError,
        match="executor failure",
    ):
        await runner.run(
            opportunity_id=OpportunityId(
                "opportunity:postgres:runner:002"
            ),
            admission=make_admission(request),
            plan=make_plan(execution_id),
            sandbox=make_sandbox(),
            worker_id="worker:postgres:runner:002",
            lease_id="lease:postgres:runner:002",
            now=BASE_TIME,
        )

    async with make_session_factory(
        database_engine,
    )() as session:
        execution = await session.scalar(
            select(PersistentExecutionModel).where(
                PersistentExecutionModel.execution_id
                == execution_id,
            )
        )

    assert execution is not None
    assert execution.state == (
        PersistentExecutionState.FAILED.value
    )
    assert execution.revision == 4
    assert execution.error_code == (
        "EXECUTION_EXCEPTION"
    )
    assert execution.error_message == (
        "Execution raised an unexpected exception."
    )
