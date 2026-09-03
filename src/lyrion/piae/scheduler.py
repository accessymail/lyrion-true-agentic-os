"""Externally stepped, bounded scheduling for proactive intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum


class SchedulerState(StrEnum):
    """Lifecycle state of the controlled scheduler."""

    READY = "READY"
    PAUSED = "PAUSED"


@dataclass(frozen=True)
class ControlledSchedulerConfig:
    """Explicit timing bounds for proactive scheduling."""

    interval_seconds: float = 60.0
    maximum_delay_seconds: float | None = None

    def __post_init__(self) -> None:
        """Validate scheduler bounds."""
        if self.interval_seconds <= 0:
            raise ValueError(
                "interval_seconds must be greater than zero"
            )

        if (
            self.maximum_delay_seconds is not None
            and self.maximum_delay_seconds <= 0
        ):
            raise ValueError(
                "maximum_delay_seconds must be greater than zero"
            )


@dataclass(frozen=True)
class SchedulerDecision:
    """Immutable answer to a scheduler evaluation."""

    due: bool
    state: SchedulerState
    next_run_at: datetime | None
    reason: str


class ControlledScheduler:
    """Determine when a bounded proactive cycle may run."""

    def __init__(
        self,
        config: ControlledSchedulerConfig | None = None,
        *,
        start_at: datetime | None = None,
    ) -> None:
        """Initialize the scheduler."""
        self._config = (
            config
            or ControlledSchedulerConfig()
        )
        self._state = SchedulerState.READY

        if start_at is None:
            self._next_run_at = None
        else:
            self._require_aware(
                start_at,
                name="start_at",
            )
            self._next_run_at = (
                start_at
                + timedelta(
                    seconds=self._config.interval_seconds,
                )
            )

    @classmethod
    def from_persisted_state(
        cls,
        state: SchedulerState,
        next_run_at: datetime | None,
        *,
        config: ControlledSchedulerConfig | None = None,
    ) -> ControlledScheduler:
        """Restore scheduler state without coupling to persistence."""
        if next_run_at is not None:
            cls._require_aware(
                next_run_at,
                name="next_run_at",
            )

        scheduler = cls(
            config=config,
        )
        scheduler._state = state
        scheduler._next_run_at = next_run_at
        return scheduler

    @property
    def config(self) -> ControlledSchedulerConfig:
        """Return scheduler configuration."""
        return self._config

    @property
    def state(self) -> SchedulerState:
        """Return scheduler state."""
        return self._state

    @property
    def next_run_at(self) -> datetime | None:
        """Return the next eligible run time."""
        return self._next_run_at

    def evaluate(
        self,
        *,
        now: datetime | None = None,
    ) -> SchedulerDecision:
        """Determine whether a bounded cycle is currently due."""
        current_time = now or datetime.now(UTC)

        self._require_aware(
            current_time,
            name="now",
        )

        if self._state is SchedulerState.PAUSED:
            return SchedulerDecision(
                due=False,
                state=self._state,
                next_run_at=self._next_run_at,
                reason="PAUSED",
            )

        if self._next_run_at is None:
            return SchedulerDecision(
                due=True,
                state=self._state,
                next_run_at=None,
                reason="INITIAL_RUN",
            )

        if current_time < self._next_run_at:
            return SchedulerDecision(
                due=False,
                state=self._state,
                next_run_at=self._next_run_at,
                reason="NOT_DUE",
            )

        return SchedulerDecision(
            due=True,
            state=self._state,
            next_run_at=self._next_run_at,
            reason="DUE",
        )

    def mark_cycle_completed(
        self,
        *,
        now: datetime | None = None,
    ) -> datetime:
        """Schedule the next cycle after a completed cycle."""
        current_time = now or datetime.now(UTC)

        self._require_aware(
            current_time,
            name="now",
        )

        next_run_at = (
            current_time
            + timedelta(
                seconds=self._config.interval_seconds,
            )
        )

        if self._config.maximum_delay_seconds is not None:
            maximum_allowed = (
                current_time
                + timedelta(
                    seconds=self._config.maximum_delay_seconds,
                )
            )

            if next_run_at > maximum_allowed:
                next_run_at = maximum_allowed

        self._next_run_at = next_run_at

        return next_run_at

    def pause(self) -> None:
        """Pause future scheduling decisions."""
        self._state = SchedulerState.PAUSED

    def resume(
        self,
        *,
        now: datetime | None = None,
    ) -> datetime:
        """Resume scheduling and permit an immediate next run."""
        current_time = now or datetime.now(UTC)

        self._require_aware(
            current_time,
            name="now",
        )

        self._state = SchedulerState.READY
        self._next_run_at = current_time

        return current_time

    @staticmethod
    def _require_aware(
        value: datetime,
        *,
        name: str,
    ) -> None:
        """Require a timezone-aware timestamp."""
        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                f"{name} must be timezone-aware"
            )
