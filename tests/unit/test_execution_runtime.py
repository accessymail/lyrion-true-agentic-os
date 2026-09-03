"""Adversarial tests for deterministic runtime controls."""

from datetime import UTC, datetime, timedelta

import pytest

from lyrion.execution.contracts import ResourceLimits
from lyrion.execution.runtime import (
    RuntimeBudget,
    RuntimeController,
    RuntimeState,
    RuntimeViolation,
)


def make_limits(**overrides: object) -> ResourceLimits:
    """Create baseline runtime limits."""
    values: dict[str, object] = {
        "max_runtime_seconds": 30.0,
        "max_memory_mb": 512,
        "max_output_bytes": 1_048_576,
        "max_cpu_seconds": 30.0,
    }

    values.update(overrides)

    return ResourceLimits(**values)


def make_budget(
    *,
    started_at: datetime | None = None,
    **overrides: object,
) -> RuntimeBudget:
    """Create a baseline runtime budget."""
    start = started_at or datetime.now(UTC)

    return RuntimeBudget.from_limits(
        make_limits(**overrides),
        started_at=start,
    )


def test_budget_creation() -> None:
    """A runtime budget should derive its deadline correctly."""
    started = datetime.now(UTC)

    budget = make_budget(
        started_at=started,
        max_runtime_seconds=30.0,
    )

    assert budget.started_at == started
    assert budget.deadline == started + timedelta(seconds=30)


def test_budget_rejects_naive_start() -> None:
    """Runtime budgets require timezone-aware timestamps."""
    with pytest.raises(ValueError):
        make_budget(
            started_at=datetime.now(),
        )


def test_controller_starts_ready() -> None:
    """A new runtime controller begins in READY state."""
    controller = RuntimeController(make_budget())

    assert controller.state is RuntimeState.READY
    assert controller.violation is None


def test_controller_can_start() -> None:
    """READY runtime can transition to RUNNING."""
    controller = RuntimeController(make_budget())

    controller.start()

    assert controller.state is RuntimeState.RUNNING


def test_controller_cannot_start_twice() -> None:
    """A runtime cannot be started more than once."""
    controller = RuntimeController(make_budget())

    controller.start()

    with pytest.raises(RuntimeError):
        controller.start()


def test_normal_snapshot_is_valid() -> None:
    """Usage inside all budgets should remain valid."""
    started = datetime.now(UTC)
    controller = RuntimeController(
        make_budget(started_at=started),
    )

    controller.start()

    snapshot = controller.snapshot(
        now=started + timedelta(seconds=5),
        cpu_seconds=4.0,
        memory_mb=256,
        output_bytes=100_000,
    )

    assert snapshot.state is RuntimeState.RUNNING
    assert snapshot.violation is None
    assert snapshot.elapsed_seconds == 5.0


def test_timeout_is_detected_at_deadline() -> None:
    """Crossing the runtime deadline must time out."""
    started = datetime.now(UTC)
    controller = RuntimeController(
        make_budget(
            started_at=started,
            max_runtime_seconds=10.0,
        ),
    )

    controller.start()

    snapshot = controller.snapshot(
        now=started + timedelta(seconds=10),
    )

    assert snapshot.state is RuntimeState.TIMED_OUT
    assert snapshot.violation is RuntimeViolation.TIMEOUT


def test_cpu_limit_is_enforced() -> None:
    """CPU usage above the configured budget must terminate."""
    started = datetime.now(UTC)
    controller = RuntimeController(
        make_budget(
            started_at=started,
            max_cpu_seconds=5.0,
        ),
    )

    controller.start()

    snapshot = controller.snapshot(
        now=started + timedelta(seconds=1),
        cpu_seconds=5.1,
    )

    assert snapshot.state is RuntimeState.TERMINATED
    assert snapshot.violation is RuntimeViolation.CPU_LIMIT_EXCEEDED


def test_memory_limit_is_enforced() -> None:
    """Memory usage above the configured budget must terminate."""
    started = datetime.now(UTC)
    controller = RuntimeController(
        make_budget(
            started_at=started,
            max_memory_mb=128,
        ),
    )

    controller.start()

    snapshot = controller.snapshot(
        now=started + timedelta(seconds=1),
        memory_mb=129,
    )

    assert snapshot.state is RuntimeState.TERMINATED
    assert snapshot.violation is RuntimeViolation.MEMORY_LIMIT_EXCEEDED


def test_output_limit_is_enforced() -> None:
    """Output above the configured budget must terminate."""
    started = datetime.now(UTC)
    controller = RuntimeController(
        make_budget(
            started_at=started,
            max_output_bytes=1_000,
        ),
    )

    controller.start()

    snapshot = controller.snapshot(
        now=started + timedelta(seconds=1),
        output_bytes=1_001,
    )

    assert snapshot.state is RuntimeState.TERMINATED
    assert snapshot.violation is RuntimeViolation.OUTPUT_LIMIT_EXCEEDED


def test_cancel_request_is_fail_closed() -> None:
    """Cancellation should prevent further normal execution."""
    controller = RuntimeController(make_budget())

    controller.start()
    controller.request_cancel()

    assert controller.state is RuntimeState.CANCEL_REQUESTED

    snapshot = controller.snapshot(
        now=controller.budget.started_at,
    )

    assert snapshot.violation is RuntimeViolation.CANCELLED


