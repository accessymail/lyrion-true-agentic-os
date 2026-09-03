"""Decision contracts for the Lyrion Proactive Intelligence and Autonomy Engine."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lyrion.core.types import (
    AutonomyLevel,
    CorrelationId,
    DecisionAction,
    DecisionId,
    EventId,
    IdempotencyKey,
    OpportunityId,
    RiskLevel,
    TaskId,
)
from lyrion.events.models import EventSensitivity, EventTrustLevel
from lyrion.state.models import StateRecord


class OpportunityStatus(StrEnum):
    """Lifecycle classification for a detected proactive opportunity."""

    OPEN = "OPEN"
    SUPPRESSED = "SUPPRESSED"
    EXPIRED = "EXPIRED"
    SELECTED = "SELECTED"
    DISMISSED = "DISMISSED"


class DecisionReason(StrEnum):
    """Structured reason codes supporting a PIAE decision."""

    USER_REQUEST = "USER_REQUEST"
    GOAL_ALIGNMENT = "GOAL_ALIGNMENT"
    TIME_SENSITIVITY = "TIME_SENSITIVITY"
    CONTEXT_RELEVANCE = "CONTEXT_RELEVANCE"
    RISK_REDUCTION = "RISK_REDUCTION"
    EFFICIENCY = "EFFICIENCY"
    SAFETY = "SAFETY"
    POLICY = "POLICY"
    INSUFFICIENT_CONFIDENCE = "INSUFFICIENT_CONFIDENCE"


class PolicyResult(StrEnum):
    """High-level result of policy evaluation."""

    NOT_EVALUATED = "NOT_EVALUATED"
    ALLOWED = "ALLOWED"
    DENIED = "DENIED"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"


class DecisionConstraints(BaseModel):
    """Bounds that a PIAE decision must respect."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    max_risk_level: RiskLevel = RiskLevel.LOW
    requires_human_approval: bool = False
    allow_external_side_effects: bool = False
    allow_network_access: bool = False
    max_cost_units: float = Field(default=0.0, ge=0.0)
    max_runtime_seconds: float = Field(default=30.0, gt=0.0)


class Opportunity(BaseModel):
    """A candidate situation that may justify proactive assistance."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    opportunity_id: OpportunityId
    correlation_id: CorrelationId | None = None

    trigger_event_ids: tuple[EventId, ...] = Field(min_length=1)
    relevant_state_ids: tuple[str, ...] = Field(default_factory=tuple)

    goal_context: tuple[str, ...] = Field(default_factory=tuple)

    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=4000)

    user_relevance: float = Field(ge=0.0, le=1.0)
    expected_benefit: float = Field(ge=0.0, le=1.0)
    interruption_cost: float = Field(ge=0.0, le=1.0)

    risk_score: float = Field(ge=0.0, le=1.0)
    reversibility: float = Field(ge=0.0, le=1.0)

    urgency: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)

    required_capabilities: tuple[str, ...] = Field(default_factory=tuple)
    required_autonomy_level: AutonomyLevel = AutonomyLevel.L0

    sensitivity: EventSensitivity = EventSensitivity.INTERNAL
    trust_level: EventTrustLevel = EventTrustLevel.UNTRUSTED

    status: OpportunityStatus = OpportunityStatus.OPEN

    created_at: datetime
    expires_at: datetime | None = None

    @field_validator("created_at", "expires_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        """Require timezone-aware opportunity timestamps."""
        if value is None:
            return None

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("opportunity timestamps must be timezone-aware")

        return value

    @field_validator("expires_at")
    @classmethod
    def validate_expiry(
        cls,
        value: datetime | None,
        info: object,
    ) -> datetime | None:
        """Ensure expiry is not earlier than creation time."""
        if value is None:
            return None

        data = getattr(info, "data", {})
        created_at = data.get("created_at")

        if created_at is not None and value < created_at:
            raise ValueError("expires_at cannot be earlier than created_at")

        return value

    @field_validator("trigger_event_ids")
    @classmethod
    def validate_trigger_event_ids(
        cls,
        value: tuple[EventId, ...],
    ) -> tuple[EventId, ...]:
        """Require unique triggering events."""
        if len(set(value)) != len(value):
            raise ValueError("trigger_event_ids must be unique")

        return value

    @field_validator("required_capabilities")
    @classmethod
    def validate_required_capabilities(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Require unique capability identifiers."""
        if len(set(value)) != len(value):
            raise ValueError("required_capabilities must be unique")

        return value

    def is_expired(self, now: datetime | None = None) -> bool:
        """Return whether the opportunity has expired."""
        current_time = now or datetime.now(UTC)

        if current_time.tzinfo is None or current_time.utcoffset() is None:
            raise ValueError("now must be timezone-aware")

        return self.expires_at is not None and current_time >= self.expires_at


