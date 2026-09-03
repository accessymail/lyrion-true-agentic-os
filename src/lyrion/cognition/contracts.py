"""Contracts for Lyrion's provider-neutral Cognitive Runtime."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lyrion.core.types import AutonomyLevel, RiskLevel


class CognitiveRequestStatus(StrEnum):
    """Lifecycle status of a cognitive request result."""

    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


class CognitiveBudget(BaseModel):
    """Explicit resource limits for one cognitive request."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    max_model_calls: int = Field(default=1, ge=1)
    max_tool_calls: int = Field(default=0, ge=0)
    max_runtime_seconds: float = Field(default=30.0, gt=0.0)
    max_cost_units: float = Field(default=0.0, ge=0.0)
    max_parallelism: int = Field(default=1, ge=1)


class CognitiveConstraints(BaseModel):
    """Non-authorizing constraints governing cognitive processing."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    autonomy_level: AutonomyLevel = AutonomyLevel.L0
    max_risk_level: RiskLevel = RiskLevel.LOW
    allow_tool_use: bool = False
    allow_external_side_effects: bool = False
    require_verification: bool = True


class ReasonRequest(BaseModel):
    """Immutable provider-neutral request for substantive reasoning."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    request_id: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=8000)

    context_refs: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)

    constraints: CognitiveConstraints = Field(
        default_factory=CognitiveConstraints,
    )

    budget: CognitiveBudget = Field(
        default_factory=CognitiveBudget,
    )

    risk_class: RiskLevel = RiskLevel.LOW

    required_capabilities: tuple[str, ...] = Field(
        default_factory=tuple,
    )

    verification_requirements: tuple[str, ...] = Field(
        default_factory=tuple,
    )

    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime,
    ) -> datetime:
        """Require a timezone-aware request timestamp."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "cognitive request timestamp must be timezone-aware",
            )

        return value


class CognitiveResult(BaseModel):
    """Immutable result returned by the Cognitive Runtime."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    request_id: str = Field(min_length=1, max_length=200)
    status: CognitiveRequestStatus

    answer: str | None = Field(
        default=None,
        max_length=12000,
    )

    proposed_plan: tuple[str, ...] = Field(
        default_factory=tuple,
    )

    uncertainty: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    evidence_refs: tuple[str, ...] = Field(
        default_factory=tuple,
    )

    provider: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    model: str | None = Field(
        default=None,
        min_length=1,
        max_length=300,
    )

    verification_required: bool = True

    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime,
    ) -> datetime:
        """Require a timezone-aware result timestamp."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "cognitive result timestamp must be timezone-aware",
            )

        return value

    def normalized_created_at(self) -> datetime:
        """Return the result timestamp normalized to UTC."""
        return self.created_at.astimezone(UTC)