def test_terminate_marks_runtime_terminated() -> None:
    """Explicit termination should produce TERMINATED state."""
    controller = RuntimeController(make_budget())

    controller.start()
    controller.terminate()

    assert controller.state is RuntimeState.TERMINATED
    assert controller.violation is RuntimeViolation.TERMINATED


def test_complete_marks_runtime_completed() -> None:
    """A running runtime can complete normally."""
    controller = RuntimeController(make_budget())

    controller.start()
    controller.complete()

    assert controller.state is RuntimeState.COMPLETED
    assert controller.violation is None


def test_completed_runtime_stays_terminal() -> None:
    """Completed runtime state cannot be restarted."""
    controller = RuntimeController(make_budget())

    controller.start()
    controller.complete()

    with pytest.raises(RuntimeError):
        controller.start()


def test_terminated_runtime_stays_terminal() -> None:
    """Terminated runtime state cannot be restarted."""
    controller = RuntimeController(make_budget())

    controller.start()
    controller.terminate()

    with pytest.raises(RuntimeError):
        controller.start()


def test_timed_out_runtime_stays_terminal() -> None:
    """Timed-out runtime state cannot be restarted."""
    started = datetime.now(UTC)
    controller = RuntimeController(
        make_budget(
            started_at=started,
            max_runtime_seconds=1.0,
        ),
    )

    controller.start()

    controller.snapshot(
        now=started + timedelta(seconds=1),
    )

    with pytest.raises(RuntimeError):
        controller.start()


def test_snapshot_rejects_naive_clock() -> None:
    """Runtime observations require timezone-aware timestamps."""
    controller = RuntimeController(make_budget())

    with pytest.raises(ValueError):
        controller.snapshot(
            now=datetime.now(),
        )


def test_snapshot_rejects_negative_cpu() -> None:
    """Negative CPU observations must be rejected."""
    controller = RuntimeController(make_budget())

    with pytest.raises(ValueError):
        controller.snapshot(
            now=controller.budget.started_at,
            cpu_seconds=-1,
        )


def test_snapshot_rejects_negative_memory() -> None:
    """Negative memory observations must be rejected."""
    controller = RuntimeController(make_budget())

    with pytest.raises(ValueError):
        controller.snapshot(
            now=controller.budget.started_at,
            memory_mb=-1,
        )


def test_snapshot_rejects_negative_output() -> None:
    """Negative output observations must be rejected."""
    controller = RuntimeController(make_budget())

    with pytest.raises(ValueError):
        controller.snapshot(
            now=controller.budget.started_at,
            output_bytes=-1,
        )


def test_snapshot_rejects_time_before_start() -> None:
    """Runtime clock cannot move before execution start."""
    started = datetime.now(UTC)
    controller = RuntimeController(
        make_budget(started_at=started),
    )

    controller.start()

    with pytest.raises(ValueError):
        controller.snapshot(
            now=started - timedelta(seconds=1),
        )


def test_require_within_limits_returns_snapshot() -> None:
    """Valid runtime usage should pass the fail-closed helper."""
    started = datetime.now(UTC)
    controller = RuntimeController(
        make_budget(started_at=started),
    )

    controller.start()

    snapshot = controller.require_within_limits(
        now=started + timedelta(seconds=1),
        cpu_seconds=1.0,
        memory_mb=128,
        output_bytes=1_000,
    )

    assert snapshot.state is RuntimeState.RUNNING
    assert snapshot.violation is None


def test_require_within_limits_raises_on_violation() -> None:
    """Runtime violations must raise at the enforcement boundary."""
    started = datetime.now(UTC)
    controller = RuntimeController(
        make_budget(
            started_at=started,
            max_memory_mb=128,
        ),
    )

    controller.start()

    with pytest.raises(
        RuntimeError,
        match="MEMORY_LIMIT_EXCEEDED",
    ):
        controller.require_within_limits(
            now=started + timedelta(seconds=1),
            memory_mb=129,
        )


def test_completed_snapshot_preserves_terminal_state() -> None:
    """Terminal snapshots preserve completed state."""
    started = datetime.now(UTC)
    controller = RuntimeController(
        make_budget(started_at=started),
    )

    controller.start()
    controller.complete()

    snapshot = controller.snapshot(
        now=started + timedelta(seconds=5),
    )

    assert snapshot.state is RuntimeState.COMPLETED
    assert snapshot.violation is None


def test_runtime_budget_is_immutable() -> None:
    """Runtime budgets must be immutable value objects."""
    budget = make_budget()

    with pytest.raises(AttributeError):
        budget.max_memory_mb = 999


def test_runtime_control_is_deterministic() -> None:
    """Equivalent observations should produce equivalent snapshots."""
    started = datetime.now(UTC)

    first_controller = RuntimeController(
        make_budget(started_at=started),
    )
    second_controller = RuntimeController(
        make_budget(started_at=started),
    )

    first_controller.start()
    second_controller.start()

    first = first_controller.snapshot(
        now=started + timedelta(seconds=5),
        cpu_seconds=2.0,
        memory_mb=128,
        output_bytes=100,
    )
    second = second_controller.snapshot(
        now=started + timedelta(seconds=5),
        cpu_seconds=2.0,
        memory_mb=128,
        output_bytes=100,
    )

    assert first == second
