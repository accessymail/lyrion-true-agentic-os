from collections.abc import Iterable
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lyrion.voice.evaluation.aggregation import VoiceEvaluationAggregator
from lyrion.voice.evaluation.contracts import (
    VoiceEvaluationFinding,
    VoiceEvaluationMetric,
    VoiceEvaluationMetricKind,
    VoiceEvaluationResult,
    VoiceEvaluationStatus,
)

NOW = datetime(2026, 9, 4, 11, 27, tzinfo=UTC)


def make_metric(
    *,
    metric_id: str,
    kind: VoiceEvaluationMetricKind,
    value: float,
    passed: bool,
) -> VoiceEvaluationMetric:
    return VoiceEvaluationMetric(
        metric_id=metric_id,
        kind=kind,
        value=value,
        passed=passed,
    )


def make_finding(
    *,
    finding_id: str,
    severity: int,
    category: VoiceEvaluationMetricKind,
) -> VoiceEvaluationFinding:
    return VoiceEvaluationFinding(
        finding_id=finding_id,
        severity=severity,
        category=category,
        message=f"finding-{finding_id}",
    )


def aggregate(
    *,
    metrics: Iterable[VoiceEvaluationMetric] = (),
    findings: Iterable[VoiceEvaluationFinding] = (),
) -> VoiceEvaluationResult:
    return VoiceEvaluationAggregator().aggregate(
        evaluation_id="evaluation-1",
        session_id="session-1",
        turn_id="turn-1",
        evaluator_id="deterministic",
        evaluator_version="1.0",
        metrics=metrics,
        findings=findings,
        evidence_ids=("evidence-1",),
        evaluated_at=NOW,
        provenance="unit-test",
    )


def test_no_metrics_is_inconclusive() -> None:
    result = aggregate()

    assert result.status is VoiceEvaluationStatus.INCONCLUSIVE
    assert result.overall_score is None


def test_all_passing_metrics_produce_passed() -> None:
    result = aggregate(
        metrics=(
            make_metric(
                metric_id="latency",
                kind=VoiceEvaluationMetricKind.LATENCY,
                value=1.0,
                passed=True,
            ),
            make_metric(
                metric_id="reliability",
                kind=VoiceEvaluationMetricKind.RELIABILITY,
                value=1.0,
                passed=True,
            ),
        ),
    )

    assert result.status is VoiceEvaluationStatus.PASSED
    assert result.overall_score == pytest.approx(1.0)


def test_partial_score_without_failed_metric_is_degraded() -> None:
    result = aggregate(
        metrics=(
            make_metric(
                metric_id="latency",
                kind=VoiceEvaluationMetricKind.LATENCY,
                value=0.8,
                passed=True,
            ),
            make_metric(
                metric_id="reliability",
                kind=VoiceEvaluationMetricKind.RELIABILITY,
                value=1.0,
                passed=True,
            ),
        ),
    )

    assert result.status is VoiceEvaluationStatus.DEGRADED
    assert result.overall_score == pytest.approx(0.9)


def test_failed_metric_produces_failed() -> None:
    result = aggregate(
        metrics=(
            make_metric(
                metric_id="latency",
                kind=VoiceEvaluationMetricKind.LATENCY,
                value=0.4,
                passed=False,
            ),
            make_metric(
                metric_id="reliability",
                kind=VoiceEvaluationMetricKind.RELIABILITY,
                value=1.0,
                passed=True,
            ),
        ),
    )

    assert result.status is VoiceEvaluationStatus.FAILED


def test_critical_security_finding_produces_failed() -> None:
    result = aggregate(
        metrics=(
            make_metric(
                metric_id="latency",
                kind=VoiceEvaluationMetricKind.LATENCY,
                value=1.0,
                passed=True,
            ),
        ),
        findings=(
            make_finding(
                finding_id="security-1",
                severity=4,
                category=VoiceEvaluationMetricKind.SECURITY,
            ),
        ),
    )

    assert result.status is VoiceEvaluationStatus.FAILED


def test_critical_security_failure_overrides_perfect_score() -> None:
    result = aggregate(
        metrics=(
            make_metric(
                metric_id="latency",
                kind=VoiceEvaluationMetricKind.LATENCY,
                value=1.0,
                passed=True,
            ),
            make_metric(
                metric_id="streaming",
                kind=VoiceEvaluationMetricKind.STREAMING,
                value=1.0,
                passed=True,
            ),
        ),
        findings=(
            make_finding(
                finding_id="security-1",
                severity=4,
                category=VoiceEvaluationMetricKind.SECURITY,
            ),
        ),
    )

    assert result.overall_score == pytest.approx(1.0)
    assert result.status is VoiceEvaluationStatus.FAILED


def test_non_security_critical_finding_does_not_trigger_security_override() -> None:
    result = aggregate(
        metrics=(
            make_metric(
                metric_id="latency",
                kind=VoiceEvaluationMetricKind.LATENCY,
                value=1.0,
                passed=True,
            ),
        ),
        findings=(
            make_finding(
                finding_id="reliability-1",
                severity=4,
                category=VoiceEvaluationMetricKind.RELIABILITY,
            ),
        ),
    )

    assert result.status is VoiceEvaluationStatus.PASSED


def test_metrics_are_preserved() -> None:
    metric = make_metric(
        metric_id="latency",
        kind=VoiceEvaluationMetricKind.LATENCY,
        value=0.75,
        passed=True,
    )

    result = aggregate(metrics=(metric,))

    assert result.metrics == (metric,)


def test_findings_are_preserved() -> None:
    finding = make_finding(
        finding_id="finding-1",
        severity=2,
        category=VoiceEvaluationMetricKind.SAFETY,
    )

    result = aggregate(findings=(finding,))

    assert result.findings == (finding,)


def test_evidence_ids_are_deduplicated() -> None:
    result = VoiceEvaluationAggregator().aggregate(
        evaluation_id="evaluation-1",
        session_id="session-1",
        turn_id=None,
        evaluator_id="deterministic",
        evaluator_version="1.0",
        metrics=(
            make_metric(
                metric_id="latency",
                kind=VoiceEvaluationMetricKind.LATENCY,
                value=1.0,
                passed=True,
            ),
        ),
        evidence_ids=("evidence-1", "evidence-1"),
        evaluated_at=NOW,
        provenance="unit-test",
    )

    assert result.evidence_ids == ("evidence-1",)


def test_duplicate_metric_ids_are_rejected() -> None:
    metric = make_metric(
        metric_id="duplicate",
        kind=VoiceEvaluationMetricKind.LATENCY,
        value=1.0,
        passed=True,
    )

    with pytest.raises(ValidationError, match="metric IDs must be unique"):
        aggregate(metrics=(metric, metric))


def test_duplicate_finding_ids_are_rejected() -> None:
    finding = make_finding(
        finding_id="duplicate",
        severity=1,
        category=VoiceEvaluationMetricKind.SAFETY,
    )

    with pytest.raises(ValidationError, match="finding IDs must be unique"):
        aggregate(findings=(finding, finding))
