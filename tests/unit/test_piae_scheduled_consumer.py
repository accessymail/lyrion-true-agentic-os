"""Adversarial tests for scheduler-controlled PIAE consumption."""

from datetime import UTC, datetime, timedelta

import pytest

from lyrion.piae.controlled_queue_consumer import (
    ControlledQueueCycleResult,
)
from lyrion.piae.scheduled_consumer import (
    CandidateFactory,
    ScheduledPIAEConsumer,
)
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


class FakeBoundedConsumer:
    """Record bounded-consumer invocations."""

    def __init__(
        self,
        result: ControlledQueueCycleResult | None = None,
    ) -> None:
        self.calls = 0
        self.times: list[datetime | None] = []
        self.result = result or ControlledQueueCycleResult(
            items=(),
            stop_reason="QUEUE_EMPTY",
        )

    def run_once(
        self,
        *,
        candidates_factory: CandidateFactory,
        now: datetime | None = None,
    ) -> ControlledQueueCycleResult:
        """Record one bounded invocation."""
        del candidates_factory

        self.calls += 1
        self.times.append(now)

        return self.result


def make_controller(
    *,
    interval_seconds: float = 60.0,
    start_at: datetime | None = None,
    consumer: FakeBoundedConsumer | None = None,
) -> tuple[
    ScheduledPIAEConsumer,
    FakeBoundedConsumer,
]:
    """Create a scheduler-controlled consumer."""
    fake_consumer = consumer or FakeBoundedConsumer()

    scheduler = ControlledScheduler(
        ControlledSchedulerConfig(
            interval_seconds=interval_seconds,
        ),
        start_at=start_at,
    )

    return (
        ScheduledPIAEConsumer(
            scheduler,
            fake_consumer,
        ),
        fake_consumer,
    )


def test_initial_run_is_allowed() -> None:
    """A new scheduler should allow the initial cycle."""
    controller, consumer = make_controller()

    result = controller.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME,
    )

    assert result.ran is True
    assert consumer.calls == 1
    assert result.scheduler.reason == "INITIAL_RUN"


def test_not_due_does_not_invoke_consumer() -> None:
    """An early scheduled check must not consume queue work."""
    controller, consumer = make_controller(
        start_at=BASE_TIME,
    )

    result = controller.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME + timedelta(seconds=59),
    )

    assert result.ran is False
    assert result.scheduler.reason == "NOT_DUE"
    assert consumer.calls == 0


def test_due_invokes_consumer_once() -> None:
    """A due scheduler should invoke exactly one bounded cycle."""
    controller, consumer = make_controller(
        start_at=BASE_TIME,
    )

    result = controller.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME + timedelta(seconds=60),
    )

    assert result.ran is True
    assert consumer.calls == 1
    assert consumer.times == [
        BASE_TIME + timedelta(seconds=60),
    ]


def test_completed_cycle_advances_schedule() -> None:
    """A completed cycle must schedule the next cycle."""
    controller, consumer = make_controller()

    result = controller.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME,
    )

    assert consumer.calls == 1
    assert result.next_run_at == (
        BASE_TIME + timedelta(seconds=60)
    )
    assert controller.scheduler.next_run_at == (
        BASE_TIME + timedelta(seconds=60)
    )


def test_followup_before_next_run_is_blocked() -> None:
    """A second early invocation must remain blocked."""
    controller, consumer = make_controller()

    controller.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME,
    )

    result = controller.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME + timedelta(seconds=59),
    )

    assert result.ran is False
    assert consumer.calls == 1


def test_followup_at_next_run_is_allowed() -> None:
    """The next scheduled time permits another cycle."""
    controller, consumer = make_controller()

    controller.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME,
    )

    result = controller.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME + timedelta(seconds=60),
    )

    assert result.ran is True
    assert consumer.calls == 2


def test_pause_blocks_real_consumer() -> None:
    """Paused scheduling must prevent bounded consumption."""
    controller, consumer = make_controller()

    controller.scheduler.pause()

    result = controller.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME,
    )

    assert result.ran is False
    assert result.scheduler.state is SchedulerState.PAUSED
    assert result.scheduler.reason == "PAUSED"
    assert consumer.calls == 0


def test_resume_allows_immediate_cycle() -> None:
    """Resume should make the next external invocation eligible."""
    controller, consumer = make_controller()

    controller.scheduler.pause()

    resumed_at = controller.scheduler.resume(
        now=BASE_TIME + timedelta(minutes=5),
    )

    result = controller.run_once(
        candidates_factory=lambda _opportunity: (),
        now=resumed_at,
    )

    assert result.ran is True
    assert consumer.calls == 1


def test_consumer_failure_result_does_not_bypass_scheduler() -> None:
    """A failed bounded result still advances scheduling normally."""
    failed_result = ControlledQueueCycleResult(
        items=(),
        stop_reason="MAX_OPPORTUNITIES_REACHED",
    )

    controller, fake_consumer = make_controller(
        consumer=FakeBoundedConsumer(
            result=failed_result,
        ),
    )

    result = controller.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME,
    )

    assert result.ran is True
    assert fake_consumer.calls == 1
    assert result.next_run_at == (
        BASE_TIME + timedelta(seconds=60)
    )


