"""Provider-neutral contracts for voice evaluation."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from math import isfinite

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class VoiceEvaluationStatus(StrEnum):
    """Normalized outcome of one voice evaluation."""

    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    DEGRADED = "DEGRADED"
    INCONCLUSIVE = "INCONCLUSIVE"
    ERROR = "ERROR"


class VoiceEvaluationMetricKind(StrEnum):
    """Provider-neutral categories of voice evaluation metrics."""

    LATENCY = "LATENCY"
    RELIABILITY = "RELIABILITY"
    STREAMING = "STREAMING"
    INTERRUPTION = "INTERRUPTION"
    CONTINUITY = "CONTINUITY"
    ASR_QUALITY = "ASR_QUALITY"
    RESPONSE_QUALITY = "RESPONSE_QUALITY"
    TTS_QUALITY = "TTS_QUALITY"
    SAFETY = "SAFETY"
    SECURITY = "SECURITY"
    PROVIDER_INTEGRITY = "PROVIDER_INTEGRITY"


class VoiceEvaluationEvidence(BaseModel):
    """Immutable, bounded evidence reference used by an evaluator.

    Evidence is observational input only. It never grants authentication,
    authorization, capability permissions, or execution authority.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str = Field(min_length=1, max_length=500)
    session_id: str = Field(min_length=1, max_length=200)
    turn_id: str | None = Field(default=None, min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=200)
    event_type: str = Field(min_length=1, max_length=200)
    reference: str | None = Field(default=None, min_length=1, max_length=500)
    provider_id: str | None = Field(default=None, min_length=1, max_length=200)
    provenance: str = Field(min_length=1, max_length=500)
    data_classification: str = Field(min_length=1, max_length=100)
    observed_at: datetime

    @field_validator(
        "evidence_id",
        "session_id",
        "turn_id",
        "source",
        "event_type",
        "reference",
        "provider_id",
        "provenance",
        "data_classification",
    )
    @classmethod
    def require_non_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("evidence fields must not be blank")
        return value

    @field_validator("observed_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value.astimezone(UTC)


class VoiceEvaluationMetric(BaseModel):
    """Immutable result for one evaluation metric."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metric_id: str = Field(min_length=1, max_length=200)
    kind: VoiceEvaluationMetricKind
    value: float = Field(ge=0.0, le=1.0)
    passed: bool
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_ids: tuple[str, ...] = ()
    detail: str | None = Field(default=None, max_length=2000)

    @field_validator("metric_id")
    @classmethod
    def require_metric_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("metric_id must not be blank")
        return value

    @field_validator("evidence_ids")
    @classmethod
    def validate_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not evidence_id.strip() for evidence_id in value):
            raise ValueError("evidence IDs must not be blank")
        if len(set(value)) != len(value):
            raise ValueError("evidence IDs must be unique")
        return value

    @field_validator("detail")
    @classmethod
    def validate_detail(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("detail must not be blank when supplied")
        return value

    @field_validator("value", "threshold")
    @classmethod
    def require_finite(cls, value: float | None) -> float | None:
        if value is not None and not isfinite(value):
            raise ValueError("metric values must be finite")
        return value


class VoiceEvaluationFinding(BaseModel):
    """Immutable structured evaluation finding."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    finding_id: str = Field(min_length=1, max_length=200)
    severity: int = Field(ge=0, le=4)
    category: VoiceEvaluationMetricKind
    message: str = Field(min_length=1, max_length=4000)
    evidence_ids: tuple[str, ...] = ()

    @field_validator("finding_id", "message")
    @classmethod
    def require_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("finding fields must not be blank")
        return value

    @field_validator("evidence_ids")
    @classmethod
    def validate_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not evidence_id.strip() for evidence_id in value):
            raise ValueError("evidence IDs must not be blank")
        if len(set(value)) != len(value):
            raise ValueError("evidence IDs must be unique")
        return value


class VoiceEvaluationResult(BaseModel):
    """Immutable aggregate voice evaluation result.

    Evaluation is observational. This result cannot authorize, authenticate,
    grant capabilities, or trigger execution.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    evaluation_id: str = Field(min_length=1, max_length=200)
    session_id: str = Field(min_length=1, max_length=200)
    turn_id: str | None = Field(default=None, min_length=1, max_length=200)
    evaluator_id: str = Field(min_length=1, max_length=200)
    evaluator_version: str = Field(min_length=1, max_length=100)
    status: VoiceEvaluationStatus
    overall_score: float | None = Field(default=None, ge=0.0, le=1.0)
    metrics: tuple[VoiceEvaluationMetric, ...] = ()
    findings: tuple[VoiceEvaluationFinding, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    evaluated_at: datetime
    provenance: str = Field(min_length=1, max_length=500)

    @field_validator(
        "evaluation_id",
        "session_id",
        "turn_id",
        "evaluator_id",
        "evaluator_version",
        "provenance",
    )
    @classmethod
    def require_non_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("evaluation fields must not be blank")
        return value

    @field_validator("overall_score")
    @classmethod
    def require_finite_score(cls, value: float | None) -> float | None:
        if value is not None and not isfinite(value):
            raise ValueError("overall_score must be finite")
        return value

    @field_validator("evidence_ids")
    @classmethod
    def validate_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not evidence_id.strip() for evidence_id in value):
            raise ValueError("evidence IDs must not be blank")
        if len(set(value)) != len(value):
            raise ValueError("evidence IDs must be unique")
        return value

    @field_validator("evaluated_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluated_at must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_result_invariants(self) -> VoiceEvaluationResult:
        metric_ids = [metric.metric_id for metric in self.metrics]
        if len(metric_ids) != len(set(metric_ids)):
            raise ValueError("metric IDs must be unique")

        finding_ids = [finding.finding_id for finding in self.findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("finding IDs must be unique")

        critical_security_failure = any(
            finding.category is VoiceEvaluationMetricKind.SECURITY
            and finding.severity >= 4
            for finding in self.findings
        )

        if (
            critical_security_failure
            and self.status is not VoiceEvaluationStatus.FAILED
        ):
            raise ValueError(
                "critical security findings require a FAILED evaluation result"
            )

        return self


class VoiceEvaluationScenario(BaseModel):
    """Immutable definition of a reproducible voice evaluation scenario."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scenario_id: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=2000)
    expected_properties: tuple[str, ...] = ()
    prohibited_properties: tuple[str, ...] = ()
    metric_kinds: tuple[VoiceEvaluationMetricKind, ...] = ()
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    provenance: str = Field(min_length=1, max_length=500)

    @field_validator(
        "scenario_id",
        "version",
        "description",
        "provenance",
    )
    @classmethod
    def require_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("scenario fields must not be blank")
        return value

    @field_validator("expected_properties", "prohibited_properties")
    @classmethod
    def validate_properties(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        if any(not item.strip() for item in value):
            raise ValueError("scenario properties must not be blank")
        if len(set(value)) != len(value):
            raise ValueError("scenario properties must be unique")
        return value

    @model_validator(mode="after")
    def validate_scenario(self) -> VoiceEvaluationScenario:
        if (
            not self.metric_kinds
            and self.threshold is not None
        ):
            raise ValueError(
                "threshold requires at least one evaluation metric kind"
            )
        return self


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""

    return datetime.now(UTC)
