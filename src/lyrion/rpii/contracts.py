"""Provider-neutral contracts for Lyrion Real Proactive Interactive Intelligence."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from lyrion.capabilities.contracts import CapabilityRequest
from lyrion.capabilities.gateway import ExecutionAdmission
from lyrion.execution.contracts import ExecutionPlan, ExecutionResult
from lyrion.execution.sandbox import SandboxConfig
from lyrion.piae.contracts import DecisionContext, DecisionResult


class RPIIStage(StrEnum):
    """Lifecycle stages of one bounded RPII interaction."""

    INTERACTION = "INTERACTION"
    COGNITION = "COGNITION"
    DECISION = "DECISION"
    AUTHORIZATION = "AUTHORIZATION"
    EXECUTION = "EXECUTION"
    VERIFICATION = "VERIFICATION"
    FEEDBACK = "FEEDBACK"
    EVALUATION = "EVALUATION"


class RPIIStatus(StrEnum):
    """Terminal status of one bounded RPII cycle."""

    COMPLETED = "COMPLETED"
    WAITING = "WAITING"
    DENIED = "DENIED"
    FAILED = "FAILED"
    DEGRADED = "DEGRADED"


class RPIIContext(BaseModel):
    """Immutable bounded context entering an RPII cycle."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    interaction_id: str = Field(min_length=1, max_length=200)
    session_id: str = Field(min_length=1, max_length=200)
    decision_context: DecisionContext
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def require_timezone_aware_created_at(cls, value: datetime) -> datetime:
        """Require timezone-aware RPII context timestamps."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value


class RPIICycleResult(BaseModel):
    """Immutable result of one bounded RPII cycle.

    This contract composes existing authority boundaries. It does not grant
    authorization, create capability permissions, or directly execute work.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    interaction_id: str = Field(min_length=1, max_length=200)
    session_id: str = Field(min_length=1, max_length=200)
    status: RPIIStatus
    stage: RPIIStage
    decision: DecisionResult

    capability_request: CapabilityRequest | None = None
    admission: ExecutionAdmission | None = None
    execution_plan: ExecutionPlan | None = None
    sandbox: SandboxConfig | None = None
    execution_result: ExecutionResult | None = None

    started_at: datetime
    completed_at: datetime | None = None

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_timezone_aware_timestamps(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        """Require timezone-aware RPII lifecycle timestamps."""
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("RPII lifecycle timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_completion_order(self) -> RPIICycleResult:
        """Ensure completion cannot precede cycle start."""
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at cannot be earlier than started_at")
        return self
