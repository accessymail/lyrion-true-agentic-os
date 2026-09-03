"""Adversarial tests for execution-result feedback."""

from datetime import UTC, datetime, timedelta

import pytest

from lyrion.core.types import EventId
from lyrion.execution.contracts import (
    ExecutionResult,
    ExecutionStatus,
)
from lyrion.state.execution_feedback import ExecutionFeedback


def make_result(
    *,
    status: ExecutionStatus = ExecutionStatus.COMPLETED,
) -> ExecutionResult:
    """Create a valid execution result."""
    started_at = datetime(
        2026,
        8,
        31,
        10,
        0,
        tzinfo=UTC,
    )

    completed_at = started_at + timedelta(
        seconds=2,
    )

    return ExecutionResult(
        execution_id="execution:test-001",
        request_id="request:test-001",
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        exit_code=0 if status is ExecutionStatus.COMPLETED else None,
        output_ref="output:test-001",
        error_code=(
            "TEST_FAILURE"
            if status is ExecutionStatus.FAILED
            else None
        ),
        error_message=(
            "intentional test failure"
            if status is ExecutionStatus.FAILED
            else None
        ),
        checkpoint_ref=None,
    )


def test_feedback_preserves_execution_identity() -> None:
    """Feedback must preserve execution identity exactly."""
    feedback = ExecutionFeedback.from_execution_result(
        make_result(),
        source_event_ids=(
            EventId("event:test-001"),
        ),
    )

    assert feedback.execution_id == (
        "execution:test-001"
    )
    assert feedback.request_id == (
        "request:test-001"
    )


def test_feedback_preserves_terminal_status() -> None:
    """Execution status must remain unchanged."""
    result = make_result(
        status=ExecutionStatus.FAILED,
    )

    feedback = ExecutionFeedback.from_execution_result(
        result,
        source_event_ids=(
            EventId("event:test-001"),
        ),
    )

    assert feedback.status is ExecutionStatus.FAILED
    assert feedback.error_code == "TEST_FAILURE"


def test_source_events_are_required() -> None:
    """Feedback must retain provenance."""
    with pytest.raises(
        ValueError,
        match="at least one source event",
    ):
        ExecutionFeedback.from_execution_result(
            make_result(),
            source_event_ids=(),
        )


def test_duplicate_source_events_are_rejected() -> None:
    """Provenance references must remain unique."""
    event_id = EventId("event:duplicate")

    with pytest.raises(
        ValueError,
        match="source event references must be unique",
    ):
        ExecutionFeedback.from_execution_result(
            make_result(),
            source_event_ids=(
                event_id,
                event_id,
            ),
        )


def test_naive_started_time_is_rejected() -> None:
    """Feedback must reject naive timestamps."""
    with pytest.raises(
        ValueError,
        match="started_at must be timezone-aware",
    ):
        ExecutionFeedback(
            execution_id="execution:test",
            request_id="request:test",
            status=ExecutionStatus.COMPLETED,
            started_at=datetime(
                2026,
                8,
                31,
                10,
                0,
            ),
            completed_at=None,
            output_ref=None,
            error_code=None,
            checkpoint_ref=None,
            correlation_id=None,
            source_event_ids=(
                EventId("event:test"),
            ),
        )


def test_completed_time_cannot_precede_started_time() -> None:
    """Feedback must preserve execution chronology."""
    started_at = datetime(
        2026,
        8,
        31,
        10,
        0,
        tzinfo=UTC,
    )

    with pytest.raises(
        ValueError,
        match="completed_at cannot be earlier",
    ):
        ExecutionFeedback(
            execution_id="execution:test",
            request_id="request:test",
            status=ExecutionStatus.COMPLETED,
            started_at=started_at,
            completed_at=started_at - timedelta(
                seconds=1,
            ),
            output_ref=None,
            error_code=None,
            checkpoint_ref=None,
            correlation_id=None,
            source_event_ids=(
                EventId("event:test"),
            ),
        )


def test_feedback_is_immutable() -> None:
    """Feedback evidence must remain immutable."""
    feedback = ExecutionFeedback.from_execution_result(
        make_result(),
        source_event_ids=(
            EventId("event:test"),
        ),
    )

    with pytest.raises(
        AttributeError,
    ):
        feedback.execution_id = "forged"  # type: ignore[misc]


def test_feedback_does_not_change_result() -> None:
    """Building feedback must not mutate the source result."""
    result = make_result()

    feedback = ExecutionFeedback.from_execution_result(
        result,
        source_event_ids=(
            EventId("event:test"),
        ),
    )

    assert feedback.execution_id == result.execution_id
    assert feedback.request_id == result.request_id
    assert feedback.status is result.status
