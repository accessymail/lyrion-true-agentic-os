"""Adversarial tests for durable idempotency contracts."""

from datetime import UTC, datetime

import pytest

from lyrion.persistence.contracts import PersistentIdempotencyRecord

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
    idempotency_key: str = "idem:001",
    request_id: str = "request:001",
    execution_id: str = "execution:001",
) -> PersistentIdempotencyRecord:
    """Create a valid persistent idempotency record."""
    return PersistentIdempotencyRecord(
        idempotency_key=idempotency_key,
        request_id=request_id,
        execution_id=execution_id,
        reserved_at=BASE_TIME,
    )


def test_record_preserves_full_identity_binding() -> None:
    """A durable record must bind key, request, and execution."""
    record = make_record()

    assert record.idempotency_key == "idem:001"
    assert record.request_id == "request:001"
    assert record.execution_id == "execution:001"


def test_record_requires_non_empty_key() -> None:
    """Blank idempotency keys must be rejected."""
    with pytest.raises(ValueError):
        make_record(
            idempotency_key="",
        )


def test_record_requires_non_empty_request_id() -> None:
    """Blank request identifiers must be rejected."""
    with pytest.raises(ValueError):
        make_record(
            request_id="",
        )


def test_record_requires_non_empty_execution_id() -> None:
    """Blank execution identifiers must be rejected."""
    with pytest.raises(ValueError):
        make_record(
            execution_id="",
        )


def test_record_requires_timezone_aware_timestamp() -> None:
    """Reservation timestamps must be timezone-aware."""
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        PersistentIdempotencyRecord(
            idempotency_key="idem:001",
            request_id="request:001",
            execution_id="execution:001",
            reserved_at=datetime(
                2026,
                8,
                31,
                12,
                0,
            ),
        )


def test_record_is_immutable() -> None:
    """Durable idempotency records cannot be mutated in place."""
    record = make_record()

    with pytest.raises(ValueError):
        record.execution_id = "execution:changed"
