from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lyrion.voice.evaluation.contracts import (
    VoiceEvaluationEvidence,
    VoiceEvaluationMetric,
    VoiceEvaluationMetricKind,
    VoiceEvaluationResult,
    VoiceEvaluationStatus,
)
from lyrion.voice.evaluation.service import VoiceEvaluationService
from lyrion.voice.streaming.contracts import VoiceStreamMetrics

NOW = datetime(2026, 9, 4, 11, 30, tzinfo=UTC)


def make_metrics(**overrides: object) -> VoiceStreamMetrics:
    values: dict[str, object] = {
        "session_id": "session-1",
        "input_chunks": 10,
        "output_chunks": 10,
        "turns_completed": 1,
        "provider_failures": 0,
        "cancellations": 0,
        "interruptions": 0,
        "duration_seconds": 2.0,
        "first_output_latency_seconds": 0.5,
    }
    values.update(overrides)
    return VoiceStreamMetrics.model_validate(values)


def make_evidence() -> tuple[VoiceEvaluationEvidence, ...]:
    return (
        VoiceEvaluationEvidence(
            evidence_id="evidence-1",
            session_id="session-1",
            turn_id="turn-1",
            source="voice-runtime",
            event_type="stream.completed",
            reference="opaque://stream-1",
            provider_id="provider-a",
            provenance="unit-test",
            data_classification="Internal",
            observed_at=NOW,
        ),
    )


def test_service_evaluates_with_default_evaluators() -> None:
    service = VoiceEvaluationService(clock=lambda: NOW)

    result = service.evaluate(
        metrics=make_metrics(),
        evidence=make_evidence(),
        evaluation_id="evaluation-1",
        turn_id="turn-1",
    )

    assert isinstance(result, VoiceEvaluationResult)
    assert result.evaluation_id == "evaluation-1"
    assert result.session_id == "session-1"
    assert result.turn_id == "turn-1"
    assert len(result.metrics) == 5
    assert result.evaluated_at == NOW
    assert result.status in {
        VoiceEvaluationStatus.PASSED,
        VoiceEvaluationStatus.DEGRADED,
    }


def test_service_generates_evaluation_id_when_missing() -> None:
    service = VoiceEvaluationService(clock=lambda: NOW)

    result = service.evaluate(metrics=make_metrics())

    assert result.evaluation_id
    assert result.evaluation_id != "None"


def test_service_rejects_blank_evaluation_id() -> None:
    service = VoiceEvaluationService(clock=lambda: NOW)

    with pytest.raises(ValueError, match="evaluation_id must not be blank"):
        service.evaluate(
            metrics=make_metrics(),
            evaluation_id="   ",
        )


def test_service_propagates_evidence_ids() -> None:
    service = VoiceEvaluationService(clock=lambda: NOW)

    result = service.evaluate(
        metrics=make_metrics(),
        evidence=make_evidence(),
    )

    assert result.evidence_ids == ("evidence-1",)


def test_custom_clock_controls_evaluation_timestamp() -> None:
    service = VoiceEvaluationService(clock=lambda: NOW)

    result = service.evaluate(
        metrics=make_metrics(),
        evaluation_id="evaluation-1",
    )

    assert result.evaluated_at == NOW


def test_empty_evaluator_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="at least one evaluator must be configured"):
        VoiceEvaluationService(evaluators=())


def test_duplicate_evaluator_ids_are_rejected() -> None:
    from lyrion.voice.evaluation.evaluators import LatencyEvaluator

    first = LatencyEvaluator()
    second = LatencyEvaluator()

    with pytest.raises(ValueError, match="evaluator IDs must be unique"):
        VoiceEvaluationService(evaluators=(first, second))


class RaisingEvaluator:
    evaluator_id = "raising"

    def evaluate(
        self,
        *,
        metrics: VoiceStreamMetrics,
        evidence: tuple[VoiceEvaluationEvidence, ...] = (),
    ) -> VoiceEvaluationMetric:
        raise RuntimeError("intentional evaluator failure")


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


class FailingEvaluator:
    evaluator_id = "failing"

    def evaluate(
        self,
        *,
        metrics: VoiceStreamMetrics,
        evidence: tuple[VoiceEvaluationEvidence, ...] = (),
    ) -> VoiceEvaluationMetric:
        return VoiceEvaluationMetric(
            metric_id="failing",
            kind=VoiceEvaluationMetricKind.SECURITY,
            value=0.0,
            passed=False,
            evidence_ids=tuple(item.evidence_id for item in evidence),
        )


def test_partial_evaluator_failure_is_degraded() -> None:
    service = VoiceEvaluationService(
        evaluators=(PassingEvaluator(), RaisingEvaluator()),
        clock=lambda: NOW,
    )

    result = service.evaluate(metrics=make_metrics())

    assert result.status is VoiceEvaluationStatus.DEGRADED
    assert len(result.metrics) == 1
    assert len(result.findings) == 1


def test_all_evaluators_failing_produces_error() -> None:
    service = VoiceEvaluationService(
        evaluators=(RaisingEvaluator(),),
        clock=lambda: NOW,
    )

    result = service.evaluate(metrics=make_metrics())

    assert result.status is VoiceEvaluationStatus.ERROR
    assert result.overall_score is None
    assert not result.metrics
    assert len(result.findings) == 1


def test_failed_metric_remains_failed_when_another_evaluator_errors() -> None:
    service = VoiceEvaluationService(
        evaluators=(FailingEvaluator(), RaisingEvaluator()),
        clock=lambda: NOW,
    )

    result = service.evaluate(metrics=make_metrics())

    assert result.status is VoiceEvaluationStatus.FAILED
    assert len(result.metrics) == 1
    assert len(result.findings) == 1


def test_evaluator_error_does_not_create_authority_fields() -> None:
    service = VoiceEvaluationService(
        evaluators=(RaisingEvaluator(),),
        clock=lambda: NOW,
    )

    result = service.evaluate(metrics=make_metrics())

    payload = result.model_dump()

    assert "authorized" not in payload
    assert "authorization" not in payload
    assert "execution" not in payload
    assert "capability" not in payload


def test_result_is_immutable() -> None:
    service = VoiceEvaluationService(clock=lambda: NOW)

    result = service.evaluate(metrics=make_metrics())

    with pytest.raises(ValidationError):
        result.status = VoiceEvaluationStatus.FAILED
