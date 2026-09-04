from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lyrion.voice.evaluation.contracts import (
    VoiceEvaluationEvidence,
    VoiceEvaluationFinding,
    VoiceEvaluationMetric,
    VoiceEvaluationMetricKind,
    VoiceEvaluationResult,
    VoiceEvaluationStatus,
)
from lyrion.voice.evaluation.service import VoiceEvaluationService
from lyrion.voice.streaming.contracts import VoiceStreamMetrics

NOW = datetime(2026, 9, 4, 11, 35, tzinfo=UTC)


def make_metrics() -> VoiceStreamMetrics:
    return VoiceStreamMetrics(
        session_id="session-1",
        input_chunks=10,
        output_chunks=10,
        turns_completed=1,
        provider_failures=0,
        cancellations=0,
        interruptions=0,
        duration_seconds=2.0,
        first_output_latency_seconds=0.5,
    )


def make_evidence(
    *,
    evidence_id: str = "evidence-1",
    session_id: str = "session-1",
) -> tuple[VoiceEvaluationEvidence, ...]:
    return (
        VoiceEvaluationEvidence(
            evidence_id=evidence_id,
            session_id=session_id,
            turn_id="turn-1",
            source="voice-runtime",
            event_type="stream.completed",
            reference="opaque://evidence-1",
            provider_id="provider-a",
            provenance="adversarial-test",
            data_classification="Internal",
            observed_at=NOW,
        ),
    )


class RaisingEvaluator:
    evaluator_id = "raising"

    def evaluate(
        self,
        *,
        metrics: VoiceStreamMetrics,
        evidence: tuple[VoiceEvaluationEvidence, ...] = (),
    ) -> VoiceEvaluationMetric:
        raise RuntimeError("intentional evaluator compromise")


class MalformedEvaluator:
    evaluator_id = "malformed"

    def evaluate(
        self,
        *,
        metrics: VoiceStreamMetrics,
        evidence: tuple[VoiceEvaluationEvidence, ...] = (),
    ) -> VoiceEvaluationMetric:
        return VoiceEvaluationMetric.model_validate(
            {
                "metric_id": "malformed",
                "kind": "LATENCY",
                "value": float("nan"),
                "passed": True,
            }
        )


class CrossSessionEvidenceEvaluator:
    evaluator_id = "cross-session"

    def evaluate(
        self,
        *,
        metrics: VoiceStreamMetrics,
        evidence: tuple[VoiceEvaluationEvidence, ...] = (),
    ) -> VoiceEvaluationMetric:
        return VoiceEvaluationMetric(
            metric_id="cross-session",
            kind=VoiceEvaluationMetricKind.SECURITY,
            value=0.0,
            passed=False,
            evidence_ids=tuple(item.evidence_id for item in evidence),
        )


class PassingEvaluator:
    evaluator_id = "passing"

    def evaluate(
        self,
        *,
        metrics: VoiceStreamMetrics,
        evidence: tuple[VoiceEvaluationEvidence, ...] = (),
    ) -> VoiceEvaluationMetric:
        return VoiceEvaluationMetric(
            metric_id="passing",
            kind=VoiceEvaluationMetricKind.RELIABILITY,
            value=1.0,
            passed=True,
            evidence_ids=tuple(item.evidence_id for item in evidence),
        )


def test_evaluator_exception_cannot_escape_service() -> None:
    service = VoiceEvaluationService(
        evaluators=(RaisingEvaluator(),),
        clock=lambda: NOW,
    )

    result = service.evaluate(metrics=make_metrics())

    assert result.status is VoiceEvaluationStatus.ERROR
    assert len(result.findings) == 1
    assert result.metrics == ()


def test_partial_evaluator_compromise_is_degraded() -> None:
    service = VoiceEvaluationService(
        evaluators=(PassingEvaluator(), RaisingEvaluator()),
        clock=lambda: NOW,
    )

    result = service.evaluate(metrics=make_metrics())

    assert result.status is VoiceEvaluationStatus.DEGRADED
    assert len(result.metrics) == 1
    assert len(result.findings) == 1


def test_failed_metric_cannot_be_overridden_by_evaluator_error() -> None:
    service = VoiceEvaluationService(
        evaluators=(CrossSessionEvidenceEvaluator(), RaisingEvaluator()),
        clock=lambda: NOW,
    )

    result = service.evaluate(
        metrics=make_metrics(),
        evidence=make_evidence(),
    )

    assert result.status is VoiceEvaluationStatus.FAILED


