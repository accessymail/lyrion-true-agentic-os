"""Behavioral tests for the SQLAlchemy lease store."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from sqlalchemy.engine import CursorResult
from sqlalchemy.sql import ClauseElement

from lyrion.persistence.contracts import RuntimeLease
from lyrion.persistence.sqlalchemy.errors import PersistenceConflictError
from lyrion.persistence.sqlalchemy.lease_store import SQLAlchemyLeaseStore

BASE_TIME = datetime(
    2026,
    8,
    31,
    12,
    0,
    tzinfo=UTC,
)


class FakeScalarResult:
    """Minimal scalar result for lease adapter tests."""

    def __init__(
        self,
        value: object = None,
        values: list[object] | None = None,
    ) -> None:
        """Store configured result values."""
        self._value = value
        self._values = values or []

    def scalar_one_or_none(self) -> object:
        """Return one configured scalar."""
        return self._value

    def scalars(self) -> FakeScalarResult:
        """Return this result for scalar iteration."""
        return self

    def all(self) -> list[object]:
        """Return configured scalar rows."""
        return self._values


class FakeCursorResult:
    """Minimal DML result exposing rowcount and RETURNING data."""

    def __init__(
        self,
        rowcount: int,
        row: object = None,
    ) -> None:
        """Store the affected-row count and optional returned row."""
        self.rowcount = rowcount
        self._row = row

    def first(self) -> object:
        """Return the configured RETURNING row."""
        return self._row


class FakeSession:
    """Minimal asynchronous SQLAlchemy session double."""

    def __init__(
        self,
        *,
        query_value: object = None,
        query_values: list[object] | None = None,
        write_rowcount: int = 1,
        write_value: object = None,
    ) -> None:
        """Initialize configured database behavior."""
        self.query_value = query_value
        self.query_values = query_values or []
        self.write_rowcount = write_rowcount
        self.write_value = write_value
        self.executed: list[ClauseElement] = []
        self._query_index = 0

    async def __aenter__(self) -> FakeSession:
        """Enter the async session context."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        """Exit the async session context."""

    async def execute(
        self,
        statement: ClauseElement,
    ) -> object:
        """Record and return a configured result."""
        self.executed.append(statement)

        statement_text = str(statement)

        if (
            statement_text.lstrip().upper().startswith("UPDATE")
            or statement_text.lstrip().upper().startswith("DELETE")
            or statement_text.lstrip().upper().startswith("INSERT")
        ):
            return cast(
                CursorResult[Any],
                FakeCursorResult(
                    self.write_rowcount,
                    self.write_value,
                ),
            )

        if self._query_index == 0:
            self._query_index += 1
            return FakeScalarResult(
                value=self.query_value,
                values=self.query_values,
            )

        return FakeScalarResult(
            value=self.query_value,
            values=self.query_values,
        )


class FakeSessionFactory:
    """Async session factory for adapter tests."""

    def __init__(
        self,
        session: FakeSession,
    ) -> None:
        """Store the configured session."""
        self.session = session

    def __call__(self) -> FakeSession:
        """Return the configured session."""
        return self.session

    @asynccontextmanager
    async def begin(
        self,
    ) -> AsyncIterator[FakeSession]:
        """Provide an async transaction context."""
        yield self.session


def make_row(
    *,
    lease_id: str,
    resource_id: str,
    worker_id: str,
    acquired_at: datetime,
    expires_at: datetime,
    revision: int,
) -> object:
    """Create a fake SQLAlchemy RETURNING row."""
    return type(
        "LeaseRow",
        (),
        {
            "lease_id": lease_id,
            "resource_id": resource_id,
            "worker_id": worker_id,
            "acquired_at": acquired_at,
            "expires_at": expires_at,
            "revision": revision,
        },
    )()


def make_lease(
    *,
    lease_id: str = "lease:001",
    resource_id: str = "resource:001",
    worker_id: str = "worker:001",
    acquired_at: datetime = BASE_TIME,
    expires_at: datetime = BASE_TIME + timedelta(minutes=5),
    revision: int = 1,
) -> RuntimeLease:
    """Create a valid lease."""
    return RuntimeLease(
        lease_id=lease_id,
        resource_id=resource_id,
        worker_id=worker_id,
        acquired_at=acquired_at,
        expires_at=expires_at,
        revision=revision,
    )


@pytest.mark.asyncio
async def test_get_missing_returns_none() -> None:
    """Missing leases should return None."""
    session = FakeSession()
    store = SQLAlchemyLeaseStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.get("resource:001")

    assert result is None


@pytest.mark.asyncio
async def test_get_existing_returns_domain_lease() -> None:
    """Persisted lease rows should become RuntimeLease contracts."""
    model = type(
        "LeaseRow",
        (),
        {
            "lease_id": "lease:001",
            "resource_id": "resource:001",
            "worker_id": "worker:001",
            "acquired_at": BASE_TIME,
            "expires_at": BASE_TIME + timedelta(minutes=5),
            "revision": 4,
        },
    )()

    session = FakeSession(
        query_value=model,
    )
    store = SQLAlchemyLeaseStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.get("resource:001")

    assert result is not None
    assert result.lease_id == "lease:001"
    assert result.worker_id == "worker:001"
    assert result.revision == 4


@pytest.mark.asyncio
async def test_acquire_unowned_resource_succeeds() -> None:
    """An unowned resource should accept a new lease."""
    session = FakeSession(
        write_value=make_row(
            lease_id="lease:001",
            resource_id="resource:001",
            worker_id="worker:001",
            acquired_at=BASE_TIME,
            expires_at=BASE_TIME + timedelta(minutes=5),
            revision=1,
        ),
    )
    store = SQLAlchemyLeaseStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.acquire(
        resource_id="resource:001",
        worker_id="worker:001",
        lease_id="lease:001",
        acquired_at=BASE_TIME,
        expires_at=BASE_TIME + timedelta(minutes=5),
    )

    assert result is not None
    assert result.lease_id == "lease:001"
    assert result.resource_id == "resource:001"
    assert result.worker_id == "worker:001"
    assert result.revision == 1


@pytest.mark.asyncio
async def test_acquire_active_resource_returns_none() -> None:
    """An active owner must prevent another worker from acquiring."""
    existing = make_lease()

    model = type(
        "LeaseRow",
        (),
        {
            "lease_id": existing.lease_id,
            "resource_id": existing.resource_id,
            "worker_id": existing.worker_id,
            "acquired_at": existing.acquired_at,
            "expires_at": existing.expires_at,
            "revision": existing.revision,
        },
    )()

    session = FakeSession(
        query_value=model,
    )
    store = SQLAlchemyLeaseStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.acquire(
        resource_id="resource:001",
        worker_id="worker:002",
        lease_id="lease:002",
        acquired_at=BASE_TIME + timedelta(seconds=1),
        expires_at=BASE_TIME + timedelta(minutes=5),
    )

    assert result is None


@pytest.mark.asyncio
async def test_acquire_expired_resource_reclaims_ownership() -> None:
    """An expired lease may be replaced by a new owner."""
    expired = make_lease(
        expires_at=BASE_TIME + timedelta(seconds=30),
        revision=3,
    )

    model = type(
        "LeaseRow",
        (),
        {
            "lease_id": expired.lease_id,
            "resource_id": expired.resource_id,
            "worker_id": expired.worker_id,
            "acquired_at": expired.acquired_at,
            "expires_at": expired.expires_at,
            "revision": expired.revision,
        },
    )()

    session = FakeSession(
        query_value=model,
        write_rowcount=1,
        write_value=make_row(
            lease_id="lease:002",
            resource_id="resource:001",
            worker_id="worker:002",
            acquired_at=BASE_TIME + timedelta(seconds=30),
            expires_at=BASE_TIME + timedelta(minutes=5),
            revision=4,
        ),
    )
    store = SQLAlchemyLeaseStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.acquire(
        resource_id="resource:001",
        worker_id="worker:002",
        lease_id="lease:002",
        acquired_at=BASE_TIME + timedelta(seconds=30),
        expires_at=BASE_TIME + timedelta(minutes=5),
    )

    assert result is not None
    assert result.worker_id == "worker:002"
    assert result.lease_id == "lease:002"
    assert result.revision == 4


@pytest.mark.asyncio
async def test_acquire_failed_reclaim_returns_none() -> None:
    """A lost concurrent reclaim race must not be reported as success."""
    expired = make_lease(
        expires_at=BASE_TIME + timedelta(seconds=30),
        revision=3,
    )

    model = type(
        "LeaseRow",
        (),
        {
            "lease_id": expired.lease_id,
            "resource_id": expired.resource_id,
            "worker_id": expired.worker_id,
            "acquired_at": expired.acquired_at,
            "expires_at": expired.expires_at,
            "revision": expired.revision,
        },
    )()

    session = FakeSession(
        query_value=model,
        write_rowcount=0,
    )
    store = SQLAlchemyLeaseStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.acquire(
        resource_id="resource:001",
        worker_id="worker:002",
        lease_id="lease:002",
        acquired_at=BASE_TIME + timedelta(seconds=30),
        expires_at=BASE_TIME + timedelta(minutes=5),
    )

    assert result is None


@pytest.mark.asyncio
async def test_renew_valid_owner_advances_revision() -> None:
    """A valid owner may renew and advance the lease revision."""
    current = make_lease(
        revision=2,
        expires_at=BASE_TIME + timedelta(minutes=5),
    )

    updated_model = type(
        "LeaseRow",
        (),
        {
            "lease_id": current.lease_id,
            "resource_id": current.resource_id,
            "worker_id": current.worker_id,
            "acquired_at": current.acquired_at,
            "expires_at": BASE_TIME + timedelta(minutes=10),
            "revision": 3,
        },
    )()

    session = FakeSession(
        query_value=updated_model,
        write_rowcount=1,
        write_value=updated_model,
    )
    store = SQLAlchemyLeaseStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.renew(
        lease_id="lease:001",
        worker_id="worker:001",
        expected_revision=2,
        expires_at=BASE_TIME + timedelta(minutes=10),
    )

    assert result.revision == 3
    assert result.expires_at == BASE_TIME + timedelta(minutes=10)


@pytest.mark.asyncio
async def test_renew_stale_revision_raises_conflict() -> None:
    """Stale owners must not overwrite newer lease state."""
    session = FakeSession(
        write_rowcount=0,
    )
    store = SQLAlchemyLeaseStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        PersistenceConflictError,
        match="lease renewal conflict",
    ):
        await store.renew(
            lease_id="lease:001",
            worker_id="worker:001",
            expected_revision=2,
            expires_at=BASE_TIME + timedelta(minutes=10),
        )

@pytest.mark.asyncio
async def test_renew_requires_later_expiry() -> None:
    """Renewal must extend the existing lease."""
    session = FakeSession(
        write_rowcount=1,
        write_value=make_row(
            lease_id="lease:001",
            resource_id="resource:001",
            worker_id="worker:001",
            acquired_at=BASE_TIME,
            expires_at=BASE_TIME + timedelta(minutes=10),
            revision=3,
        ),
    )
    store = SQLAlchemyLeaseStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.renew(
        lease_id="lease:001",
        worker_id="worker:001",
        expected_revision=2,
        expires_at=BASE_TIME + timedelta(minutes=10),
    )

    assert result.expires_at == BASE_TIME + timedelta(minutes=10)


@pytest.mark.asyncio
async def test_renew_rejects_shortening_expiry() -> None:
    """Renewal must never shorten an existing lease."""
    session = FakeSession(
        write_rowcount=0,
    )
    store = SQLAlchemyLeaseStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        PersistenceConflictError,
        match="lease renewal conflict",
    ):
        await store.renew(
            lease_id="lease:001",
            worker_id="worker:001",
            expected_revision=2,
            expires_at=BASE_TIME + timedelta(minutes=4),
        )


@pytest.mark.asyncio
async def test_release_only_targets_exact_owner() -> None:
    """Release must include both lease and worker identity."""
    session = FakeSession(
        write_rowcount=1,
    )
    store = SQLAlchemyLeaseStore(
        cast(Any, FakeSessionFactory(session)),
    )

    await store.release(
        lease_id="lease:001",
        worker_id="worker:001",
    )

    assert len(session.executed) == 1

    statement_text = str(session.executed[0])

    assert "lease_id" in statement_text
    assert "worker_id" in statement_text


@pytest.mark.asyncio
async def test_find_expired_is_bounded_and_ordered() -> None:
    """Expired lease recovery must be bounded and deterministic."""
    first = make_lease(
        lease_id="lease:001",
        acquired_at=BASE_TIME - timedelta(minutes=10),
        expires_at=BASE_TIME - timedelta(minutes=2),
    )
    second = make_lease(
        lease_id="lease:002",
        acquired_at=BASE_TIME - timedelta(minutes=10),
        expires_at=BASE_TIME - timedelta(minutes=1),
    )

    def row(lease: RuntimeLease) -> object:
        return type(
            "LeaseRow",
            (),
            {
                "lease_id": lease.lease_id,
                "resource_id": lease.resource_id,
                "worker_id": lease.worker_id,
                "acquired_at": lease.acquired_at,
                "expires_at": lease.expires_at,
                "revision": lease.revision,
            },
        )()

    session = FakeSession(
        query_values=[
            row(first),
            row(second),
        ],
    )
    store = SQLAlchemyLeaseStore(
        cast(Any, FakeSessionFactory(session)),
    )

    result = await store.find_expired(
        now=BASE_TIME,
        limit=2,
    )

    assert len(result) == 2
    assert result[0].lease_id == "lease:001"
    assert result[1].lease_id == "lease:002"


@pytest.mark.asyncio
async def test_blank_resource_id_is_rejected() -> None:
    """Resource identifiers must be non-empty."""
    session = FakeSession()
    store = SQLAlchemyLeaseStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        ValueError,
        match="resource_id must not be empty",
    ):
        await store.acquire(
            resource_id=" ",
            worker_id="worker:001",
            lease_id="lease:001",
            acquired_at=BASE_TIME,
            expires_at=BASE_TIME + timedelta(minutes=5),
        )


@pytest.mark.asyncio
async def test_blank_worker_id_is_rejected() -> None:
    """Worker identifiers must be non-empty."""
    session = FakeSession()
    store = SQLAlchemyLeaseStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        ValueError,
        match="worker_id must not be empty",
    ):
        await store.acquire(
            resource_id="resource:001",
            worker_id=" ",
            lease_id="lease:001",
            acquired_at=BASE_TIME,
            expires_at=BASE_TIME + timedelta(minutes=5),
        )


@pytest.mark.asyncio
async def test_invalid_limit_is_rejected() -> None:
    """Expired-lease query limits must be positive."""
    session = FakeSession()
    store = SQLAlchemyLeaseStore(
        cast(Any, FakeSessionFactory(session)),
    )

    with pytest.raises(
        ValueError,
        match="limit must be positive",
    ):
        await store.find_expired(
            now=BASE_TIME,
            limit=0,
        )
