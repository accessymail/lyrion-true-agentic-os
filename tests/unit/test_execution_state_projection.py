"""Adversarial tests for execution-to-state projection."""

from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from pydantic import ValidationError

from lyrion.core.types import EventId
from lyrion.execution.contracts import (
    ExecutionResult,
    ExecutionStatus,
)
from lyrion.state.execution_feedback import ExecutionFeedback
from lyrion.state.execution_state_projection import (
    ExecutionStateProjectionAdapter,
)
from lyrion.state.models import StateValueType


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
        execution_id="execution:projection:001",
        request_id="request:projection:001",
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        exit_code=0 if status is ExecutionStatus.COMPLETED else 1,
        output_ref="output:projection:001",
        error_code=(
            None
            if status is ExecutionStatus.COMPLETED
            else "EXECUTION_FAILED"
        ),
        error_message=(
            None
            if status is ExecutionStatus.COMPLETED
            else "projection test failure"
        ),
        checkpoint_ref=None,
    )


def make_feedback(
    *,
    status: ExecutionStatus = ExecutionStatus.COMPLETED,
) -> ExecutionFeedback:
    """Create validated execution feedback."""
    return ExecutionFeedback.from_execution_result(
        make_result(
            status=status,
        ),
        source_event_ids=(
            EventId("event:projection:001"),
        ),
    )


def make_state_value(
    state_value: object,
) -> dict[str, object]:
    """Cast the projection payload to its known object shape."""
    assert isinstance(state_value, dict)
    return cast(dict[str, object], state_value)


def test_projection_preserves_execution_identity() -> None:
    """Projected state must preserve execution identity."""
    feedback = make_feedback()

    state = ExecutionStateProjectionAdapter().project(
        feedback,
        subject="lyri",
        now=feedback.completed_at,
    )

    assert state.state_id == (
        "state:execution:execution:projection:001"
    )
    assert state.key == "execution_outcome"
    assert state.value_type is StateValueType.OBJECT
    assert state.evidence_refs == (
        EventId("event:projection:001"),
    )


def test_projection_preserves_execution_status() -> None:
    """State must record the exact execution status."""
    feedback = make_feedback(
        status=ExecutionStatus.FAILED,
    )

    state = ExecutionStateProjectionAdapter().project(
        feedback,
        subject="lyri",
        now=feedback.completed_at,
    )

    value = make_state_value(state.value)

    assert value["status"] == "FAILED"
    assert value["execution_id"] == (
        feedback.execution_id
    )
    assert value["request_id"] == (
        feedback.request_id
    )


def test_projection_preserves_failure_information() -> None:
    """Failure metadata must remain available as evidence."""
    feedback = make_feedback(
        status=ExecutionStatus.FAILED,
    )

    state = ExecutionStateProjectionAdapter().project(
        feedback,
        subject="lyri",
        now=feedback.completed_at,
    )

    value = make_state_value(state.value)

    assert value["error_code"] == (
        "EXECUTION_FAILED"
    )
    assert value["error_code"] == (
        feedback.error_code
    )


def test_projection_requires_existing_event_provenance() -> None:
    """Feedback without provenance cannot produce state."""
    with pytest.raises(
        ValueError,
        match="at least one source event",
    ):
        ExecutionFeedback.from_execution_result(
            make_result(),
            source_event_ids=(),
        )


def test_projection_rejects_naive_now() -> None:
    """Projection time must be timezone-aware."""
    feedback = make_feedback()

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        ExecutionStateProjectionAdapter().project(
            feedback,
            subject="lyri",
            now=datetime.now(),
        )


def test_projection_rejects_future_effective_time() -> None:
    """State cannot become effective in the future."""
    feedback = make_feedback()

    assert feedback.completed_at is not None

    with pytest.raises(
        ValueError,
        match="future",
    ):
        ExecutionStateProjectionAdapter().project(
            feedback,
            subject="lyri",
            now=feedback.started_at,
        )


def test_projection_uses_completed_time_when_available() -> None:
    """Completed executions use completion time as effective time."""
    feedback = make_feedback()

    assert feedback.completed_at is not None

    state = ExecutionStateProjectionAdapter().project(
        feedback,
        subject="lyri",
        now=feedback.completed_at,
    )

    assert state.effective_at == (
        feedback.completed_at
    )


def test_projection_uses_started_time_when_incomplete() -> None:
    """Incomplete executions use start time as effective time."""
    result = make_result(
        status=ExecutionStatus.DENIED,
    ).model_copy(
        update={
            "completed_at": None,
        },
    )

    feedback = ExecutionFeedback.from_execution_result(
        result,
        source_event_ids=(
            EventId("event:projection:denied"),
        ),
    )

    state = ExecutionStateProjectionAdapter().project(
        feedback,
        subject="lyri",
        now=feedback.started_at,
    )

    assert state.effective_at == feedback.started_at


def test_projection_is_immutable() -> None:
    """Projected state must remain immutable."""
    feedback = make_feedback()

    state = ExecutionStateProjectionAdapter().project(
        feedback,
        subject="lyri",
        now=feedback.completed_at,
    )

    with pytest.raises(
        ValidationError,
    ):
        state.key = "authorization"  # type: ignore[misc]


def test_projection_does_not_emit_authorization_state() -> None:
    """Execution feedback must not become an authorization signal."""
    feedback = make_feedback()

    state = ExecutionStateProjectionAdapter().project(
        feedback,
        subject="lyri",
        now=feedback.completed_at,
    )

    value = make_state_value(state.value)

    assert state.key == "execution_outcome"
    assert "authorization" not in state.key.lower()
    assert "authorize" not in str(value).lower()
