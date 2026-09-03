"""Deterministic task lifecycle contracts for Lyrion Intelligence OS."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lyrion.core.types import AutonomyLevel, RiskLevel, TaskId


class TaskStatus(StrEnum):
    """Lifecycle states for a Lyrion task."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    RETRYING = "RETRYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskTransition(StrEnum):
    """Supported lifecycle transition intents."""

    START = "START"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    RETRY = "RETRY"
    COMPLETE = "COMPLETE"
    FAIL = "FAIL"
    CANCEL = "CANCEL"


class Task(BaseModel):
    """Immutable task contract used by the Lyrion task lifecycle."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        validate_assignment=True,
    )

    task_id: TaskId
    objective: str = Field(min_length=1, max_length=2000)

    status: TaskStatus = TaskStatus.PENDING

    autonomy_level: AutonomyLevel
    risk_level: RiskLevel

    created_at: datetime
    updated_at: datetime

    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=0)

    checkpoint_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )

    revision: int = Field(default=1, ge=1)

    parent_task_id: TaskId | None = None

    last_error: str | None = Field(
        default=None,
        max_length=4000,
    )

    @model_validator(mode="after")
    def validate_task(self) -> Task:
        """Validate task timestamp and retry invariants."""

        for name, value in (
            ("created_at", self.created_at),
            ("updated_at", self.updated_at),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")

        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")

        if self.retry_count > self.max_retries:
            raise ValueError("retry_count cannot exceed max_retries")

        if self.status is TaskStatus.COMPLETED and self.last_error is not None:
            raise ValueError("completed task cannot contain last_error")

        return self

    def can_transition_to(self, target: TaskStatus) -> bool:
        """Return whether the requested lifecycle transition is allowed."""

        allowed: dict[TaskStatus, frozenset[TaskStatus]] = {
            TaskStatus.PENDING: frozenset(
                {
                    TaskStatus.RUNNING,
                    TaskStatus.CANCELLED,
                }
            ),
            TaskStatus.RUNNING: frozenset(
                {
                    TaskStatus.PAUSED,
                    TaskStatus.RETRYING,
                    TaskStatus.COMPLETED,
                    TaskStatus.FAILED,
                    TaskStatus.CANCELLED,
                }
            ),
            TaskStatus.PAUSED: frozenset(
                {
                    TaskStatus.RUNNING,
                    TaskStatus.CANCELLED,
                }
            ),
            TaskStatus.RETRYING: frozenset(
                {
                    TaskStatus.RUNNING,
                    TaskStatus.FAILED,
                    TaskStatus.CANCELLED,
                }
            ),
            TaskStatus.COMPLETED: frozenset(),
            TaskStatus.FAILED: frozenset(
                {
                    TaskStatus.RETRYING,
                    TaskStatus.CANCELLED,
                }
            ),
            TaskStatus.CANCELLED: frozenset(),
        }

        return target in allowed[self.status]

    def transition(
        self,
        target: TaskStatus,
        *,
        now: datetime | None = None,
        error: str | None = None,
        checkpoint_ref: str | None = None,
    ) -> Task:
        """Return a new task with a validated lifecycle transition."""
        if not self.can_transition_to(target):
            raise ValueError(
                f"invalid task transition: {self.status} -> {target}"
            )

        current_time = now or datetime.now(UTC)

        if current_time.tzinfo is None or current_time.utcoffset() is None:
            raise ValueError("now must be timezone-aware")

        next_retry_count = self.retry_count

        if target is TaskStatus.RETRYING:
            if self.retry_count >= self.max_retries:
                raise ValueError("maximum retry count reached")
            next_retry_count += 1

        next_checkpoint = (
            checkpoint_ref
            if checkpoint_ref is not None
            else self.checkpoint_ref
        )

        next_error = error

        if target is TaskStatus.COMPLETED:
            next_error = None

        return self.model_copy(
            update={
                "status": target,
                "updated_at": current_time,
                "retry_count": next_retry_count,
                "checkpoint_ref": next_checkpoint,
                "last_error": next_error,
            }
        )
