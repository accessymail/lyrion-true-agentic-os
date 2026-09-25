"""SQLAlchemy persistence for immutable opportunity recovery context."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lyrion.core.types import AutonomyLevel, CorrelationId, EventId, OpportunityId
from lyrion.events.models import EventSensitivity, EventTrustLevel
from lyrion.persistence.contracts import OpportunityRecoveryContext
from lyrion.persistence.sqlalchemy.models import OpportunityRecoveryContextModel


class SQLAlchemyOpportunityRecoveryContextStore:
    """Persist immutable recovery context using an ownership-aware session."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        *,
        session: AsyncSession | None = None,
    ) -> None:
        """Initialize the recovery-context store."""
        if (session_factory is None) == (session is None):
            raise ValueError("exactly one session source is required")

        self._session_factory = session_factory
        self._session = session

    @classmethod
    def _from_session(
        cls,
        session: AsyncSession,
    ) -> SQLAlchemyOpportunityRecoveryContextStore:
        """Create a store bound to an existing transaction session."""
        return cls(session=session)

    @asynccontextmanager
    async def _read_session(self) -> AsyncIterator[AsyncSession]:
        """Provide a read session without owning the transaction."""
        if self._session is not None:
            yield self._session
            return

        factory = self._session_factory
        if factory is None:
            raise RuntimeError("recovery-context store has no session factory")

        async with factory() as session:
            yield session

    @asynccontextmanager
    async def _write_session(self) -> AsyncIterator[AsyncSession]:
        """Provide a write session with ownership-aware transaction scope."""
        if self._session is not None:
            yield self._session
            return

        factory = self._session_factory
        if factory is None:
            raise RuntimeError("recovery-context store has no session factory")

        async with factory.begin() as session:
            yield session

    async def create(
        self,
        context: OpportunityRecoveryContext,
    ) -> OpportunityRecoveryContext:
        """Persist one immutable recovery context."""
        async with self._write_session() as session:
            existing = await session.execute(
                select(OpportunityRecoveryContextModel.opportunity_id).where(
                    OpportunityRecoveryContextModel.opportunity_id
                    == str(context.opportunity_id)
                )
            )

            if existing.scalar_one_or_none() is not None:
                raise ValueError(
                    "recovery context already exists for opportunity"
                )

            values = {
                "opportunity_id": str(context.opportunity_id),
                "correlation_id": (
                    str(context.correlation_id)
                    if context.correlation_id is not None
                    else None
                ),
                "trigger_event_ids": [
                    str(event_id) for event_id in context.trigger_event_ids
                ],
                "source_provenance_ref": context.source_provenance_ref,
                "relevant_state_ids": list(context.relevant_state_ids),
                "goal_context": list(context.goal_context),
                "title": context.title,
                "description": context.description,
                "user_relevance": context.user_relevance,
                "expected_benefit": context.expected_benefit,
                "interruption_cost": context.interruption_cost,
                "risk_score": context.risk_score,
                "reversibility": context.reversibility,
                "urgency": context.urgency,
                "confidence": context.confidence,
                "required_capabilities": list(context.required_capabilities),
                "required_autonomy_level": context.required_autonomy_level.value,
                "sensitivity": context.sensitivity.value,
                "trust_level": context.trust_level.value,
                "original_status": context.original_status,
                "created_at": context.created_at,
                "expires_at": context.expires_at,
                "schema_version": context.schema_version,
                "context_revision": context.context_revision,
                "integrity_digest": context.integrity_digest,
            }

            try:
                await session.execute(
                    insert(OpportunityRecoveryContextModel).values(**values)
                )
            except IntegrityError as exc:
                raise ValueError(
                    "recovery context already exists for opportunity"
                ) from exc

        return context

    async def get(
        self,
        opportunity_id: str,
    ) -> OpportunityRecoveryContext | None:
        """Return one immutable recovery context."""
        normalized_id = opportunity_id.strip()

        if not normalized_id:
            raise ValueError("opportunity_id must not be empty")

        async with self._read_session() as session:
            result = await session.execute(
                select(OpportunityRecoveryContextModel).where(
                    OpportunityRecoveryContextModel.opportunity_id
                    == normalized_id
                )
            )
            model = result.scalar_one_or_none()

        if model is None:
            return None

        return OpportunityRecoveryContext(
            opportunity_id=OpportunityId(model.opportunity_id),
            correlation_id=(
                CorrelationId(model.correlation_id)
                if model.correlation_id is not None
                else None
            ),
            trigger_event_ids=tuple(
                EventId(value) for value in model.trigger_event_ids
            ),
            source_provenance_ref=model.source_provenance_ref,
            relevant_state_ids=tuple(model.relevant_state_ids),
            goal_context=tuple(model.goal_context),
            title=model.title,
            description=model.description,
            user_relevance=model.user_relevance,
            expected_benefit=model.expected_benefit,
            interruption_cost=model.interruption_cost,
            risk_score=model.risk_score,
            reversibility=model.reversibility,
            urgency=model.urgency,
            confidence=model.confidence,
            required_capabilities=tuple(model.required_capabilities),
            required_autonomy_level=AutonomyLevel(
                model.required_autonomy_level
            ),
            sensitivity=EventSensitivity(model.sensitivity),
            trust_level=EventTrustLevel(model.trust_level),
            original_status=model.original_status,
            created_at=model.created_at,
            expires_at=model.expires_at,
            schema_version=model.schema_version,
            context_revision=model.context_revision,
            integrity_digest=model.integrity_digest,
        )

    async def exists(self, opportunity_id: str) -> bool:
        """Return whether immutable recovery context exists."""
        normalized_id = opportunity_id.strip()

        if not normalized_id:
            raise ValueError("opportunity_id must not be empty")

        async with self._read_session() as session:
            result = await session.execute(
                select(OpportunityRecoveryContextModel.opportunity_id).where(
                    OpportunityRecoveryContextModel.opportunity_id
                    == normalized_id
                )
            )
            return result.scalar_one_or_none() is not None
