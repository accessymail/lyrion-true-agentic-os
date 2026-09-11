"""Shared PostgreSQL integration-test fixtures."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from lyrion.persistence.sqlalchemy import models as _models
from lyrion.persistence.sqlalchemy.base import Base, create_engine

# Importing the ORM module registers all mapped tables with Base.metadata.
assert _models is not None


@pytest_asyncio.fixture
async def database_engine() -> AsyncIterator[AsyncEngine]:
    """Create and tear down the integration-test database engine."""
    database_url = os.environ.get("LYRION_DATABASE_URL")

    if not database_url:
        pytest.skip(
            "LYRION_DATABASE_URL is required for PostgreSQL integration tests",
        )

    engine = create_engine(database_url)

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

        yield engine

    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)

        await engine.dispose()


@pytest_asyncio.fixture
async def database_session_factory(
    database_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Return an independent async session factory."""
    return async_sessionmaker(
        database_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
