"""Tests for the SQLAlchemy persistence unit of work."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from lyrion.persistence.sqlalchemy.base import create_engine, create_session_factory


@pytest.mark.asyncio
async def test_session_factory_produces_async_sessions() -> None:
    """The UoW will rely on the project's async session factory."""
    engine = create_engine(
        "postgresql+asyncpg://localhost/lyrion",
    )

    try:
        factory = create_session_factory(engine)
        session = factory()

        try:
            assert isinstance(session, AsyncSession)
        finally:
            await session.close()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_runtime_store_can_bind_to_existing_session() -> None:
    """RuntimeStore must support composition inside a shared transaction."""
    from lyrion.persistence.sqlalchemy.runtime_store import (
        SQLAlchemyRuntimeStore,
    )

    engine = create_engine(
        "postgresql+asyncpg://localhost/lyrion",
    )

    try:
        factory = create_session_factory(engine)

        async with factory() as session:
            store = SQLAlchemyRuntimeStore._from_session(session)

            assert store._session is session
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_lease_store_can_bind_to_existing_session() -> None:
    """LeaseStore must support composition inside a shared transaction."""
    from lyrion.persistence.sqlalchemy.lease_store import (
        SQLAlchemyLeaseStore,
    )

    engine = create_engine(
        "postgresql+asyncpg://localhost/lyrion",
    )

    try:
        factory = create_session_factory(engine)

        async with factory() as session:
            store = SQLAlchemyLeaseStore._from_session(session)

            assert store._session is session
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_execution_store_can_bind_to_existing_session() -> None:
    """ExecutionStore must support composition inside a shared transaction."""
    from lyrion.persistence.sqlalchemy.execution_store import (
        SQLAlchemyExecutionStore,
    )

    engine = create_engine(
        "postgresql+asyncpg://localhost/lyrion",
    )

    try:
        factory = create_session_factory(engine)

        async with factory() as session:
            store = SQLAlchemyExecutionStore._from_session(session)

            assert store._session is session
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_idempotency_store_can_bind_to_existing_session() -> None:
    """IdempotencyStore must support shared-session composition."""
    from lyrion.persistence.sqlalchemy.idempotency_store import (
        SQLAlchemyIdempotencyStore,
    )

    engine = create_engine(
        "postgresql+asyncpg://localhost/lyrion",
    )

    try:
        factory = create_session_factory(engine)

        async with factory() as session:
            store = SQLAlchemyIdempotencyStore._from_session(session)

            assert store._session is session
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_recovery_store_can_bind_to_existing_session() -> None:
    """RecoveryStore must support shared-session composition."""
    from lyrion.persistence.sqlalchemy.recovery_store import (
        SQLAlchemyRecoveryStore,
    )

    engine = create_engine(
        "postgresql+asyncpg://localhost/lyrion",
    )

    try:
        factory = create_session_factory(engine)

        async with factory() as session:
            store = SQLAlchemyRecoveryStore._from_session(session)

            assert store._session is session
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_scheduler_store_can_bind_to_existing_session() -> None:
    """SchedulerStore must support shared-session composition."""
    from lyrion.persistence.sqlalchemy.scheduler_store import (
        SQLAlchemySchedulerStore,
    )

    engine = create_engine(
        "postgresql+asyncpg://localhost/lyrion",
    )

    try:
        factory = create_session_factory(engine)

        async with factory() as session:
            store = SQLAlchemySchedulerStore._from_session(session)

            assert store._session is session
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_uow_exposes_scheduler_store_on_shared_session() -> None:
    """The UoW scheduler store must use its transaction session."""
    from lyrion.persistence.sqlalchemy.uow import (
        SQLAlchemyPersistenceUnitOfWork,
    )

    engine = create_engine(
        "postgresql+asyncpg://localhost/lyrion",
    )

    try:
        factory = create_session_factory(engine)
        uow = SQLAlchemyPersistenceUnitOfWork(factory)

        async with uow:
            assert uow.scheduler._session is uow._session
            assert uow.voice_identity._session is uow._session
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_uow_exposes_all_seven_stores() -> None:
    """A UoW must expose every durable persistence boundary."""
    from lyrion.persistence.sqlalchemy.uow import (
        SQLAlchemyPersistenceUnitOfWork,
    )

    engine = create_engine(
        "postgresql+asyncpg://localhost/lyrion",
    )

    try:
        factory = create_session_factory(engine)
        uow = SQLAlchemyPersistenceUnitOfWork(factory)

        async with uow:
            assert uow.runtime._session is uow._session
            assert uow.opportunities._session is uow._session
            assert uow.leases._session is uow._session
            assert uow.executions._session is uow._session
            assert uow.idempotency._session is uow._session
            assert uow.recovery._session is uow._session
            assert uow.scheduler._session is uow._session
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_uow_exposes_all_six_stores() -> None:
    """A UoW must expose every durable persistence boundary."""
    from lyrion.persistence.sqlalchemy.uow import (
        SQLAlchemyPersistenceUnitOfWork,
    )

    engine = create_engine(
        "postgresql+asyncpg://localhost/lyrion",
    )

    try:
        factory = create_session_factory(engine)
        uow = SQLAlchemyPersistenceUnitOfWork(factory)

        async with uow:
            assert uow.runtime._session is uow._session
            assert uow.opportunities._session is uow._session
            assert uow.leases._session is uow._session
            assert uow.executions._session is uow._session
            assert uow.idempotency._session is uow._session
            assert uow.recovery._session is uow._session
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_uow_cannot_be_entered_twice() -> None:
    """A single UoW instance must not own two concurrent transactions."""
    from lyrion.persistence.sqlalchemy.uow import (
        SQLAlchemyPersistenceUnitOfWork,
    )

    engine = create_engine(
        "postgresql+asyncpg://localhost/lyrion",
    )

    try:
        factory = create_session_factory(engine)
        uow = SQLAlchemyPersistenceUnitOfWork(factory)

        async with uow:
            with pytest.raises(
                RuntimeError,
                match="already active",
            ):
                await uow.__aenter__()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_uow_requires_active_transaction_for_store_access() -> None:
    """Store access outside the UoW context must fail clearly."""
    from lyrion.persistence.sqlalchemy.uow import (
        SQLAlchemyPersistenceUnitOfWork,
    )

    engine = create_engine(
        "postgresql+asyncpg://localhost/lyrion",
    )

    try:
        factory = create_session_factory(engine)
        uow = SQLAlchemyPersistenceUnitOfWork(factory)

        with pytest.raises(
            RuntimeError,
            match="not active",
        ):
            _ = uow.executions
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_opportunity_store_can_bind_to_existing_session() -> None:
    """OpportunityStore must support shared-session composition."""
    from lyrion.persistence.sqlalchemy.opportunity_store import (
        SQLAlchemyOpportunityStore,
    )

    engine = create_engine(
        "postgresql+asyncpg://localhost/lyrion",
    )

    try:
        factory = create_session_factory(engine)

        async with factory() as session:
            store = SQLAlchemyOpportunityStore._from_session(session)

            assert store._session is session
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_uow_exposes_opportunity_store_on_shared_session() -> None:
    """The UoW opportunity store must use its single transaction session."""
    from lyrion.persistence.sqlalchemy.uow import (
        SQLAlchemyPersistenceUnitOfWork,
    )

    engine = create_engine(
        "postgresql+asyncpg://localhost/lyrion",
    )

    try:
        factory = create_session_factory(engine)
        uow = SQLAlchemyPersistenceUnitOfWork(factory)

        async with uow:
            assert uow.opportunities._session is uow._session
    finally:
        await engine.dispose()

@pytest.mark.asyncio
async def test_voice_identity_store_can_bind_to_existing_session() -> None:
    """Voice Identity store must support shared-session composition."""
    from lyrion.persistence.sqlalchemy.voice_identity_profile_store import (
        SQLAlchemyVoiceIdentityProfileStore,
    )

    engine = create_engine("postgresql+asyncpg://localhost/lyrion")
    try:
        factory = create_session_factory(engine)
        async with factory() as session:
            store = SQLAlchemyVoiceIdentityProfileStore._from_session(session)
            assert store._session is session
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_uow_exposes_voice_identity_store_on_shared_session() -> None:
    """The UoW Voice Identity store must use its transaction session."""
    from lyrion.persistence.sqlalchemy.uow import SQLAlchemyPersistenceUnitOfWork

    engine = create_engine("postgresql+asyncpg://localhost/lyrion")
    try:
        factory = create_session_factory(engine)
        uow = SQLAlchemyPersistenceUnitOfWork(factory)

        async with uow:
            assert uow.voice_identity._session is uow._session
    finally:
        await engine.dispose()
