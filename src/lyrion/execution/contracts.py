"""Secure execution contracts for Lyrion Intelligence OS."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from lyrion.core.types import (
    AutonomyLevel,
    CorrelationId,
    ExecutionTarget,
    IdempotencyKey,
    RiskLevel,
    TaskId,
)


class ExecutionStatus(StrEnum):
    """Lifecycle state of a secure execution."""

    ADMITTED = "ADMITTED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"
    TERMINATED = "TERMINATED"
    DENIED = "DENIED"


class ResourceLimits(BaseModel):
    """Explicit resource limits for one execution."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    max_runtime_seconds: float = Field(
        default=30.0,
        gt=0.0,
    )
    max_memory_mb: int = Field(
        default=512,
        gt=0,
    )
    max_output_bytes: int = Field(
        default=1_048_576,
        gt=0,
    )
    max_cpu_seconds: float = Field(
        default=30.0,
        gt=0.0,
    )


class ExecutionRequest(BaseModel):
    """Immutable request entering the secure execution boundary."""

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
    task_id: TaskId

    capability_id: str = Field(
        min_length=1,
        max_length=500,
    )
    target_scope: str = Field(
        min_length=1,
        max_length=1000,
    )
    operation: str = Field(
        min_length=1,
        max_length=200,
    )

    authorization_reference: str = Field(
        min_length=1,
        max_length=500,
    )
    policy_version: str = Field(
        min_length=1,
        max_length=200,
    )

    principal_id: str = Field(
        min_length=1,
        max_length=500,
    )

    autonomy_level: AutonomyLevel
    risk_level: RiskLevel

    resource_limits: ResourceLimits

    network_access_allowed: bool = False
    external_side_effects_allowed: bool = False

    checkpoint_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )

    idempotency_key: IdempotencyKey

    correlation_id: CorrelationId | None = None

    requested_at: datetime
    expires_at: datetime

    @field_validator("requested_at", "expires_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime,
    ) -> datetime:
        """Require timezone-aware execution timestamps."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "execution timestamps must be timezone-aware"
            )

        return value

    @field_validator("expires_at")
    @classmethod
    def validate_expiry(
        cls,
        value: datetime,
        info: object,
    ) -> datetime:
        """Ensure expiry does not precede request time."""
        data = getattr(info, "data", {})
        requested_at = data.get("requested_at")

        if requested_at is not None and value < requested_at:
            raise ValueError(
                "expires_at cannot be earlier than requested_at"
            )

        return value

    @field_validator("operation")
    @classmethod
    def normalize_operation(cls, value: str) -> str:
        """Normalize operation identifiers at the execution boundary."""
        normalized = value.strip().upper()

        if not normalized:
            raise ValueError("operation must not be empty")

        return normalized


class ExecutionPlan(BaseModel):
    """Immutable plan describing bounded execution behavior."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    execution_id: str = Field(
        min_length=1,
        max_length=500,
    )
    execution_target: ExecutionTarget

    command_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )

    input_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )

    output_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )

    resource_limits: ResourceLimits

    network_access_allowed: bool = False
    external_side_effects_allowed: bool = False

    checkpoint_required: bool = False


class ExecutionResult(BaseModel):
    """Immutable result emitted after secure execution."""

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

    status: ExecutionStatus

    started_at: datetime
    completed_at: datetime | None = None

    exit_code: int | None = None

    output_ref: str | None = Field(
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

    checkpoint_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
    )

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        """Require timezone-aware execution result timestamps."""
        if value is None:
            return None

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "execution result timestamps must be timezone-aware"
            )

        return value

    @field_validator("completed_at")
    @classmethod
    def validate_completion_time(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        """Ensure completion cannot precede execution start."""
        if value is None:
            return None

        data = getattr(info, "data", {})
        started_at = data.get("started_at")

        if started_at is not None and value < started_at:
            raise ValueError(
                "completed_at cannot be earlier than started_at"
            )

        return value

    @model_validator(mode="after")
    def validate_status_consistency(self) -> ExecutionResult:
        """Require failed executions to carry error information."""
        if self.status is ExecutionStatus.FAILED:
            if self.error_code is None and self.error_message is None:
                raise ValueError(
                    "failed execution requires error information"
                )

        return self


class ExecutionAdmissionEnvelope(BaseModel):
    """Execution boundary envelope produced from a gateway admission."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    execution_request: ExecutionRequest

    admitted_at: datetime

    @field_validator("admitted_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime,
    ) -> datetime:
        """Require a timezone-aware admission timestamp."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "admitted_at must be timezone-aware"
            )

        return value.astimezone(UTC)
