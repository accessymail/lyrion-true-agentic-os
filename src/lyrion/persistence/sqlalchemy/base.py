"""SQLAlchemy persistence foundation for Lyrion."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for durable Lyrion persistence models."""


def create_engine(
    database_url: str,
) -> AsyncEngine:
    """Create an asynchronous SQLAlchemy engine."""
    normalized_url = database_url.strip()

    if not normalized_url:
        raise ValueError(
            "database_url must not be empty"
        )

    if not normalized_url.startswith(
        "postgresql+asyncpg://",
    ):
        raise ValueError(
            "database_url must use postgresql+asyncpg"
        )

    return create_async_engine(
        normalized_url,
        future=True,
    )


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create the async session factory for persistence operations."""
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
