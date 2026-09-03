"""Real PostgreSQL integration tests for persistent scheduled consumption."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from lyrion.capabilities.contracts import CapabilityOperation
from lyrion.capabilities.gateway import (
    CapabilityGateway,
    ExecutionAdmission,
)
from lyrion.core.types import (
    AutonomyLevel,
    CorrelationId,
    DecisionAction,
    EventId,
    ExecutionTarget,
    IdempotencyKey,
    OpportunityId,
    RiskLevel,
    TaskId,
)
from lyrion.events.models import (
    EventSensitivity,
    EventTrustLevel,
)
from lyrion.execution.contracts import (
    ExecutionPlan,
    ExecutionResult,
    ResourceLimits,
)
from lyrion.execution.executor import SecureExecutor
from lyrion.execution.sandbox import (
    EnvironmentMode,
    FilesystemMode,
    IsolationLevel,
    NetworkMode,
    SandboxConfig,
)
from lyrion.integration.persistent_scheduled_consumer import (
    PersistentScheduledPIAEConsumer,
)
from lyrion.integration.persistent_scheduler import (
    PersistentSchedulerCoordinator,
)
from lyrion.integration.proactive_execution import (
    CapabilityIntent,
    ProactiveExecutionCoordinator,
)
from lyrion.persistence.contracts import (
    PersistentExecutionState,
    PersistentSchedulerState,
)
from lyrion.persistence.sqlalchemy.models import (
    PersistentExecutionModel,
    PersistentSchedulerModel,
    RuntimeLeaseModel,
)
from lyrion.persistence.sqlalchemy.scheduler_store import (
    SQLAlchemySchedulerStore,
)
from lyrion.persistence.sqlalchemy.uow import (
    SQLAlchemyPersistenceUnitOfWork,
)
from lyrion.piae.action_loop import PIAEActionLoop
from lyrion.piae.contracts import (
    DecisionCandidate,
    DecisionConstraints,
    DecisionReason,
    Opportunity,
)
from lyrion.piae.controlled_queue_consumer import (
    ControlledQueueConsumer,
    ControlledQueueConsumerConfig,
    ControlledQueueCycleResult,
)
from lyrion.piae.engine import PIAEDecisionEngine
from lyrion.piae.opportunity_binding import (
    DeterministicOpportunityContextFactory,
)
from lyrion.piae.opportunity_consumer import OpportunityConsumer
from lyrion.piae.opportunity_queue import OpportunityQueue
from lyrion.piae.scheduled_consumer import CandidateFactory
from lyrion.security.authorization import AegisAuthorizationService
from lyrion.security.guards import AuthorizationGuard
from lyrion.security.policy import AegisPolicyEvaluator
from lyrion.security.replay import ReplayGuard
from lyrion.security.rules import default_aegis_policy

pytestmark = pytest.mark.integration


BASE_TIME = datetime(
    2026,
    8,
    31,
    12,
    0,
    tzinfo=UTC,
)


class FakeBoundedConsumer:
    """Deterministic bounded consumer for integration tests."""

    def __init__(self) -> None:
        """Initialize the consumer."""
        self.calls = 0

    def run_once(
        self,
        *,
        candidates_factory: CandidateFactory,
        now: datetime | None = None,
    ) -> ControlledQueueCycleResult:
        """Execute one deterministic bounded cycle."""
        del candidates_factory
        del now

        self.calls += 1

        return ControlledQueueCycleResult(
            items=(),
            stop_reason="QUEUE_EMPTY",
        )


def make_store(
    database_engine: AsyncEngine,
) -> SQLAlchemySchedulerStore:
    """Create a PostgreSQL-backed scheduler store."""
    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    return SQLAlchemySchedulerStore(
        session_factory,
    )


def make_opportunity(
    opportunity_id: str,
    *,
    now: datetime,
    urgency: float,
) -> Opportunity:
    """Create a valid executable opportunity."""
    return Opportunity(
        opportunity_id=OpportunityId(
            opportunity_id,
        ),
        correlation_id=CorrelationId(
            f"corr:{opportunity_id}",
        ),
        trigger_event_ids=(
            EventId(
                f"event:{opportunity_id}",
            ),
        ),
        relevant_state_ids=(),
        goal_context=(
            "persistent-scheduler-integration",
        ),
        title="Persistent scheduler opportunity",
        description="Real persistent scheduler integration test.",
        user_relevance=0.9,
        expected_benefit=0.9,
        interruption_cost=0.1,
        risk_score=0.1,
        reversibility=0.9,
        urgency=urgency,
        confidence=0.95,
        required_capabilities=(
            "development.prepare",
        ),
        required_autonomy_level=AutonomyLevel.L1,
        sensitivity=EventSensitivity.INTERNAL,
        trust_level=EventTrustLevel.SYSTEM,
        created_at=now,
        expires_at=None,
    )


def make_candidate(
    opportunity: Opportunity,
) -> tuple[DecisionCandidate, ...]:
    """Create a safe executable candidate for one opportunity."""
    return (
        DecisionCandidate(
            action=DecisionAction.EXECUTE,
            rationale=DecisionReason.EFFICIENCY,
            explanation=(
                f"Execute {opportunity.opportunity_id}."
            ),
            confidence=0.95,
            estimated_risk=RiskLevel.LOW,
            estimated_cost_units=0.5,
            estimated_runtime_seconds=1.0,
            requires_human_approval=False,
            has_external_side_effect=False,
            requires_network_access=False,
        ),
    )


def make_intent(
    opportunity: Opportunity,
) -> CapabilityIntent:
    """Create capability intent scoped to one opportunity."""
    opportunity_id = str(
        opportunity.opportunity_id,
    )

    return CapabilityIntent(
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope=(
            f"lyrion/project/{opportunity_id}"
        ),
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        task_id=TaskId(
            f"task:{opportunity_id}",
        ),
        risk_level=RiskLevel.LOW,
        justification=(
            f"opportunity:{opportunity_id}: "
            "persistent scheduler integration"
        ),
        idempotency_key=IdempotencyKey(
            f"idem:{opportunity_id}",
        ),
    )


def make_plan(
    opportunity: Opportunity,
) -> ExecutionPlan:
    """Create an execution plan matching opportunity identity."""
    decision_id = (
        f"opportunity:{opportunity.opportunity_id}"
    )

    return ExecutionPlan(
        execution_id=(
            f"execution:capreq:{decision_id}"
        ),
        execution_target=ExecutionTarget.REMOTE_SANDBOX,
        resource_limits=ResourceLimits(),
        network_access_allowed=False,
        external_side_effects_allowed=False,
        checkpoint_required=False,
    )


def make_sandbox() -> SandboxConfig:
    """Create the conservative sandbox required by the real consumer."""
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


def make_constraints() -> DecisionConstraints:
    """Create safe decision constraints."""
    return DecisionConstraints(
        max_risk_level=RiskLevel.LOW,
        requires_human_approval=False,
        allow_external_side_effects=False,
        allow_network_access=False,
        max_cost_units=10.0,
        max_runtime_seconds=30.0,
    )


def make_real_controlled_consumer(
    queue: OpportunityQueue,
) -> ControlledQueueConsumer:
    """Create the real bounded PIAE queue consumer."""
    policy = default_aegis_policy()

    gateway = CapabilityGateway(
        AegisAuthorizationService(
            AegisPolicyEvaluator(policy),
            AuthorizationGuard(policy.policy_version),
            ReplayGuard(),
        )
    )

    opportunity_consumer = OpportunityConsumer(
        queue,
        PIAEActionLoop(
            ProactiveExecutionCoordinator(
                piae=PIAEDecisionEngine(),
                gateway=gateway,
                executor=SecureExecutor(),
            )
        ),
    )

    context_factory = (
        DeterministicOpportunityContextFactory(
            autonomy_level=AutonomyLevel.L1,
            constraints=make_constraints(),
            intent_factory=make_intent,
            plan_factory=make_plan,
            sandbox_factory=(
                lambda _opportunity: make_sandbox()
            ),
        )
    )

    return ControlledQueueConsumer(
        queue,
        opportunity_consumer,
        context_factory,
        ControlledQueueConsumerConfig(
            max_opportunities_per_cycle=1,
        ),
    )


@pytest.mark.asyncio
async def test_persistent_scheduled_cycle_survives_restart(
    database_engine: AsyncEngine,
) -> None:
    """A completed scheduled cycle must survive coordinator restart."""
    store = make_store(database_engine)
    consumer = FakeBoundedConsumer()

    first = PersistentSchedulerCoordinator(
        store,
        scheduler_id="scheduler:integration:001",
    )

    await first.initialize()

    scheduled = PersistentScheduledPIAEConsumer(
        first,
        consumer,
    )

    result = await scheduled.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME,
    )

    assert result.ran is True
    assert consumer.calls == 1
    assert result.next_run_at is not None

    second = PersistentSchedulerCoordinator(
        make_store(database_engine),
        scheduler_id="scheduler:integration:001",
    )

    restored = await second.initialize()

    assert restored.next_run_at == result.next_run_at
    assert restored.state.value == (
        PersistentSchedulerState.READY.value
    )
    assert second.revision == 2


@pytest.mark.asyncio
async def test_persisted_future_schedule_blocks_restart_attempt(
    database_engine: AsyncEngine,
) -> None:
    """A restarted scheduler must remain blocked before its persisted deadline."""
    store = make_store(database_engine)

    coordinator = PersistentSchedulerCoordinator(
        store,
        scheduler_id="scheduler:integration:002",
    )

    await coordinator.initialize()
    await coordinator.mark_cycle_completed(
        now=BASE_TIME,
    )

    restarted = PersistentSchedulerCoordinator(
        make_store(database_engine),
        scheduler_id="scheduler:integration:002",
    )

    await restarted.initialize()

    consumer = FakeBoundedConsumer()
    scheduled = PersistentScheduledPIAEConsumer(
        restarted,
        consumer,
    )

    result = await scheduled.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME,
    )

    assert result.ran is False
    assert result.scheduler.reason == "NOT_DUE"
    assert consumer.calls == 0


@pytest.mark.asyncio
async def test_persisted_paused_scheduler_remains_paused_after_restart(
    database_engine: AsyncEngine,
) -> None:
    """PAUSED scheduler state must survive coordinator restart."""
    coordinator = PersistentSchedulerCoordinator(
        make_store(database_engine),
        scheduler_id="scheduler:integration:003",
    )

    await coordinator.initialize()
    persisted = await coordinator.pause()

    assert persisted.state is PersistentSchedulerState.PAUSED

    restarted = PersistentSchedulerCoordinator(
        make_store(database_engine),
        scheduler_id="scheduler:integration:003",
    )

    restored = await restarted.initialize()

    assert restored.state.value == (
        PersistentSchedulerState.PAUSED.value
    )
    assert restarted.revision == 2


def make_real_opportunity(
    opportunity_id: str,
    *,
    now: datetime,
) -> Opportunity:
    """Create a valid executable opportunity."""
    return Opportunity(
        opportunity_id=OpportunityId(opportunity_id),
        correlation_id=CorrelationId(
            f"corr:{opportunity_id}",
        ),
        trigger_event_ids=(
            EventId(
                f"event:{opportunity_id}",
            ),
        ),
        relevant_state_ids=(),
        goal_context=(
            "persistent-scheduler-integration",
        ),
        title="Persistent scheduler opportunity",
        description="Real persistent scheduler integration test.",
        user_relevance=0.9,
        expected_benefit=0.9,
        interruption_cost=0.1,
        risk_score=0.1,
        reversibility=0.9,
        urgency=0.9,
        confidence=0.95,
        required_capabilities=(
            "development.prepare",
        ),
        required_autonomy_level=AutonomyLevel.L1,
        sensitivity=EventSensitivity.INTERNAL,
        trust_level=EventTrustLevel.SYSTEM,
        created_at=now,
        expires_at=None,
    )


def make_real_candidate(
    opportunity: Opportunity,
) -> tuple[DecisionCandidate, ...]:
    """Create a safe executable candidate."""
    return (
        DecisionCandidate(
            action=DecisionAction.EXECUTE,
            rationale=DecisionReason.EFFICIENCY,
            explanation=(
                f"Execute {opportunity.opportunity_id}."
            ),
            confidence=0.95,
            estimated_risk=RiskLevel.LOW,
            estimated_cost_units=0.5,
            estimated_runtime_seconds=1.0,
            requires_human_approval=False,
            has_external_side_effect=False,
            requires_network_access=False,
        ),
    )


def make_real_intent(
    opportunity: Opportunity,
) -> CapabilityIntent:
    """Create capability intent scoped to the opportunity."""
    opportunity_id = str(
        opportunity.opportunity_id,
    )

    return CapabilityIntent(
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope=(
            f"lyrion/project/{opportunity_id}"
        ),
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        task_id=TaskId(
            f"task:{opportunity_id}",
        ),
        risk_level=RiskLevel.LOW,
        justification=(
            f"opportunity:{opportunity_id}: "
            "persistent scheduler integration"
        ),
        idempotency_key=IdempotencyKey(
            f"idem:{opportunity_id}",
        ),
    )


def make_real_plan(
    opportunity: Opportunity,
) -> ExecutionPlan:
    """Create an execution plan matching opportunity identity."""
    decision_id = (
        f"opportunity:{opportunity.opportunity_id}"
    )

    return ExecutionPlan(
        execution_id=(
            f"execution:capreq:{decision_id}"
        ),
        execution_target=ExecutionTarget.REMOTE_SANDBOX,
        resource_limits=ResourceLimits(),
        network_access_allowed=False,
        external_side_effects_allowed=False,
        checkpoint_required=False,
    )


def make_real_sandbox() -> SandboxConfig:
    """Create the conservative sandbox required by the real consumer."""
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


def make_real_constraints() -> DecisionConstraints:
    """Create safe decision constraints."""
    return DecisionConstraints(
        max_risk_level=RiskLevel.LOW,
        requires_human_approval=False,
        allow_external_side_effects=False,
        allow_network_access=False,
        max_cost_units=10.0,
        max_runtime_seconds=30.0,
    )


@pytest.mark.asyncio
async def test_postgresql_persistent_scheduled_cycle_commits_scheduler_and_execution(
    database_engine: AsyncEngine,
) -> None:
    """Successful persistent scheduled execution must commit atomically."""
    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    scheduler_id = (
        "scheduler:integration:transaction:commit:001"
    )
    opportunity_id = (
        "opp:persistent:transaction:commit:001"
    )

    store = make_store(
        database_engine,
    )

    coordinator = PersistentSchedulerCoordinator(
        store,
        scheduler_id=scheduler_id,
    )

    await coordinator.initialize()

    queue = OpportunityQueue()

    opportunity = make_real_opportunity(
        opportunity_id,
        now=BASE_TIME,
    )

    assert queue.enqueue(
        opportunity,
        now=BASE_TIME,
    ) is True

    consumer = make_real_controlled_consumer(
        queue,
    )

    scheduled = PersistentScheduledPIAEConsumer(
        coordinator,
        consumer,
    )

    result = await scheduled.run_once_persistent(
        candidates_factory=make_candidate,
        worker_id="worker:transaction:commit:001",
        lease_id_factory=lambda item_id: (
            f"lease:transaction:commit:{item_id}"
        ),
        now=BASE_TIME,
        uow_factory=lambda: SQLAlchemyPersistenceUnitOfWork(
            session_factory,
        ),
    )

    assert result.ran is True
    assert result.cycle is not None
    assert result.cycle.attempted_count == 1

    async with session_factory() as session:
        scheduler = await session.scalar(
            select(PersistentSchedulerModel).where(
                PersistentSchedulerModel.scheduler_id
                == scheduler_id,
            )
        )

        execution = await session.scalar(
            select(PersistentExecutionModel).where(
                PersistentExecutionModel.opportunity_id
                == opportunity_id,
            )
        )

        lease = await session.scalar(
            select(RuntimeLeaseModel).where(
                RuntimeLeaseModel.resource_id
                == "execution:capreq:opportunity:"
                f"{opportunity_id}",
            )
        )

    assert scheduler is not None
    assert scheduler.revision == 2

    assert execution is not None
    assert execution.state == (
        PersistentExecutionState.COMPLETED.value
    )

    assert lease is None


@pytest.mark.asyncio
async def test_postgresql_persistent_scheduled_cycle_rolls_back_scheduler_and_execution(
    database_engine: AsyncEngine,
) -> None:
    """Execution failure must roll back the entire scheduled transaction."""
    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    scheduler_id = (
        "scheduler:integration:transaction:rollback:001"
    )
    opportunity_id = (
        "opp:persistent:transaction:rollback:001"
    )

    store = make_store(
        database_engine,
    )

    scheduler = PersistentSchedulerCoordinator(
        store,
        scheduler_id=scheduler_id,
    )

    await scheduler.initialize()

    assert scheduler.revision == 1

    queue = OpportunityQueue()

    opportunity = make_real_opportunity(
        opportunity_id,
        now=BASE_TIME,
    )

    assert queue.enqueue(
        opportunity,
        now=BASE_TIME,
    ) is True

    policy = default_aegis_policy()

    gateway = CapabilityGateway(
        AegisAuthorizationService(
            AegisPolicyEvaluator(policy),
            AuthorizationGuard(policy.policy_version),
            ReplayGuard(),
        )
    )

    class FailingSecureExecutor(SecureExecutor):
        """Secure-execution backend that fails deterministically."""

        def execute(
            self,
            admission: ExecutionAdmission,
            plan: ExecutionPlan,
            sandbox: SandboxConfig,
            *,
            now: datetime | None = None,
        ) -> ExecutionResult:
            """Fail after admission has succeeded."""
            del admission
            del plan
            del sandbox
            del now

            raise RuntimeError(
                "forced persistent transaction failure",
            )

    opportunity_consumer = OpportunityConsumer(
        queue,
        PIAEActionLoop(
            ProactiveExecutionCoordinator(
                piae=PIAEDecisionEngine(),
                gateway=gateway,
                executor=FailingSecureExecutor(),
            )
        ),
    )

    context_factory = (
        DeterministicOpportunityContextFactory(
            autonomy_level=AutonomyLevel.L1,
            constraints=make_constraints(),
            intent_factory=make_intent,
            plan_factory=make_plan,
            sandbox_factory=lambda _opportunity: make_sandbox(),
        )
    )

    consumer = ControlledQueueConsumer(
        queue,
        opportunity_consumer,
        context_factory,
        ControlledQueueConsumerConfig(
            max_opportunities_per_cycle=1,
        ),
    )

    scheduled = PersistentScheduledPIAEConsumer(
        scheduler,
        consumer,
    )

    execution_id = (
        f"execution:capreq:opportunity:{opportunity_id}"
    )
    lease_id = (
        f"lease:transaction:rollback:{opportunity_id}"
    )

    with pytest.raises(
        RuntimeError,
        match="forced persistent transaction failure",
    ):
        await scheduled.run_once_persistent(
            candidates_factory=make_candidate,
            worker_id="worker:transaction:rollback:001",
            lease_id_factory=lambda _item_id: lease_id,
            now=BASE_TIME,
            uow_factory=lambda: SQLAlchemyPersistenceUnitOfWork(
                session_factory,
            ),
        )

    async with session_factory() as session:
        persisted_scheduler = await session.scalar(
            select(PersistentSchedulerModel).where(
                PersistentSchedulerModel.scheduler_id
                == scheduler_id,
            )
        )

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

    assert persisted_scheduler is not None
    assert persisted_scheduler.revision == 1
    assert persisted_scheduler.next_run_at is None

    assert execution is None
    assert lease is None
