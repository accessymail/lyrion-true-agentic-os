"""PostgreSQL tests for UoW-bound persistent execution."""

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
from lyrion.persistence.contracts import PersistentExecutionState
from lyrion.persistence.execution_runner import (
    PersistentExecutionRunner,
)
from lyrion.persistence.sqlalchemy.models import (
    PersistentExecutionModel,
    RuntimeLeaseModel,
)
from lyrion.persistence.sqlalchemy.uow import (
    SQLAlchemyPersistenceUnitOfWork,
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
    """Deterministic successful execution backend."""

    def __init__(
        self,
        *,
        fail_after_execution: bool = False,
    ) -> None:
        """Initialize backend behavior."""
        self.fail_after_execution = fail_after_execution

    def execute(
        self,
        admission: ExecutionAdmission,
        plan: ExecutionPlan,
        sandbox: SandboxConfig,
        *,
        now: datetime | None = None,
    ) -> ExecutionResult:
        """Return a deterministic successful result."""
        del plan
        del sandbox
        del now

        request = admission.execution_request

        return ExecutionResult(
            execution_id=request.execution_id,
            request_id=request.request_id,
            status=ExecutionStatus.COMPLETED,
            started_at=BASE_TIME + timedelta(seconds=2),
            completed_at=BASE_TIME + timedelta(seconds=3),
            exit_code=0,
            output_ref=None,
            error_code=None,
            error_message=None,
            checkpoint_ref=None,
        )


def make_session_factory(
    database_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create a session factory."""
    return async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


def make_request() -> ExecutionRequest:
    """Create a valid execution request."""
    return ExecutionRequest(
        execution_id="execution:uow:runner:001",
        request_id="request:uow:runner:001",
        task_id=TaskId("task:uow:runner:001"),
        capability_id="development.prepare",
        target_scope="lyrion/project/uow-runner",
        operation="READ",
        authorization_reference=(
            "authorization:uow:runner:001"
        ),
        policy_version="aegis-policy-v1",
        principal_id="lyrion-test",
        autonomy_level=AutonomyLevel.L1,
        risk_level=RiskLevel.LOW,
        resource_limits=ResourceLimits(),
        idempotency_key=IdempotencyKey(
            "idem:uow:runner:001"
        ),
        correlation_id=CorrelationId(
            "corr:uow:runner:001"
        ),
        requested_at=BASE_TIME,
        expires_at=BASE_TIME + timedelta(minutes=5),
    )


def make_admission(
    request: ExecutionRequest,
) -> ExecutionAdmission:
    """Create an admitted execution."""
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


@pytest.mark.asyncio
async def test_uow_bound_runner_commits_execution(
    database_engine: AsyncEngine,
) -> None:
    """A UoW-bound runner must commit execution with the UoW."""
    session_factory = make_session_factory(
        database_engine,
    )

    request = make_request()

    async with SQLAlchemyPersistenceUnitOfWork(
        session_factory,
    ) as uow:
        runner = PersistentExecutionRunner.from_stores(
            FakeExecutionBackend(),
            execution_store=uow.executions,
            lease_store=uow.leases,
        )

        result = await runner.run(
            opportunity_id=OpportunityId(
                "opportunity:uow:runner:001"
            ),
            admission=make_admission(request),
            plan=make_plan(request.execution_id),
            sandbox=make_sandbox(),
            worker_id="worker:uow:runner:001",
            lease_id="lease:uow:runner:001",
            now=BASE_TIME,
        )

        assert result.status is ExecutionStatus.COMPLETED

    async with session_factory() as session:
        execution = await session.scalar(
            select(PersistentExecutionModel).where(
                PersistentExecutionModel.execution_id
                == request.execution_id,
            )
        )
        lease = await session.scalar(
            select(RuntimeLeaseModel).where(
                RuntimeLeaseModel.resource_id
                == request.execution_id,
            )
        )

    assert execution is not None
    assert execution.state == (
        PersistentExecutionState.COMPLETED.value
    )
    assert execution.revision == 4
    assert lease is None


@pytest.mark.asyncio
async def test_uow_bound_runner_rolls_back_execution(
    database_engine: AsyncEngine,
) -> None:
    """An exception escaping the UoW must roll back execution state."""
    session_factory = make_session_factory(
        database_engine,
    )

    request = make_request().model_copy(
        update={
            "execution_id": "execution:uow:runner:002",
            "request_id": "request:uow:runner:002",
            "task_id": TaskId("task:uow:runner:002"),
            "idempotency_key": IdempotencyKey(
                "idem:uow:runner:002"
            ),
            "correlation_id": CorrelationId(
                "corr:uow:runner:002"
            ),
        }
    )

    class FailingBackend:
        """Backend that fails after durable execution setup."""

        def execute(
            self,
            admission: ExecutionAdmission,
            plan: ExecutionPlan,
            sandbox: SandboxConfig,
            *,
            now: datetime | None = None,
        ) -> ExecutionResult:
            """Raise a deterministic failure."""
            del admission
            del plan
            del sandbox
            del now
            raise RuntimeError("force uow rollback")

    with pytest.raises(
        RuntimeError,
        match="force uow rollback",
    ):
        async with SQLAlchemyPersistenceUnitOfWork(
            session_factory,
        ) as uow:
            runner = PersistentExecutionRunner.from_stores(
                FailingBackend(),
                execution_store=uow.executions,
                lease_store=uow.leases,
            )

            await runner.run(
                opportunity_id=OpportunityId(
                    "opportunity:uow:runner:002"
                ),
                admission=make_admission(request),
                plan=make_plan(request.execution_id),
                sandbox=make_sandbox(),
                worker_id="worker:uow:runner:002",
                lease_id="lease:uow:runner:002",
                now=BASE_TIME,
            )

    async with session_factory() as session:
        execution = await session.scalar(
            select(PersistentExecutionModel).where(
                PersistentExecutionModel.execution_id
                == request.execution_id,
            )
        )
        lease = await session.scalar(
            select(RuntimeLeaseModel).where(
                RuntimeLeaseModel.resource_id
                == request.execution_id,
            )
        )

    assert execution is None
    assert lease is None
