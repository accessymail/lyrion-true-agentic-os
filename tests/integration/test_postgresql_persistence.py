"""PostgreSQL persistence integration smoke tests."""



from __future__ import annotations

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

pytestmark = pytest.mark.integration


async def test_postgresql_connection(
    database_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """The integration suite must reach PostgreSQL successfully."""
    async with database_session_factory() as session:
        result = await session.execute(
            text("SELECT 1"),
        )

        assert result.scalar_one() == 1


async def test_persistence_schema_exists(
    database_engine: AsyncEngine,
) -> None:
    """All durable persistence tables must exist in PostgreSQL."""
    expected_tables = {
        "runtime_instances",
        "runtime_leases",
        "persistent_opportunities",
        "persistent_executions",
        "persistent_scheduler",
        "idempotency_records",
        "recovery_decisions",
    }

    async with database_engine.connect() as connection:
        tables = await connection.run_sync(
            lambda sync_connection: set(
                inspect(sync_connection).get_table_names(),
            ),
        )

    assert expected_tables <= tables
