"""SQLAlchemy implementation of the persistence unit of work."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from lyrion.persistence.sqlalchemy.execution_store import (
    SQLAlchemyExecutionStore,
)
from lyrion.persistence.sqlalchemy.idempotency_store import (
    SQLAlchemyIdempotencyStore,
)
from lyrion.persistence.sqlalchemy.lease_store import SQLAlchemyLeaseStore
from lyrion.persistence.sqlalchemy.opportunity_store import (
    SQLAlchemyOpportunityStore,
)
from lyrion.persistence.sqlalchemy.recovery_store import SQLAlchemyRecoveryStore
from lyrion.persistence.sqlalchemy.opportunity_recovery_context_store import SQLAlchemyOpportunityRecoveryContextStore
from lyrion.persistence.sqlalchemy.runtime_store import SQLAlchemyRuntimeStore
from lyrion.persistence.sqlalchemy.scheduler_store import SQLAlchemySchedulerStore
from lyrion.persistence.sqlalchemy.voice_identity_profile_store import (
    SQLAlchemyVoiceIdentityProfileStore,
)


class SQLAlchemyPersistenceUnitOfWork:
    """Provide all durable stores inside one SQLAlchemy transaction."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Initialize the persistence unit of work."""
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

        self._runtime: SQLAlchemyRuntimeStore | None = None
        self._opportunities: SQLAlchemyOpportunityStore | None = None
        self._leases: SQLAlchemyLeaseStore | None = None
        self._executions: SQLAlchemyExecutionStore | None = None
        self._idempotency: SQLAlchemyIdempotencyStore | None = None
        self._recovery: SQLAlchemyRecoveryStore | None = None
        self._opportunity_recovery_context: SQLAlchemyOpportunityRecoveryContextStore | None = None
        self._scheduler: SQLAlchemySchedulerStore | None = None
        self._voice_identity: SQLAlchemyVoiceIdentityProfileStore | None = None

    async def __aenter__(
        self,
    ) -> SQLAlchemyPersistenceUnitOfWork:
        """Open one shared database transaction."""
        if self._session is not None:
            raise RuntimeError(
                "persistence unit of work is already active"
            )

        self._session = self._session_factory()

        await self._session.begin()

        self._runtime = SQLAlchemyRuntimeStore._from_session(
            self._session,
        )
        self._opportunities = SQLAlchemyOpportunityStore._from_session(
            self._session,
        )
        self._leases = SQLAlchemyLeaseStore._from_session(
            self._session,
        )
        self._executions = SQLAlchemyExecutionStore._from_session(
            self._session,
        )
        self._idempotency = SQLAlchemyIdempotencyStore._from_session(
            self._session,
        )
        self._recovery = SQLAlchemyRecoveryStore._from_session(
            self._session,
        )
        self._opportunity_recovery_context = (
            SQLAlchemyOpportunityRecoveryContextStore._from_session(
                self._session,
            )
        )
        self._scheduler = SQLAlchemySchedulerStore._from_session(
            self._session,
        )
        self._voice_identity = SQLAlchemyVoiceIdentityProfileStore._from_session(
            self._session,
        )

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        """Commit on success and roll back on failure."""
        session = self._session

        if session is None:
            raise RuntimeError(
                "persistence unit of work is not active"
            )

        try:
            if exc_type is None:
                await session.commit()
            else:
                await session.rollback()
        finally:
            await session.close()

            self._session = None
            self._runtime = None
            self._opportunities = None
            self._leases = None
            self._executions = None
            self._idempotency = None
            self._recovery = None
            self._opportunity_recovery_context = None
            self._scheduler = None
            self._voice_identity = None

    @property
    def runtime(self) -> SQLAlchemyRuntimeStore:
        """Return the runtime store within the transaction."""
        if self._runtime is None:
            raise RuntimeError(
                "persistence unit of work is not active"
            )

        return self._runtime

    @property
    def opportunities(self) -> SQLAlchemyOpportunityStore:
        """Return the opportunity store within the transaction."""
        if self._opportunities is None:
            raise RuntimeError(
                "persistence unit of work is not active"
            )

        return self._opportunities

    @property
    def leases(self) -> SQLAlchemyLeaseStore:
        """Return the lease store within the transaction."""
        if self._leases is None:
            raise RuntimeError(
                "persistence unit of work is not active"
            )

        return self._leases

    @property
    def executions(self) -> SQLAlchemyExecutionStore:
        """Return the execution store within the transaction."""
        if self._executions is None:
            raise RuntimeError(
                "persistence unit of work is not active"
            )

        return self._executions

    @property
    def idempotency(self) -> SQLAlchemyIdempotencyStore:
        """Return the idempotency store within the transaction."""
        if self._idempotency is None:
            raise RuntimeError(
                "persistence unit of work is not active"
            )

        return self._idempotency

    @property
    def recovery(self) -> SQLAlchemyRecoveryStore:
        """Return the recovery store within the transaction."""
        if self._recovery is None:
            raise RuntimeError(
                "persistence unit of work is not active"
            )

        return self._recovery

    @property
    def opportunity_recovery_context(
        self,
    ) -> SQLAlchemyOpportunityRecoveryContextStore:
        """Return the opportunity recovery-context store within the transaction."""
        if self._opportunity_recovery_context is None:
            raise RuntimeError(
                "persistence unit of work is not active"
            )

        return self._opportunity_recovery_context

    @property
    def voice_identity(self) -> SQLAlchemyVoiceIdentityProfileStore:
        """Return the Voice Identity profile store within the transaction."""
        if self._voice_identity is None:
            raise RuntimeError(
                "persistence unit of work is not active"
            )
        return self._voice_identity

    @property
    def scheduler(self) -> SQLAlchemySchedulerStore:
        """Return the scheduler store within the transaction."""
        if self._scheduler is None:
            raise RuntimeError(
                "persistence unit of work is not active"
            )

        return self._scheduler
