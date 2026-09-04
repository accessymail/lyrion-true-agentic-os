from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lyrion.voice.evaluation.contracts import (
    VoiceEvaluationEvidence,
    VoiceEvaluationFinding,
    VoiceEvaluationMetric,
    VoiceEvaluationMetricKind,
    VoiceEvaluationResult,
    VoiceEvaluationScenario,
    VoiceEvaluationStatus,
)

NOW = datetime(2026, 9, 4, 5, 30, tzinfo=UTC)


def make_evidence() -> VoiceEvaluationEvidence:
    return VoiceEvaluationEvidence(
        evidence_id="evidence-1",
        session_id="session-1",
        turn_id="turn-1",
        source="voice-runtime",
        event_type="turn.completed",
        reference="opaque://evidence-1",
        provider_id="provider-a",
        provenance="runtime-test",
        data_classification="Internal",
        observed_at=NOW,
    )


def make_metric() -> VoiceEvaluationMetric:
    return VoiceEvaluationMetric(
        metric_id="latency-1",
        kind=VoiceEvaluationMetricKind.LATENCY,
        value=0.9,
        passed=True,
        threshold=0.8,
        evidence_ids=("evidence-1",),
    )


def make_result(**overrides: object) -> VoiceEvaluationResult:
    values: dict[str, object] = {
        "evaluation_id": "evaluation-1",
        "session_id": "session-1",
        "turn_id": "turn-1",
        "evaluator_id": "deterministic",
        "evaluator_version": "1.0",
        "status": VoiceEvaluationStatus.PASSED,
        "overall_score": 0.9,
        "metrics": (make_metric(),),
        "evidence_ids": ("evidence-1",),
        "evaluated_at": NOW,
        "provenance": "unit-test",
    }
    values.update(overrides)
    return VoiceEvaluationResult.model_validate(values)


def test_evidence_is_immutable_and_provider_is_metadata() -> None:
    evidence = make_evidence()

    with pytest.raises(ValidationError):
        evidence.reference = "changed"

    assert evidence.provider_id == "provider-a"


def test_metric_accepts_normalized_value() -> None:
    metric = make_metric()

    assert metric.value == pytest.approx(0.9)
    assert metric.passed is True


def test_metric_rejects_out_of_range_value() -> None:
    with pytest.raises(ValidationError):
        VoiceEvaluationMetric(
            metric_id="metric-1",
            kind=VoiceEvaluationMetricKind.LATENCY,
            value=1.1,
            passed=True,
        )


def test_result_is_immutable() -> None:
    result = make_result()

    with pytest.raises(ValidationError):
        result.status = VoiceEvaluationStatus.FAILED


def test_result_rejects_duplicate_metric_ids() -> None:
    metric = make_metric()

    with pytest.raises(ValidationError, match="metric IDs must be unique"):
        make_result(metrics=(metric, metric))


def test_result_rejects_duplicate_finding_ids() -> None:
    finding = VoiceEvaluationFinding(
        finding_id="finding-1",
        severity=1,
        category=VoiceEvaluationMetricKind.RELIABILITY,
        message="degraded runtime behavior",
    )

    with pytest.raises(ValidationError, match="finding IDs must be unique"):
        make_result(findings=(finding, finding))


def test_critical_security_finding_forces_failed_result() -> None:
    finding = VoiceEvaluationFinding(
        finding_id="finding-security",
        severity=4,
        category=VoiceEvaluationMetricKind.SECURITY,
        message="critical security boundary failure",
    )

    with pytest.raises(
        ValidationError,
        match="critical security findings require a FAILED evaluation result",
    ):
        make_result(findings=(finding,))


def test_critical_security_finding_is_valid_when_result_failed() -> None:
    finding = VoiceEvaluationFinding(
        finding_id="finding-security",
        severity=4,
        category=VoiceEvaluationMetricKind.SECURITY,
        message="critical security boundary failure",
    )

    result = make_result(
        status=VoiceEvaluationStatus.FAILED,
        findings=(finding,),
    )

    assert result.status is VoiceEvaluationStatus.FAILED


def test_scenario_requires_metrics_for_threshold() -> None:
    with pytest.raises(
        ValidationError,
        match="threshold requires at least one evaluation metric kind",
    ):
        VoiceEvaluationScenario(
            scenario_id="scenario-1",
            version="1.0",
            description="threshold without metrics",
            threshold=0.8,
            provenance="unit-test",
        )


def test_scenario_accepts_metric_threshold() -> None:
    scenario = VoiceEvaluationScenario(
        scenario_id="scenario-1",
        version="1.0",
        description="normal voice turn",
        metric_kinds=(VoiceEvaluationMetricKind.LATENCY,),
        threshold=0.8,
        provenance="unit-test",
    )

    assert scenario.threshold == pytest.approx(0.8)


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        VoiceEvaluationEvidence.model_validate(
            {
                "evidence_id": "evidence-1",
                "session_id": "session-1",
                "source": "runtime",
                "event_type": "turn.completed",
                "provenance": "unit-test",
                "data_classification": "Internal",
                "observed_at": NOW,
                "unauthorized_field": "should-fail",
            }
        )


def test_naive_timestamp_is_rejected() -> None:
    with pytest.raises(
        ValidationError,
        match="observed_at must be timezone-aware",
    ):
        VoiceEvaluationEvidence(
            evidence_id="evidence-1",
            session_id="session-1",
            source="runtime",
            event_type="turn.completed",
            provenance="unit-test",
            data_classification="Internal",
            observed_at=datetime(2026, 9, 4, 5, 30),
        )
