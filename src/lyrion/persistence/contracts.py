"""Durable runtime and recovery contracts for Lyrion."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from lyrion.core.types import AutonomyLevel, CorrelationId, EventId, IdempotencyKey, OpportunityId, TaskId
from lyrion.events.models import EventSensitivity, EventTrustLevel


class RuntimeLifecycleState(StrEnum):
    """Persistent lifecycle state of one runtime instance."""

    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    RECOVERING = "RECOVERING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class PersistentExecutionState(StrEnum):
    """Durable lifecycle state of one proactive execution."""

    QUEUED = "QUEUED"
    CLAIMED = "CLAIMED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"
    ABANDONED = "ABANDONED"


class RecoveryAction(StrEnum):
    """Explicit recovery decisions for interrupted work."""

    NOOP = "NOOP"
    REQUEUE = "REQUEUE"
    QUARANTINE = "QUARANTINE"
    RECONCILE = "RECONCILE"


class RuntimeInstance(BaseModel):
    """Immutable durable identity and lifecycle state for one runtime."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    instance_id: str = Field(
        min_length=1,
        max_length=200,
    )
    state: RuntimeLifecycleState
    started_at: datetime
    heartbeat_at: datetime
    revision: int = Field(
        default=1,
        ge=1,
    )

    @field_validator("started_at", "heartbeat_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime,
    ) -> datetime:
        """Require timezone-aware runtime timestamps."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "runtime timestamps must be timezone-aware"
            )

        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_heartbeat(self) -> RuntimeInstance:
        """Ensure heartbeat does not precede runtime startup."""
        if self.heartbeat_at < self.started_at:
            raise ValueError(
                "heartbeat_at cannot be earlier than started_at"
            )

        return self


class RuntimeLease(BaseModel):
    """Immutable ownership lease for a durable runtime resource."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    lease_id: str = Field(
        min_length=1,
        max_length=200,
    )
    resource_id: str = Field(
        min_length=1,
        max_length=500,
    )
    worker_id: str = Field(
        min_length=1,
        max_length=200,
    )
    acquired_at: datetime
    expires_at: datetime
    revision: int = Field(
        default=1,
        ge=1,
    )

    @field_validator("acquired_at", "expires_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime,
    ) -> datetime:
        """Require timezone-aware lease timestamps."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "lease timestamps must be timezone-aware"
            )

        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_expiry(self) -> RuntimeLease:
        """Ensure lease expiry follows acquisition."""
        if self.expires_at <= self.acquired_at:
            raise ValueError(
                "expires_at must be later than acquired_at"
            )

        return self

    def is_expired(
        self,
        now: datetime,
    ) -> bool:
        """Return whether the lease has expired."""
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError(
                "now must be timezone-aware"
            )

        return now.astimezone(UTC) >= self.expires_at


class PersistentSchedulerState(StrEnum):
    """Durable lifecycle state of the proactive scheduler."""

    READY = "READY"
    PAUSED = "PAUSED"


class PersistentScheduler(BaseModel):
    """Durable scheduling state for one proactive scheduler."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    scheduler_id: str = Field(
        min_length=1,
        max_length=200,
    )
    state: PersistentSchedulerState
    next_run_at: datetime | None = None
    revision: int = Field(
        default=1,
        ge=1,
    )

    @field_validator("next_run_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        """Require a timezone-aware scheduled timestamp."""
        if value is None:
            return None

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "next_run_at must be timezone-aware"
            )

        return value.astimezone(UTC)


class OpportunityRecoveryContext(BaseModel):
    """Immutable durable recovery context for R097 recovery.

    Recovery restores work context and lineage only; execution authority
    must always be re-established through fresh admission.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")
    opportunity_id: OpportunityId
    correlation_id: CorrelationId | None
    trigger_event_ids: tuple[EventId, ...]
    source_provenance_ref: str
    relevant_state_ids: tuple[str, ...]
    goal_context: tuple[str, ...]
    title: str
    description: str
    user_relevance: float
    expected_benefit: float
    interruption_cost: float
    risk_score: float
    reversibility: float
    urgency: float
    confidence: float
    required_capabilities: tuple[str, ...]
    required_autonomy_level: AutonomyLevel
    sensitivity: EventSensitivity
    trust_level: EventTrustLevel
    original_status: str
    created_at: datetime
    expires_at: datetime | None
    schema_version: str
    context_revision: int
    integrity_digest: str

class PersistentExecutionRecord(BaseModel):
    """Durable identity and lifecycle record for one execution."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    execution_id: str = Field(
        min_length=1,
        max_length=500,
    )
    request_id: str = Field(
        min_length=1,
        max_length=500,
    )
    opportunity_id: OpportunityId
    task_id: TaskId
    idempotency_key: IdempotencyKey

    state: PersistentExecutionState

    created_at: datetime
    claimed_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    worker_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    lease_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    checkpoint_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )

    error_code: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    error_message: str | None = Field(
        default=None,
        max_length=4000,
    )

    revision: int = Field(
        default=1,
        ge=1,
    )

    @field_validator(
        "created_at",
        "claimed_at",
        "started_at",
        "completed_at",
    )
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        """Require timezone-aware execution timestamps."""
        if value is None:
            return None

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "execution timestamps must be timezone-aware"
            )

        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_lifecycle_timestamps(
        self,
    ) -> PersistentExecutionRecord:
        """Require lifecycle timestamps to remain ordered."""
        timestamps = (
            self.claimed_at,
            self.started_at,
            self.completed_at,
        )

        previous = self.created_at

        for current in timestamps:
            if current is None:
                continue

            if current < previous:
                raise ValueError(
                    "execution lifecycle timestamps must be ordered"
                )

            previous = current

        terminal_states = {
            PersistentExecutionState.COMPLETED,
            PersistentExecutionState.FAILED,
            PersistentExecutionState.CANCELLED,
            PersistentExecutionState.ABANDONED,
        }

        if self.state in terminal_states and self.completed_at is None:
            raise ValueError(
                "terminal execution state requires completed_at"
            )

        if (
            self.state is PersistentExecutionState.EXECUTING
            and self.started_at is None
        ):
            raise ValueError(
                "EXECUTING state requires started_at"
            )

        return self


class PersistentOpportunityState(StrEnum):
    """Durable lifecycle state of one queued opportunity."""

    QUEUED = "QUEUED"
    CLAIMED = "CLAIMED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"
    ABANDONED = "ABANDONED"


class PersistentOpportunity(BaseModel):
    """Durable lifecycle record for one proactive opportunity."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    opportunity_id: OpportunityId
    state: PersistentOpportunityState

    created_at: datetime
    expires_at: datetime | None = None

    worker_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    lease_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    claimed_at: datetime | None = None
    completed_at: datetime | None = None

    execution_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )

    revision: int = Field(
        default=1,
        ge=1,
    )

    @field_validator(
        "created_at",
        "expires_at",
        "claimed_at",
        "completed_at",
    )
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        """Require timezone-aware lifecycle timestamps."""
        if value is None:
            return None

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "opportunity timestamps must be timezone-aware"
            )

        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_lifecycle(self) -> PersistentOpportunity:
        """Validate expiry and lifecycle timestamp ordering."""
        if (
            self.expires_at is not None
            and self.expires_at < self.created_at
        ):
            raise ValueError(
                "expires_at cannot be earlier than created_at"
            )

        previous = self.created_at

        for current in (
            self.claimed_at,
            self.completed_at,
        ):
            if current is None:
                continue

            if current < previous:
                raise ValueError(
                    "opportunity lifecycle timestamps must be ordered"
                )

            previous = current

        if (
            self.state is PersistentOpportunityState.CLAIMED
            and self.claimed_at is None
        ):
            raise ValueError(
                "CLAIMED state requires claimed_at"
            )

        if (
            self.state is PersistentOpportunityState.EXECUTING
            and (
                self.claimed_at is None
                or self.execution_id is None
            )
        ):
            raise ValueError(
                "EXECUTING state requires claimed_at and execution_id"
            )

        terminal_states = {
            PersistentOpportunityState.COMPLETED,
            PersistentOpportunityState.FAILED,
            PersistentOpportunityState.CANCELLED,
            PersistentOpportunityState.ABANDONED,
        }

        if self.state in terminal_states and self.completed_at is None:
            raise ValueError(
                "terminal opportunity state requires completed_at"
            )

        return self

    def is_expired(
        self,
        now: datetime,
    ) -> bool:
        """Return whether the durable opportunity has expired."""
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError(
                "now must be timezone-aware"
            )

        return (
            self.expires_at is not None
            and now.astimezone(UTC) >= self.expires_at
        )


class PersistentIdempotencyRecord(BaseModel):
    """Durable binding between one idempotency key and one execution."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    idempotency_key: str = Field(
        min_length=1,
        max_length=500,
    )
    request_id: str = Field(
        min_length=1,
        max_length=500,
    )
    execution_id: str = Field(
        min_length=1,
        max_length=500,
    )
    reserved_at: datetime

    @field_validator("reserved_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime,
    ) -> datetime:
        """Require a timezone-aware reservation timestamp."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "reserved_at must be timezone-aware"
            )

        return value.astimezone(UTC)


class RecoveryDecision(BaseModel):
    """Explicit result of durable runtime recovery analysis."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    execution_id: str = Field(
        min_length=1,
        max_length=500,
    )
    action: RecoveryAction
    reason: str = Field(
        min_length=1,
        max_length=2000,
    )
    evaluated_at: datetime
    source_revision: int = Field(
        default=1,
        ge=1,
    )

    @field_validator("evaluated_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime,
    ) -> datetime:
        """Require timezone-aware recovery timestamps."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "evaluated_at must be timezone-aware"
            )

        return value.astimezone(UTC)
