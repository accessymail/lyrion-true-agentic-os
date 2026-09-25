"""R097 PostgreSQL/UoW atomicity integration tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from lyrion.core.types import (
    AutonomyLevel,
    CorrelationId,
    EventId,
    OpportunityId,
)
from lyrion.events.models import EventSensitivity, EventTrustLevel
from lyrion.piae.contracts import Opportunity
from lyrion.persistence.opportunity_persistence import (
    OpportunityPersistenceCoordinator,
)
from lyrion.persistence.sqlalchemy.models import (
    PersistentOpportunityModel,
    OpportunityRecoveryContextModel,
)
from lyrion.persistence.sqlalchemy.uow import (
    SQLAlchemyPersistenceUnitOfWork,
)


pytestmark = pytest.mark.integration


BASE_TIME = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


def make_opportunity(opportunity_id: str) -> Opportunity:
    return Opportunity(
        opportunity_id=OpportunityId(opportunity_id),
        correlation_id=CorrelationId(
            f"corr:{opportunity_id}",
        ),
        trigger_event_ids=(
            EventId(f"event:{opportunity_id}"),
        ),
        relevant_state_ids=(
            f"state:{opportunity_id}",
        ),
        goal_context=("R097 atomicity validation",),
        title="R097 atomicity validation",
        description="Controlled PostgreSQL/UoW atomicity test.",
        user_relevance=0.8,
        expected_benefit=0.7,
        interruption_cost=0.2,
        risk_score=0.1,
        reversibility=0.9,
        urgency=0.4,
        confidence=0.95,
        required_capabilities=("validation",),
        required_autonomy_level=AutonomyLevel.L1,
        sensitivity=EventSensitivity.INTERNAL,
        trust_level=EventTrustLevel.SYSTEM,
        created_at=BASE_TIME,
        expires_at=BASE_TIME + timedelta(minutes=10),
    )


async def cleanup(
    database_engine: AsyncEngine,
    opportunity_id: str,
) -> None:
    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory.begin() as session:
        await session.execute(
            delete(OpportunityRecoveryContextModel).where(
                OpportunityRecoveryContextModel.opportunity_id
                == opportunity_id,
            ),
        )
        await session.execute(
            delete(PersistentOpportunityModel).where(
                PersistentOpportunityModel.opportunity_id
                == opportunity_id,
            ),
        )


@pytest.mark.asyncio
async def test_r097_coordinator_commits_opportunity_and_context_atomically(
    database_engine: AsyncEngine,
) -> None:
    """Opportunity and R097 context must commit in one UoW transaction."""
    opportunity_id = "r097:atomic:commit:001"
    opportunity = make_opportunity(opportunity_id)

    try:
        session_factory = async_sessionmaker(
            database_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with SQLAlchemyPersistenceUnitOfWork(
            session_factory,
        ) as uow:
            assert (
                uow.opportunities._session
                is uow.opportunity_recovery_context._session
            )

            coordinator = OpportunityPersistenceCoordinator(
                uow.opportunities,
                uow.opportunity_recovery_context,
            )

            persisted = await coordinator.persist_queued(
                opportunity,
                source_provenance_ref="r097://integration/commit",
                context_revision=1,
            )

            assert persisted.opportunity_id == opportunity.opportunity_id

        async with session_factory() as session:
            opportunity_row = await session.scalar(
                select(PersistentOpportunityModel).where(
                    PersistentOpportunityModel.opportunity_id
                    == opportunity_id,
                ),
            )

            context_row = await session.scalar(
                select(OpportunityRecoveryContextModel).where(
                    OpportunityRecoveryContextModel.opportunity_id
                    == opportunity_id,
                ),
            )

            assert opportunity_row is not None
            assert context_row is not None
            assert opportunity_row.opportunity_id == context_row.opportunity_id

    finally:
        await cleanup(database_engine, opportunity_id)


@pytest.mark.asyncio
async def test_r097_coordinator_rolls_back_both_records_on_context_failure(
    database_engine: AsyncEngine,
) -> None:
    """Recovery-context failure must roll back the Opportunity record too."""
    opportunity_id = "r097:atomic:rollback:001"
    opportunity = make_opportunity(opportunity_id)

    class FailingRecoveryStore:
        async def create(self, context):
            raise RuntimeError("forced R097 context rollback")

    try:
        session_factory = async_sessionmaker(
            database_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        with pytest.raises(
            RuntimeError,
            match="forced R097 context rollback",
        ):
            async with SQLAlchemyPersistenceUnitOfWork(
                session_factory,
            ) as uow:
                coordinator = OpportunityPersistenceCoordinator(
                    uow.opportunities,
                    FailingRecoveryStore(),
                )

                await coordinator.persist_queued(
                    opportunity,
                    source_provenance_ref="r097://integration/rollback",
                    context_revision=1,
                )

        async with session_factory() as session:
            opportunity_row = await session.scalar(
                select(PersistentOpportunityModel).where(
                    PersistentOpportunityModel.opportunity_id
                    == opportunity_id,
                ),
            )

            context_row = await session.scalar(
                select(OpportunityRecoveryContextModel).where(
                    OpportunityRecoveryContextModel.opportunity_id
                    == opportunity_id,
                ),
            )

            assert opportunity_row is None
            assert context_row is None

    finally:
        await cleanup(database_engine, opportunity_id)
