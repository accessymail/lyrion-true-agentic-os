"""Real PostgreSQL concurrency tests for durable lease ownership."""



from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from lyrion.persistence.sqlalchemy.lease_store import SQLAlchemyLeaseStore
from lyrion.persistence.sqlalchemy.models import RuntimeLeaseModel

pytestmark = pytest.mark.integration

BASE_TIME = datetime(
    2026,
    8,
    31,
    12,
    0,
    tzinfo=UTC,
)


@pytest.mark.asyncio
async def test_two_workers_compete_for_one_resource(
    database_engine: AsyncEngine,
) -> None:
    """Exactly one concurrent worker may acquire one resource."""
    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    start = asyncio.Event()

    async def attempt(
        worker_id: str,
        lease_id: str,
    ) -> bool:
        await start.wait()

        store = SQLAlchemyLeaseStore(session_factory)

        result = await store.acquire(
            resource_id="resource:concurrent",
            worker_id=worker_id,
            lease_id=lease_id,
            acquired_at=BASE_TIME,
            expires_at=BASE_TIME + timedelta(minutes=5),
        )

        return result is not None

    tasks = [
        asyncio.create_task(
            attempt("worker:A", "lease:A"),
        ),
        asyncio.create_task(
            attempt("worker:B", "lease:B"),
        ),
    ]

    start.set()

    results = await asyncio.gather(*tasks)

    assert sum(results) == 1

    async with session_factory() as session:
        rows = (
            await session.execute(
                select(RuntimeLeaseModel).where(
                    RuntimeLeaseModel.resource_id
                    == "resource:concurrent",
                )
            )
        ).scalars().all()

    assert len(rows) == 1
    assert rows[0].worker_id in {"worker:A", "worker:B"}


@pytest.mark.asyncio
async def test_concurrent_reclaim_allows_only_one_new_owner(
    database_engine: AsyncEngine,
) -> None:
    """Two workers reclaiming one expired lease must serialize."""
    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    seed = SQLAlchemyLeaseStore(session_factory)

    seeded = await seed.acquire(
        resource_id="resource:expired-race",
        worker_id="worker:old",
        lease_id="lease:old",
        acquired_at=BASE_TIME - timedelta(minutes=10),
        expires_at=BASE_TIME - timedelta(minutes=1),
    )

    assert seeded is not None

    start = asyncio.Event()

    async def reclaim(
        worker_id: str,
        lease_id: str,
    ) -> bool:
        await start.wait()

        store = SQLAlchemyLeaseStore(session_factory)

        result = await store.acquire(
            resource_id="resource:expired-race",
            worker_id=worker_id,
            lease_id=lease_id,
            acquired_at=BASE_TIME,
            expires_at=BASE_TIME + timedelta(minutes=5),
        )

        return result is not None

    tasks = [
        asyncio.create_task(
            reclaim("worker:A", "lease:A"),
        ),
        asyncio.create_task(
            reclaim("worker:B", "lease:B"),
        ),
    ]

    start.set()

    results = await asyncio.gather(*tasks)

    assert sum(results) == 1

    async with session_factory() as session:
        row = await session.scalar(
            select(RuntimeLeaseModel).where(
                RuntimeLeaseModel.resource_id
                == "resource:expired-race",
            )
        )

    assert row is not None
    assert row.worker_id in {"worker:A", "worker:B"}
    assert row.lease_id in {"lease:A", "lease:B"}
    assert row.revision == 2
