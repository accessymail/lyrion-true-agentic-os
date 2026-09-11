"""Adversarial tests for controlled proactive scheduling."""

from datetime import UTC, datetime, timedelta

import pytest

from lyrion.piae.scheduler import (
    ControlledScheduler,
    ControlledSchedulerConfig,
    SchedulerState,
)

BASE_TIME = datetime(
    2026,
    8,
    31,
    12,
    0,
    tzinfo=UTC,
)


def test_default_interval_is_positive() -> None:
    """Default scheduling interval must be bounded."""
    config = ControlledSchedulerConfig()

    assert config.interval_seconds > 0


def test_zero_interval_is_rejected() -> None:
    """Zero scheduling interval is invalid."""
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        ControlledSchedulerConfig(
            interval_seconds=0,
        )


def test_negative_interval_is_rejected() -> None:
    """Negative scheduling interval is invalid."""
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        ControlledSchedulerConfig(
            interval_seconds=-1,
        )


def test_invalid_maximum_delay_is_rejected() -> None:
    """Maximum delay must be positive when configured."""
    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        ControlledSchedulerConfig(
            maximum_delay_seconds=0,
        )


def test_initial_scheduler_is_immediately_due() -> None:
    """A new scheduler permits its first externally driven cycle."""
    scheduler = ControlledScheduler()

    decision = scheduler.evaluate(
        now=BASE_TIME,
    )

    assert decision.due is True
    assert decision.reason == "INITIAL_RUN"
    assert decision.state is SchedulerState.READY


def test_interval_prevents_early_execution() -> None:
    """A cycle cannot run before its interval expires."""
    scheduler = ControlledScheduler(
        ControlledSchedulerConfig(
            interval_seconds=60,
        ),
        start_at=BASE_TIME,
    )

    decision = scheduler.evaluate(
        now=BASE_TIME + timedelta(seconds=59),
    )

    assert decision.due is False
    assert decision.reason == "NOT_DUE"


def test_interval_allows_execution_when_due() -> None:
    """A cycle becomes due at the scheduled timestamp."""
    scheduler = ControlledScheduler(
        ControlledSchedulerConfig(
            interval_seconds=60,
        ),
        start_at=BASE_TIME,
    )

    decision = scheduler.evaluate(
        now=BASE_TIME + timedelta(seconds=60),
    )

    assert decision.due is True
    assert decision.reason == "DUE"


def test_completed_cycle_schedules_next_run() -> None:
    """Completing a cycle establishes the next run time."""
    scheduler = ControlledScheduler(
        ControlledSchedulerConfig(
            interval_seconds=60,
        )
    )

    next_run = scheduler.mark_cycle_completed(
        now=BASE_TIME,
    )

    assert next_run == (
        BASE_TIME + timedelta(seconds=60)
    )
    assert scheduler.next_run_at == next_run


def test_pause_blocks_execution() -> None:
    """Paused scheduling must never report due."""
    scheduler = ControlledScheduler(
        start_at=BASE_TIME,
    )

    scheduler.pause()

    decision = scheduler.evaluate(
        now=BASE_TIME,
    )

    assert decision.due is False
    assert decision.reason == "PAUSED"
    assert decision.state is SchedulerState.PAUSED


def test_resume_reenables_execution() -> None:
    """Resuming establishes an immediate next run."""
    scheduler = ControlledScheduler(
        start_at=BASE_TIME,
    )

    scheduler.pause()

    resumed_at = scheduler.resume(
        now=BASE_TIME + timedelta(minutes=5),
    )

    decision = scheduler.evaluate(
        now=resumed_at,
    )

    assert resumed_at == (
        BASE_TIME + timedelta(minutes=5)
    )
    assert decision.due is True
    assert scheduler.state is SchedulerState.READY


def test_naive_now_is_rejected() -> None:
    """Scheduling decisions require timezone-aware time."""
    scheduler = ControlledScheduler()

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        scheduler.evaluate(
            now=datetime(2026, 8, 31, 12, 0),
        )


