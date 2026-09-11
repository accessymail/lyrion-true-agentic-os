"""Tests for the SQLAlchemy persistence foundation."""

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from lyrion.persistence.sqlalchemy.base import (
    Base,
    create_engine,
    create_session_factory,
)


def test_base_is_declarative_base() -> None:
    """Persistence models must share the project SQLAlchemy base."""
    assert issubclass(Base, object)
    assert hasattr(Base, "metadata")


def test_engine_requires_database_url() -> None:
    """Empty database configuration must fail closed."""
    with pytest.raises(
        ValueError,
        match="database_url must not be empty",
    ):
        create_engine("   ")


def test_engine_requires_postgresql_asyncpg() -> None:
    """The initial production persistence target is PostgreSQL asyncpg."""
    with pytest.raises(
        ValueError,
        match="postgresql\\+asyncpg",
    ):
        create_engine(
            "sqlite+aiosqlite:///lyrion.db",
        )


def test_engine_factory_returns_async_engine() -> None:
    """The foundation must construct an async SQLAlchemy engine."""
    engine = create_engine(
        "postgresql+asyncpg://localhost/lyrion",
    )

    try:
        assert isinstance(engine, AsyncEngine)
    finally:
        # Engine creation does not connect to PostgreSQL.
        engine.sync_engine.dispose()


def test_session_factory_is_async() -> None:
    """The persistence session factory must create AsyncSession objects."""
    engine = create_engine(
        "postgresql+asyncpg://localhost/lyrion",
    )

    try:
        factory = create_session_factory(engine)

        session = factory()

        try:
            assert isinstance(session, AsyncSession)
        finally:
            import asyncio

            asyncio.run(session.close())
    finally:
        engine.sync_engine.dispose()