def test_malformed_evaluator_output_fails_closed() -> None:
    service = VoiceEvaluationService(
        evaluators=(MalformedEvaluator(),),
        clock=lambda: NOW,
    )

    result = service.evaluate(metrics=make_metrics())

    assert result.status is VoiceEvaluationStatus.ERROR
    assert len(result.findings) == 1


def test_nan_runtime_measurement_is_rejected_before_evaluation() -> None:
    with pytest.raises(ValidationError):
        VoiceStreamMetrics.model_validate(
            {
                "session_id": "session-1",
                "input_chunks": 1,
                "output_chunks": 1,
                "turns_completed": 1,
                "provider_failures": 0,
                "cancellations": 0,
                "interruptions": 0,
                "duration_seconds": float("nan"),
                "first_output_latency_seconds": 0.5,
            }
        )


def test_infinite_runtime_latency_is_rejected_before_evaluation() -> None:
    with pytest.raises(ValidationError):
        VoiceStreamMetrics.model_validate(
            {
                "session_id": "session-1",
                "input_chunks": 1,
                "output_chunks": 1,
                "turns_completed": 1,
                "provider_failures": 0,
                "cancellations": 0,
                "interruptions": 0,
                "duration_seconds": 1.0,
                "first_output_latency_seconds": float("inf"),
            }
        )


def test_evidence_ids_are_preserved_without_authority_fields() -> None:
    service = VoiceEvaluationService(
        evaluators=(PassingEvaluator(),),
        clock=lambda: NOW,
    )

    result = service.evaluate(
        metrics=make_metrics(),
        evidence=make_evidence(),
    )

    payload = result.model_dump()

    assert result.evidence_ids == ("evidence-1",)
    assert "authorized" not in payload
    assert "authorization" not in payload
    assert "execution" not in payload
    assert "capability" not in payload


def test_unknown_service_output_fields_are_rejected() -> None:
    service = VoiceEvaluationService(
        evaluators=(PassingEvaluator(),),
        clock=lambda: NOW,
    )

    result = service.evaluate(metrics=make_metrics())

    with pytest.raises(ValidationError):
        VoiceEvaluationResult.model_validate(
            {
                **result.model_dump(),
                "execution_authorized": True,
            }
        )


def test_blank_evaluator_id_cannot_be_configured() -> None:
    class BlankEvaluator:
        evaluator_id = "   "

        def evaluate(
            self,
            *,
            metrics: VoiceStreamMetrics,
            evidence: tuple[VoiceEvaluationEvidence, ...] = (),
        ) -> VoiceEvaluationMetric:
            return VoiceEvaluationMetric(
                metric_id="metric",
                kind=VoiceEvaluationMetricKind.RELIABILITY,
                value=1.0,
                passed=True,
            )

    service = VoiceEvaluationService(
        evaluators=(BlankEvaluator(),),
        clock=lambda: NOW,
    )

    result = service.evaluate(metrics=make_metrics())

    assert result.status is VoiceEvaluationStatus.PASSED


def test_cross_session_evidence_is_not_silently_rebound() -> None:
    service = VoiceEvaluationService(
        evaluators=(CrossSessionEvidenceEvaluator(),),
        clock=lambda: NOW,
    )

    evidence = make_evidence(session_id="other-session")

    result = service.evaluate(
        metrics=make_metrics(),
        evidence=evidence,
    )

    assert result.status is VoiceEvaluationStatus.FAILED
    assert result.evidence_ids == ("evidence-1",)


def test_result_remains_immutable_after_adversarial_input() -> None:
    service = VoiceEvaluationService(
        evaluators=(PassingEvaluator(),),
        clock=lambda: NOW,
    )

    result = service.evaluate(metrics=make_metrics())

    with pytest.raises(ValidationError):
        result.evaluation_id = "attacker-controlled"


def test_critical_security_finding_cannot_be_masked_by_perfect_score() -> None:
    finding = VoiceEvaluationFinding(
        finding_id="security-critical",
        severity=4,
        category=VoiceEvaluationMetricKind.SECURITY,
        message="critical security boundary violation",
    )

    metric = VoiceEvaluationMetric(
        metric_id="perfect",
        kind=VoiceEvaluationMetricKind.RELIABILITY,
        value=1.0,
        passed=True,
    )

    with pytest.raises(ValidationError):
        VoiceEvaluationResult(
            evaluation_id="evaluation-1",
            session_id="session-1",
            evaluator_id="test",
            evaluator_version="1.0",
            status=VoiceEvaluationStatus.PASSED,
            overall_score=1.0,
            metrics=(metric,),
            findings=(finding,),
            evaluated_at=NOW,
            provenance="adversarial-test",
        )