def test_naive_time_fails_closed() -> None:
    """The scheduler integration must reject naive timestamps."""
    controller, consumer = make_controller()

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        controller.run_once(
            candidates_factory=lambda _opportunity: (),
            now=datetime(
                2026,
                8,
                31,
                12,
                0,
            ),
        )

    assert consumer.calls == 0


def test_scheduler_has_no_execution_authority() -> None:
    """Scheduling remains separate from execution authority."""
    controller, _ = make_controller()

    assert not hasattr(
        controller.scheduler,
        "authorize",
    )
    assert not hasattr(
        controller.scheduler,
        "execute",
    )


def test_not_due_result_exposes_no_cycle() -> None:
    """A blocked invocation must expose no consumption result."""
    controller, consumer = make_controller(
        start_at=BASE_TIME,
    )

    result = controller.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME,
    )

    controller.scheduler.pause()

    paused = controller.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME,
    )

    assert result.cycle is None
    assert result.scheduler.reason == "NOT_DUE"
    assert paused.cycle is None
    assert paused.scheduler.reason == "PAUSED"
    assert consumer.calls == 0


def test_consumer_reference_is_exposed() -> None:
    """The underlying bounded consumer remains inspectable."""
    controller, consumer = make_controller()

    assert controller.consumer is consumer


def test_scheduler_reference_is_exposed() -> None:
    """The scheduler remains inspectable."""
    controller, _ = make_controller()

    assert isinstance(
        controller.scheduler,
        ControlledScheduler,
    )


class RaisingBoundedConsumer:
    """Bounded consumer that raises an infrastructure failure."""

    def __init__(self) -> None:
        self.calls = 0

    def run_once(
        self,
        *,
        candidates_factory: CandidateFactory,
        now: datetime | None = None,
    ) -> ControlledQueueCycleResult:
        """Raise without returning a cycle result."""
        del candidates_factory
        del now

        self.calls += 1

        raise RuntimeError(
            "intentional infrastructure failure"
        )


def test_consumer_exception_advances_schedule() -> None:
    """Infrastructure failure must not create an immediate retry loop."""
    consumer = RaisingBoundedConsumer()

    scheduler = ControlledScheduler()

    controller = ScheduledPIAEConsumer(
        scheduler,
        consumer,
    )

    with pytest.raises(
        RuntimeError,
        match="intentional infrastructure failure",
    ):
        controller.run_once(
            candidates_factory=lambda _opportunity: (),
            now=BASE_TIME,
        )

    assert consumer.calls == 1
    assert scheduler.next_run_at == (
        BASE_TIME + timedelta(seconds=60)
    )


def test_consumer_exception_does_not_immediately_retry() -> None:
    """A failed cycle must remain blocked until its next schedule."""
    consumer = RaisingBoundedConsumer()

    scheduler = ControlledScheduler()

    controller = ScheduledPIAEConsumer(
        scheduler,
        consumer,
    )

    with pytest.raises(RuntimeError):
        controller.run_once(
            candidates_factory=lambda _opportunity: (),
            now=BASE_TIME,
        )

    decision = scheduler.evaluate(
        now=BASE_TIME,
    )

    assert decision.due is False
    assert decision.reason == "NOT_DUE"
    assert consumer.calls == 1


def test_consumer_exception_allows_later_scheduled_attempt() -> None:
    """A later external tick may attempt another cycle."""
    consumer = RaisingBoundedConsumer()

    scheduler = ControlledScheduler()

    controller = ScheduledPIAEConsumer(
        scheduler,
        consumer,
    )

    with pytest.raises(RuntimeError):
        controller.run_once(
            candidates_factory=lambda _opportunity: (),
            now=BASE_TIME,
        )

    with pytest.raises(RuntimeError):
        controller.run_once(
            candidates_factory=lambda _opportunity: (),
            now=BASE_TIME + timedelta(seconds=60),
        )

    assert consumer.calls == 2


def test_pause_after_completed_cycle_preserves_next_run() -> None:
    """Pausing must not erase an already scheduled next run."""
    controller, consumer = make_controller()

    result = controller.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME,
    )

    assert result.next_run_at == (
        BASE_TIME + timedelta(seconds=60)
    )

    controller.scheduler.pause()

    decision = controller.scheduler.evaluate(
        now=BASE_TIME + timedelta(seconds=60),
    )

    assert decision.due is False
    assert decision.reason == "PAUSED"
    assert decision.next_run_at == (
        BASE_TIME + timedelta(seconds=60)
    )
    assert consumer.calls == 1


def test_resume_replaces_pause_with_immediate_eligibility() -> None:
    """Resume intentionally establishes an immediate eligible run."""
    controller, consumer = make_controller()

    controller.run_once(
        candidates_factory=lambda _opportunity: (),
        now=BASE_TIME,
    )

    controller.scheduler.pause()

    resumed_at = controller.scheduler.resume(
        now=BASE_TIME + timedelta(minutes=5),
    )

    decision = controller.scheduler.evaluate(
        now=resumed_at,
    )

    assert decision.due is True
    assert decision.reason == "DUE"
    assert decision.next_run_at == resumed_at
    assert consumer.calls == 1
