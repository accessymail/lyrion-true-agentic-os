"""Real PostgreSQL integration tests for idempotency persistence."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from lyrion.persistence.contracts import PersistentIdempotencyRecord
from lyrion.persistence.sqlalchemy.idempotency_store import (
    SQLAlchemyIdempotencyStore,
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


def make_record(
    *,
    idempotency_key: str = "idem:integration:001",
    request_id: str = "request:integration:001",
    execution_id: str = "execution:integration:001",
) -> PersistentIdempotencyRecord:
    """Create a valid idempotency record."""
    return PersistentIdempotencyRecord(
        idempotency_key=idempotency_key,
        request_id=request_id,
        execution_id=execution_id,
        reserved_at=BASE_TIME,
    )


def make_store(
    database_engine: AsyncEngine,
) -> SQLAlchemyIdempotencyStore:
    """Create an idempotency store using an independent session factory."""
    session_factory = async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return SQLAlchemyIdempotencyStore(session_factory)


@pytest.mark.asyncio
async def test_reservation_persists_across_sessions(
    database_engine: AsyncEngine,
) -> None:
    """A successful reservation must survive a new session."""
    record = make_record()

    store = make_store(database_engine)

    assert await store.reserve(record) is True

    loaded = await store.get(record.idempotency_key)

    assert loaded == record
    assert await store.contains(record.idempotency_key) is True


@pytest.mark.asyncio
async def test_duplicate_key_does_not_replace_original_binding(
    database_engine: AsyncEngine,
) -> None:
    """A duplicate key must preserve the original execution binding."""
    first = make_record(
        idempotency_key="idem:integration:binding",
        request_id="request:first",
        execution_id="execution:first",
    )
    second = make_record(
        idempotency_key="idem:integration:binding",
        request_id="request:second",
        execution_id="execution:second",
    )

    store = make_store(database_engine)

    assert await store.reserve(first) is True
    assert await store.reserve(second) is False

    loaded = await store.get(first.idempotency_key)

    assert loaded == first


@pytest.mark.asyncio
async def test_two_workers_compete_for_one_idempotency_key(
    database_engine: AsyncEngine,
) -> None:
    """Exactly one concurrent reservation may claim one key."""
    start = asyncio.Event()

    async def attempt(
        worker_number: int,
    ) -> bool:
        store = make_store(database_engine)

        record = make_record(
            idempotency_key="idem:integration:race",
            request_id=f"request:worker:{worker_number}",
            execution_id=f"execution:worker:{worker_number}",
        )

        await start.wait()

        return await store.reserve(record)

    tasks = [
        asyncio.create_task(attempt(1)),
        asyncio.create_task(attempt(2)),
    ]

    start.set()

    results = await asyncio.gather(*tasks)

    assert sum(results) == 1


@pytest.mark.asyncio
async def test_get_missing_key_returns_none(
    database_engine: AsyncEngine,
) -> None:
    """A missing key must not produce a phantom reservation."""
    store = make_store(database_engine)

    result = await store.get("idem:integration:missing")

    assert result is None


@pytest.mark.asyncio
async def test_contains_missing_key_returns_false(
    database_engine: AsyncEngine,
) -> None:
    """contains() must report absent keys accurately."""
    store = make_store(database_engine)

    result = await store.contains("idem:integration:missing")

    assert result is False
