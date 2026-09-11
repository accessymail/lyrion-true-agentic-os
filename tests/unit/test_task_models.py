"""Unit tests for Lyrion task lifecycle contracts."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lyrion.core.types import AutonomyLevel, RiskLevel, TaskId
from lyrion.tasks.models import Task, TaskStatus


def make_task(**overrides: object) -> Task:
    """Create a valid baseline task for tests."""
    now = datetime.now(UTC)

    values: dict[str, object] = {
        "task_id": TaskId("task_test_001"),
        "objective": "Test task lifecycle",
        "status": TaskStatus.PENDING,
        "autonomy_level": AutonomyLevel.L2,
        "risk_level": RiskLevel.LOW,
        "created_at": now,
        "updated_at": now,
        "retry_count": 0,
        "max_retries": 3,
        "checkpoint_ref": None,
        "revision": 1,
        "parent_task_id": None,
        "last_error": None,
    }

    values.update(overrides)
    return Task(**values)


def test_task_creation() -> None:
    """A valid task should be accepted."""
    task = make_task()

    assert task.task_id == "task_test_001"
    assert task.status is TaskStatus.PENDING
    assert task.retry_count == 0


def test_task_is_immutable() -> None:
    """Task fields must not be mutable after creation."""
    task = make_task()

    with pytest.raises(ValidationError):
        task.objective = "modified"


def test_task_requires_timezone_aware_timestamps() -> None:
    """Naive task timestamps must be rejected."""
    naive = datetime.now()

    with pytest.raises(ValidationError):
        make_task(created_at=naive)


def test_updated_at_cannot_precede_created_at() -> None:
    """Updated time cannot precede creation time."""
    created = datetime.now(UTC)

    with pytest.raises(ValidationError):
        make_task(
            created_at=created,
            updated_at=created - timedelta(seconds=1),
        )


def test_retry_count_cannot_exceed_maximum() -> None:
    """A task cannot start with an invalid retry count."""
    with pytest.raises(ValidationError):
        make_task(retry_count=4, max_retries=3)


def test_pending_can_start() -> None:
    """Pending tasks may transition to running."""
    task = make_task()

    assert task.can_transition_to(TaskStatus.RUNNING) is True

    running = task.transition(TaskStatus.RUNNING)

    assert running.status is TaskStatus.RUNNING


def test_running_can_pause_and_resume() -> None:
    """Running tasks may pause and later resume."""
    task = make_task().transition(TaskStatus.RUNNING)

    paused = task.transition(
        TaskStatus.PAUSED,
        checkpoint_ref="checkpoint_001",
    )

    resumed = paused.transition(TaskStatus.RUNNING)

    assert paused.status is TaskStatus.PAUSED
    assert paused.checkpoint_ref == "checkpoint_001"
    assert resumed.status is TaskStatus.RUNNING


def test_running_can_complete() -> None:
    """Running tasks may complete successfully."""
    task = make_task().transition(TaskStatus.RUNNING)

    completed = task.transition(TaskStatus.COMPLETED)

    assert completed.status is TaskStatus.COMPLETED
    assert completed.last_error is None


def test_completed_is_terminal() -> None:
    """Completed tasks cannot transition to another state."""
    task = (
        make_task()
        .transition(TaskStatus.RUNNING)
        .transition(TaskStatus.COMPLETED)
    )

    assert task.can_transition_to(TaskStatus.RUNNING) is False

    with pytest.raises(ValueError):
        task.transition(TaskStatus.RUNNING)


def test_cancelled_is_terminal() -> None:
    """Cancelled tasks cannot transition to another state."""
    task = make_task().transition(TaskStatus.CANCELLED)

    assert task.can_transition_to(TaskStatus.RUNNING) is False

    with pytest.raises(ValueError):
        task.transition(TaskStatus.RUNNING)


def test_failed_task_can_retry() -> None:
    """A failed task may enter retrying state within its retry budget."""
    task = (
        make_task()
        .transition(TaskStatus.RUNNING)
        .transition(TaskStatus.FAILED, error="temporary failure")
    )

    retrying = task.transition(TaskStatus.RETRYING)

    assert retrying.status is TaskStatus.RETRYING
    assert retrying.retry_count == 1


def test_retry_budget_is_enforced() -> None:
    """Retrying must stop when the maximum retry count is reached."""
    task = make_task(max_retries=1)
    running = task.transition(TaskStatus.RUNNING)
    retrying = running.transition(TaskStatus.RETRYING)

    assert retrying.retry_count == 1

    with pytest.raises(ValueError):
        retrying.transition(TaskStatus.RETRYING)


def test_completed_task_cannot_have_error() -> None:
    """Completed tasks cannot contain an error."""
    with pytest.raises(ValidationError):
        make_task(
            status=TaskStatus.COMPLETED,
            last_error="unexpected error",
        )


def test_transition_preserves_checkpoint() -> None:
    """A checkpoint should survive later lifecycle transitions."""
    task = make_task().transition(
        TaskStatus.RUNNING,
        checkpoint_ref="checkpoint_001",
    )

    paused = task.transition(TaskStatus.PAUSED)

    assert paused.checkpoint_ref == "checkpoint_001"


def test_transition_rejects_naive_now() -> None:
    """Transition timestamps must be timezone-aware."""
    task = make_task()
    naive = datetime.now()

    with pytest.raises(ValueError):
        task.transition(TaskStatus.RUNNING, now=naive)
