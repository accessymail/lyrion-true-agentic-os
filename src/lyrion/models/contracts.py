"""Provider-neutral contracts for Lyrion's Model Gateway."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lyrion.core.types import ExecutionTarget, RiskLevel


class ModelModality(StrEnum):
    """Supported model input/output modalities."""

    TEXT = "TEXT"
    AUDIO = "AUDIO"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    MULTIMODAL = "MULTIMODAL"


class ModelCapability(StrEnum):
    """High-level capabilities a model may provide."""

    GENERATION = "GENERATION"
    REASONING = "REASONING"
    PLANNING = "PLANNING"
    VISION = "VISION"
    AUDIO = "AUDIO"
    TOOL_USE = "TOOL_USE"


class ModelBudget(BaseModel):
    """Explicit resource limits for one model invocation."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    max_runtime_seconds: float = Field(
        default=30.0,
        gt=0.0,
    )
    max_cost_units: float = Field(
        default=0.0,
        ge=0.0,
    )
    max_output_tokens: int = Field(
        default=4096,
        ge=1,
    )


class ModelRequest(BaseModel):
    """Provider-neutral request submitted to the Model Gateway."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    request_id: str = Field(
        min_length=1,
        max_length=200,
    )

    objective: str = Field(
        min_length=1,
        max_length=12000,
    )

    context_refs: tuple[str, ...] = Field(
        default_factory=tuple,
    )

    evidence_refs: tuple[str, ...] = Field(
        default_factory=tuple,
    )

    required_capabilities: tuple[ModelCapability, ...] = Field(
        default_factory=tuple,
    )

    modality: ModelModality = ModelModality.TEXT

    reasoning_difficulty: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    risk_level: RiskLevel = RiskLevel.LOW

    privacy_required: bool = False
    network_required: bool = False

    budget: ModelBudget = Field(
        default_factory=ModelBudget,
    )

    preferred_targets: tuple[ExecutionTarget, ...] = Field(
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
                "model request timestamp must be timezone-aware",
            )

        return value


class ModelResponse(BaseModel):
    """Provider-neutral result returned by the Model Gateway."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    request_id: str = Field(
        min_length=1,
        max_length=200,
    )

    content: str = Field(
        min_length=1,
        max_length=20000,
    )

    provider: str = Field(
        min_length=1,
        max_length=200,
    )

    model: str = Field(
        min_length=1,
        max_length=300,
    )

    execution_target: ExecutionTarget

    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def require_timezone_aware(
        cls,
        value: datetime,
    ) -> datetime:
        """Require a timezone-aware response timestamp."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "model response timestamp must be timezone-aware",
            )

        return value
