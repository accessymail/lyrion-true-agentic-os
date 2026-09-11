"""Execution-result feedback contracts for Lyrion state projection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from lyrion.core.types import CorrelationId, EventId
from lyrion.execution.contracts import (
    ExecutionResult,
    ExecutionStatus,
)


@dataclass(frozen=True, slots=True)
class ExecutionFeedback:
    """Immutable evidence describing one completed execution attempt."""

    execution_id: str
    request_id: str
    status: ExecutionStatus
    started_at: datetime
    completed_at: datetime | None
    output_ref: str | None
    error_code: str | None
    checkpoint_ref: str | None
    correlation_id: CorrelationId | None
    source_event_ids: tuple[EventId, ...]

    def __post_init__(self) -> None:
        """Validate feedback invariants."""
        if not self.execution_id.strip():
            raise ValueError(
                "execution_id must not be empty"
            )

        if not self.request_id.strip():
            raise ValueError(
                "request_id must not be empty"
            )

        if not self.source_event_ids:
            raise ValueError(
                "at least one source event is required"
            )

        if len(set(self.source_event_ids)) != len(
            self.source_event_ids
        ):
            raise ValueError(
                "source event references must be unique"
            )

        if (
            self.started_at.tzinfo is None
            or self.started_at.utcoffset() is None
        ):
            raise ValueError(
                "started_at must be timezone-aware"
            )

        if self.completed_at is not None:
            if (
                self.completed_at.tzinfo is None
                or self.completed_at.utcoffset() is None
            ):
                raise ValueError(
                    "completed_at must be timezone-aware"
                )

            if self.completed_at < self.started_at:
                raise ValueError(
                    "completed_at cannot be earlier than started_at"
                )

    @classmethod
    def from_execution_result(
        cls,
        result: ExecutionResult,
        *,
        source_event_ids: tuple[EventId, ...],
    ) -> ExecutionFeedback:
        """Create immutable feedback from a validated execution result."""
        return cls(
            execution_id=result.execution_id,
            request_id=result.request_id,
            status=result.status,
            started_at=result.started_at.astimezone(UTC),
            completed_at=(
                result.completed_at.astimezone(UTC)
                if result.completed_at is not None
                else None
            ),
            output_ref=result.output_ref,
            error_code=result.error_code,
            checkpoint_ref=result.checkpoint_ref,
            correlation_id=None,
            source_event_ids=source_event_ids,
        )
