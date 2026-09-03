"""Adversarial tests for the durable opportunity lifecycle."""

from datetime import UTC, datetime, timedelta

import pytest

from lyrion.core.types import OpportunityId
from lyrion.persistence.contracts import (
    PersistentOpportunity,
    PersistentOpportunityState,
)

BASE_TIME = datetime(
    2026,
    8,
    31,
    12,
    0,
    tzinfo=UTC,
)


def make_opportunity(
    *,
    state: PersistentOpportunityState = (
        PersistentOpportunityState.QUEUED
    ),
    claimed_at: datetime | None = None,
    completed_at: datetime | None = None,
    worker_id: str | None = None,
    lease_id: str | None = None,
    execution_id: str | None = None,
    expires_at: datetime | None = None,
) -> PersistentOpportunity:
    """Create a valid durable opportunity."""
    return PersistentOpportunity(
        opportunity_id=OpportunityId("opportunity:001"),
        state=state,
        created_at=BASE_TIME,
        expires_at=expires_at,
        worker_id=worker_id,
        lease_id=lease_id,
        claimed_at=claimed_at,
        completed_at=completed_at,
        execution_id=execution_id,
    )


def test_queued_opportunity_is_minimal() -> None:
    """A newly persisted opportunity needs only creation evidence."""
    opportunity = make_opportunity()

    assert opportunity.state is PersistentOpportunityState.QUEUED
    assert opportunity.claimed_at is None
    assert opportunity.completed_at is None
    assert opportunity.execution_id is None


def test_claimed_requires_claim_timestamp() -> None:
    """CLAIMED must carry claim evidence."""
    with pytest.raises(
        ValueError,
        match="CLAIMED state requires claimed_at",
    ):
        make_opportunity(
            state=PersistentOpportunityState.CLAIMED,
        )


def test_executing_requires_execution_identity() -> None:
    """EXECUTING must be tied to a concrete execution."""
    with pytest.raises(
        ValueError,
        match="requires claimed_at and execution_id",
    ):
        make_opportunity(
            state=PersistentOpportunityState.EXECUTING,
            claimed_at=BASE_TIME + timedelta(seconds=1),
        )


def test_terminal_state_requires_completion_time() -> None:
    """Terminal opportunity state requires completion evidence."""
    with pytest.raises(
        ValueError,
        match="terminal opportunity state requires completed_at",
    ):
        make_opportunity(
            state=PersistentOpportunityState.COMPLETED,
        )


def test_lifecycle_timestamps_cannot_move_backward() -> None:
    """Claim time must not precede opportunity creation."""
    with pytest.raises(
        ValueError,
        match="timestamps must be ordered",
    ):
        make_opportunity(
            claimed_at=BASE_TIME - timedelta(seconds=1),
        )


def test_expiry_cannot_precede_creation() -> None:
    """Expired-at cannot contradict creation time."""
    with pytest.raises(
        ValueError,
        match="expires_at cannot be earlier",
    ):
        make_opportunity(
            expires_at=BASE_TIME - timedelta(seconds=1),
        )


def test_expiration_uses_supplied_clock() -> None:
    """Expiration evaluation must be deterministic."""
    opportunity = make_opportunity(
        expires_at=BASE_TIME + timedelta(seconds=30),
    )

    assert opportunity.is_expired(
        BASE_TIME + timedelta(seconds=29),
    ) is False

    assert opportunity.is_expired(
        BASE_TIME + timedelta(seconds=30),
    ) is True


def test_naive_clock_is_rejected() -> None:
    """Expiration checks must reject naive timestamps."""
    opportunity = make_opportunity(
        expires_at=BASE_TIME + timedelta(seconds=30),
    )

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        opportunity.is_expired(
            datetime(
                2026,
                8,
                31,
                12,
                0,
            ),
        )


def test_completed_opportunity_preserves_execution_identity() -> None:
    """Completion retains the execution that consumed the opportunity."""
    opportunity = make_opportunity(
        state=PersistentOpportunityState.COMPLETED,
        claimed_at=BASE_TIME + timedelta(seconds=1),
        completed_at=BASE_TIME + timedelta(seconds=2),
        worker_id="worker:001",
        lease_id="lease:001",
        execution_id="execution:001",
    )

    assert opportunity.execution_id == "execution:001"
    assert opportunity.worker_id == "worker:001"
    assert opportunity.lease_id == "lease:001"


def test_unknown_is_valid_for_unresolved_crash_state() -> None:
    """UNKNOWN represents an unresolved execution outcome."""
    opportunity = make_opportunity(
        state=PersistentOpportunityState.UNKNOWN,
        completed_at=BASE_TIME + timedelta(seconds=1),
    )

    assert opportunity.state is PersistentOpportunityState.UNKNOWN


def test_opportunity_model_is_immutable() -> None:
    """Durable opportunity records cannot be mutated in place."""
    opportunity = make_opportunity()

    with pytest.raises(ValueError):
        opportunity.state = PersistentOpportunityState.CLAIMED