def test_naive_start_time_is_rejected() -> None:
    """Scheduler start times must be timezone-aware."""
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        ControlledScheduler(
            start_at=datetime(
                2026,
                8,
                31,
                12,
                0,
            ),
        )


def test_next_run_is_bounded_by_maximum_delay() -> None:
    """Configured maximum delay must cap the next run."""
    scheduler = ControlledScheduler(
        ControlledSchedulerConfig(
            interval_seconds=120,
            maximum_delay_seconds=60,
        )
    )

    next_run = scheduler.mark_cycle_completed(
        now=BASE_TIME,
    )

    assert next_run == (
        BASE_TIME + timedelta(seconds=60)
    )


def test_scheduler_does_not_execute_work() -> None:
    """The scheduler must only decide timing."""
    scheduler = ControlledScheduler(
        start_at=BASE_TIME,
    )

    decision = scheduler.evaluate(
        now=BASE_TIME,
    )

    assert decision.due is False
    assert decision.reason == "NOT_DUE"
    assert not hasattr(
        scheduler,
        "execute",
    )
    assert not hasattr(
        scheduler,
        "consume",
    )


def test_scheduler_state_is_explicit() -> None:
    """Scheduler state must remain explicit and inspectable."""
    scheduler = ControlledScheduler()

    assert scheduler.state is SchedulerState.READY

    scheduler.pause()

    paused_state: SchedulerState = scheduler.state
    assert paused_state == SchedulerState.PAUSED


def test_persisted_ready_state_is_restored() -> None:
    """Persisted READY state and deadline should survive restoration."""
    next_run_at = BASE_TIME + timedelta(minutes=5)

    scheduler = ControlledScheduler.from_persisted_state(
        SchedulerState.READY,
        next_run_at,
    )

    assert scheduler.state is SchedulerState.READY
    assert scheduler.next_run_at == next_run_at


def test_persisted_paused_state_is_restored() -> None:
    """Persisted PAUSED state must remain paused after restoration."""
    scheduler = ControlledScheduler.from_persisted_state(
        SchedulerState.PAUSED,
        None,
    )

    decision = scheduler.evaluate(
        now=BASE_TIME,
    )

    assert scheduler.state is SchedulerState.PAUSED
    assert scheduler.next_run_at is None
    assert decision.due is False
    assert decision.reason == "PAUSED"


def test_persisted_past_deadline_is_immediately_due() -> None:
    """A persisted overdue deadline must remain due after restart."""
    scheduler = ControlledScheduler.from_persisted_state(
        SchedulerState.READY,
        BASE_TIME - timedelta(seconds=1),
    )

    decision = scheduler.evaluate(
        now=BASE_TIME,
    )

    assert decision.due is True
    assert decision.reason == "DUE"


def test_persisted_future_deadline_remains_not_due() -> None:
    """A persisted future deadline must remain blocked until due."""
    next_run_at = BASE_TIME + timedelta(seconds=60)

    scheduler = ControlledScheduler.from_persisted_state(
        SchedulerState.READY,
        next_run_at,
    )

    decision = scheduler.evaluate(
        now=BASE_TIME + timedelta(seconds=59),
    )

    assert decision.due is False
    assert decision.reason == "NOT_DUE"
    assert decision.next_run_at == next_run_at


def test_persisted_initial_state_preserves_initial_run() -> None:
    """A null persisted deadline must preserve INITIAL_RUN semantics."""
    scheduler = ControlledScheduler.from_persisted_state(
        SchedulerState.READY,
        None,
    )

    decision = scheduler.evaluate(
        now=BASE_TIME,
    )

    assert decision.due is True
    assert decision.reason == "INITIAL_RUN"


def test_persisted_naive_deadline_is_rejected() -> None:
    """Restored scheduler deadlines must remain timezone-aware."""
    with pytest.raises(
        ValueError,
        match="next_run_at must be timezone-aware",
    ):
        ControlledScheduler.from_persisted_state(
            SchedulerState.READY,
            datetime(
                2026,
                8,
                31,
                12,
                0,
            ),
        )
