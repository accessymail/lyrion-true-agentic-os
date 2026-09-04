from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lyrion.voice.evaluation.contracts import (
    VoiceEvaluationFinding,
    VoiceEvaluationMetric,
    VoiceEvaluationMetricKind,
    VoiceEvaluationResult,
    VoiceEvaluationStatus,
)

NOW = datetime(2026, 9, 4, 5, 30, tzinfo=UTC)


def make_result(**overrides: object) -> VoiceEvaluationResult:
    values: dict[str, object] = {
        "evaluation_id": "evaluation-1",
        "session_id": "session-1",
        "evaluator_id": "deterministic",
        "evaluator_version": "1.0",
        "status": VoiceEvaluationStatus.PASSED,
        "overall_score": 0.9,
        "evaluated_at": NOW,
        "provenance": "adversarial-test",
    }
    values.update(overrides)
    return VoiceEvaluationResult.model_validate(values)


def test_nan_metric_is_rejected() -> None:
    with pytest.raises(ValidationError):
        VoiceEvaluationMetric(
            metric_id="metric-1",
            kind=VoiceEvaluationMetricKind.LATENCY,
            value=float("nan"),
            passed=True,
        )


def test_positive_infinity_metric_is_rejected() -> None:
    with pytest.raises(ValidationError):
        VoiceEvaluationMetric(
            metric_id="metric-1",
            kind=VoiceEvaluationMetricKind.LATENCY,
            value=float("inf"),
            passed=True,
        )


def test_negative_infinity_metric_is_rejected() -> None:
    with pytest.raises(ValidationError):
        VoiceEvaluationMetric(
            metric_id="metric-1",
            kind=VoiceEvaluationMetricKind.LATENCY,
            value=float("-inf"),
            passed=True,
        )


def test_nan_overall_score_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_result(overall_score=float("nan"))


def test_duplicate_evidence_ids_are_rejected() -> None:
    with pytest.raises(ValidationError, match="evidence IDs must be unique"):
        VoiceEvaluationMetric(
            metric_id="metric-1",
            kind=VoiceEvaluationMetricKind.SECURITY,
            value=0.5,
            passed=False,
            evidence_ids=("evidence-1", "evidence-1"),
        )


def test_duplicate_finding_evidence_ids_are_rejected() -> None:
    with pytest.raises(ValidationError, match="evidence IDs must be unique"):
        VoiceEvaluationFinding(
            finding_id="finding-1",
            severity=2,
            category=VoiceEvaluationMetricKind.SECURITY,
            message="security observation",
            evidence_ids=("evidence-1", "evidence-1"),
        )


def test_critical_security_failure_cannot_be_hidden_by_high_score() -> None:
    finding = VoiceEvaluationFinding(
        finding_id="security-1",
        severity=4,
        category=VoiceEvaluationMetricKind.SECURITY,
        message="critical security failure",
    )

    with pytest.raises(
        ValidationError,
        match="critical security findings require a FAILED evaluation result",
    ):
        make_result(
            overall_score=1.0,
            status=VoiceEvaluationStatus.PASSED,
            findings=(finding,),
        )


def test_failed_result_can_report_zero_score() -> None:
    result = make_result(
        status=VoiceEvaluationStatus.FAILED,
        overall_score=0.0,
    )

    assert result.status is VoiceEvaluationStatus.FAILED
    assert result.overall_score == pytest.approx(0.0)


def test_result_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        make_result(execution_authorized=True)
