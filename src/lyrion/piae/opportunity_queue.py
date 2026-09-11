"""Bounded, deterministic opportunity queue for PIAE."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock

from lyrion.core.types import OpportunityId
from lyrion.piae.contracts import Opportunity, OpportunityStatus


@dataclass(frozen=True)
class OpportunityQueueConfig:
    """Explicit bounds for the opportunity queue."""

    max_size: int = 128

    def __post_init__(self) -> None:
        """Validate queue capacity."""
        if self.max_size <= 0:
            raise ValueError(
                "max_size must be greater than zero"
            )


class OpportunityQueue:
    """Thread-safe bounded queue with deterministic priority ordering."""

    def __init__(
        self,
        config: OpportunityQueueConfig | None = None,
    ) -> None:
        """Initialize the queue."""
        self._config = config or OpportunityQueueConfig()
        self._lock = Lock()
        self._items: dict[OpportunityId, Opportunity] = {}

    @property
    def config(self) -> OpportunityQueueConfig:
        """Return the queue configuration."""
        return self._config

    def size(
        self,
        *,
        now: datetime | None = None,
    ) -> int:
        """Return the number of currently active queued opportunities."""
        current_time = self._normalize_now(now)

        with self._lock:
            self._expire_locked(current_time)
            return len(self._items)

    def enqueue(
        self,
        opportunity: Opportunity,
        *,
        now: datetime | None = None,
    ) -> bool:
        """Add an opportunity unless it is duplicate, expired, or suppressed."""
        current_time = self._normalize_now(now)

        with self._lock:
            self._expire_locked(current_time)

            if opportunity.status is not OpportunityStatus.OPEN:
                return False

            if opportunity.is_expired(current_time):
                return False

            if opportunity.opportunity_id in self._items:
                return False

            if len(self._items) >= self._config.max_size:
                return False

            self._items[opportunity.opportunity_id] = opportunity
            return True

    def peek(
        self,
        *,
        now: datetime | None = None,
    ) -> Opportunity | None:
        """Return the highest-priority opportunity without removing it."""
        current_time = self._normalize_now(now)

        with self._lock:
            self._expire_locked(current_time)

            if not self._items:
                return None

            return min(
                self._items.values(),
                key=self._sort_key,
            )

    def dequeue(
        self,
        *,
        now: datetime | None = None,
    ) -> Opportunity | None:
        """Remove and return the highest-priority opportunity."""
        current_time = self._normalize_now(now)

        with self._lock:
            self._expire_locked(current_time)

            if not self._items:
                return None

            selected = min(
                self._items.values(),
                key=self._sort_key,
            )

            self._items.pop(
                selected.opportunity_id,
                None,
            )

            return selected

    def remove(
        self,
        opportunity_id: OpportunityId,
        *,
        now: datetime | None = None,
    ) -> bool:
        """Remove an opportunity by ID."""
        current_time = self._normalize_now(now)

        with self._lock:
            self._expire_locked(current_time)
            return (
                self._items.pop(
                    opportunity_id,
                    None,
                )
                is not None
            )

    def contains(
        self,
        opportunity_id: OpportunityId,
        *,
        now: datetime | None = None,
    ) -> bool:
        """Return whether an opportunity is currently queued."""
        current_time = self._normalize_now(now)

        with self._lock:
            self._expire_locked(current_time)
            return opportunity_id in self._items

    def clear(
        self,
        *,
        now: datetime | None = None,
    ) -> int:
        """Remove all queued opportunities and return the count."""
        self._normalize_now(now)

        with self._lock:
            count = len(self._items)
            self._items.clear()
            return count

    def snapshot(
        self,
        *,
        now: datetime | None = None,
    ) -> tuple[Opportunity, ...]:
        """Return a deterministic snapshot without removing entries."""
        current_time = self._normalize_now(now)

        with self._lock:
            self._expire_locked(current_time)

            return tuple(
                sorted(
                    self._items.values(),
                    key=self._sort_key,
                )
            )

    @staticmethod
    def _sort_key(
        opportunity: Opportunity,
    ) -> tuple[float, float, float, float, datetime, str]:
        """Return deterministic priority ordering."""
        return (
            -opportunity.urgency,
            -opportunity.expected_benefit,
            opportunity.interruption_cost,
            opportunity.risk_score,
            opportunity.created_at,
            str(opportunity.opportunity_id),
        )

    @staticmethod
    def _normalize_now(
        now: datetime | None,
    ) -> datetime:
        """Normalize and validate the current time."""
        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        return current_time.astimezone(UTC)

    def _expire_locked(
        self,
        now: datetime,
    ) -> None:
        """Remove opportunities that are already expired."""
        expired_ids = tuple(
            opportunity_id
            for opportunity_id, opportunity in self._items.items()
            if opportunity.is_expired(now)
        )

        for opportunity_id in expired_ids:
            self._items.pop(
                opportunity_id,
                None,
            )