class DecisionContext(BaseModel):
    """Bounded context available to PIAE when evaluating an opportunity."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    opportunity: Opportunity
    state_records: tuple[StateRecord, ...] = Field(default_factory=tuple)

    active_task_ids: tuple[TaskId, ...] = Field(default_factory=tuple)

    autonomy_level: AutonomyLevel
    constraints: DecisionConstraints

    now: datetime

    @field_validator("now")
    @classmethod
    def require_timezone_aware_now(cls, value: datetime) -> datetime:
        """Require timezone-aware decision time."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("decision time must be timezone-aware")

        return value


class DecisionCandidate(BaseModel):
    """A proposed action considered by PIAE."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    action: DecisionAction

    rationale: DecisionReason
    explanation: str = Field(min_length=1, max_length=4000)

    confidence: float = Field(ge=0.0, le=1.0)
    estimated_risk: RiskLevel

    estimated_cost_units: float = Field(default=0.0, ge=0.0)
    estimated_runtime_seconds: float = Field(default=0.0, ge=0.0)

    requires_human_approval: bool = False
    has_external_side_effect: bool = False
    requires_network_access: bool = False


class DecisionResult(BaseModel):
    """Immutable output of a PIAE evaluation."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    decision_id: DecisionId

    input_context_ref: str = Field(min_length=1, max_length=500)
    opportunity_ref: OpportunityId

    selected_action: DecisionAction
    alternative_actions: tuple[DecisionAction, ...] = Field(
        default_factory=tuple,
    )

    utility_estimate: float = Field(ge=0.0, le=1.0)
    interruption_cost: float = Field(ge=0.0, le=1.0)
    risk_estimate: float = Field(ge=0.0, le=1.0)

    autonomy_level: AutonomyLevel

    authorization_result: PolicyResult
    policy_result: PolicyResult

    confidence: float = Field(ge=0.0, le=1.0)

    reason_codes: tuple[DecisionReason, ...] = Field(min_length=1)

    authorization_required: bool
    authorization_granted: bool = False

    candidate_count: int = Field(ge=0)

    correlation_id: CorrelationId | None = None
    idempotency_key: IdempotencyKey | None = None

    expires_at: datetime | None = None
    decided_at: datetime

    @field_validator("decided_at", "expires_at")
    @classmethod
    def require_timezone_aware_timestamps(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        """Require timezone-aware decision timestamps."""
        if value is None:
            return None

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("decision timestamps must be timezone-aware")

        return value

    @field_validator("alternative_actions")
    @classmethod
    def validate_alternative_actions(
        cls,
        value: tuple[DecisionAction, ...],
    ) -> tuple[DecisionAction, ...]:
        """Ensure alternative actions are unique."""
        if len(set(value)) != len(value):
            raise ValueError("alternative_actions must be unique")

        return value

    @field_validator("reason_codes")
    @classmethod
    def validate_reason_codes(
        cls,
        value: tuple[DecisionReason, ...],
    ) -> tuple[DecisionReason, ...]:
        """Ensure decision reason codes are unique."""
        if len(set(value)) != len(value):
            raise ValueError("reason_codes must be unique")

        return value
