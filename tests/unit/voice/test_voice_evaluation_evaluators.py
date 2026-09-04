from math import inf, nan

import pytest
from pydantic import ValidationError

from lyrion.voice.evaluation.contracts import (
    VoiceEvaluationEvidence,
    VoiceEvaluationMetricKind,
)
from lyrion.voice.evaluation.evaluators import (
    ContinuityEvaluator,
    InterruptionEvaluator,
    LatencyEvaluator,
    ReliabilityEvaluator,
    StreamingEvaluator,
)
from lyrion.voice.streaming.contracts import VoiceStreamMetrics


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
    from datetime import UTC, datetime

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
            observed_at=datetime(2026, 9, 4, 5, 30, tzinfo=UTC),
        ),
    )


def test_latency_evaluator_passes_fast_output() -> None:
    result = LatencyEvaluator().evaluate(
        metrics=make_metrics(first_output_latency_seconds=0.5),
        evidence=make_evidence(),
    )

    assert result.kind is VoiceEvaluationMetricKind.LATENCY
    assert result.value == pytest.approx(1.0)
    assert result.passed is True
    assert result.evidence_ids == ("evidence-1",)


def test_latency_evaluator_fails_when_measurement_missing() -> None:
    result = LatencyEvaluator().evaluate(
        metrics=make_metrics(first_output_latency_seconds=None),
    )

    assert result.value == 0.0
    assert result.passed is False


def test_latency_evaluator_degrades_as_latency_increases() -> None:
    fast = LatencyEvaluator().evaluate(
        metrics=make_metrics(first_output_latency_seconds=0.5),
    )
    slow = LatencyEvaluator().evaluate(
        metrics=make_metrics(first_output_latency_seconds=2.0),
    )

    assert fast.value > slow.value
    assert slow.passed is False


def test_reliability_evaluator_passes_without_failures() -> None:
    result = ReliabilityEvaluator().evaluate(
        metrics=make_metrics(provider_failures=0),
    )

    assert result.value == 1.0
    assert result.passed is True


def test_reliability_evaluator_fails_when_provider_fails() -> None:
    result = ReliabilityEvaluator().evaluate(
        metrics=make_metrics(provider_failures=1, turns_completed=1),
    )

    assert result.value == pytest.approx(0.5)
    assert result.passed is False


def test_streaming_evaluator_passes_with_output() -> None:
    result = StreamingEvaluator().evaluate(
        metrics=make_metrics(input_chunks=10, output_chunks=10),
    )

    assert result.value == 1.0
    assert result.passed is True


def test_streaming_evaluator_fails_without_output() -> None:
    result = StreamingEvaluator().evaluate(
        metrics=make_metrics(input_chunks=10, output_chunks=0),
    )

    assert result.value == 0.0
    assert result.passed is False


def test_streaming_evaluator_caps_score_at_one() -> None:
    result = StreamingEvaluator().evaluate(
        metrics=make_metrics(input_chunks=2, output_chunks=10),
    )

    assert result.value == 1.0
    assert result.passed is True


def test_interruption_evaluator_passes_without_interruptions() -> None:
    result = InterruptionEvaluator().evaluate(
        metrics=make_metrics(interruptions=0, cancellations=0),
    )

    assert result.value == 1.0
    assert result.passed is True


def test_interruption_evaluator_passes_when_interruptions_are_cancelled() -> None:
    result = InterruptionEvaluator().evaluate(
        metrics=make_metrics(interruptions=3, cancellations=3),
    )

    assert result.value == 1.0
    assert result.passed is True


def test_interruption_evaluator_fails_when_cancellations_lag() -> None:
    result = InterruptionEvaluator().evaluate(
        metrics=make_metrics(interruptions=4, cancellations=2),
    )

    assert result.value == pytest.approx(0.5)
    assert result.passed is False


def test_continuity_evaluator_passes_when_turn_completed() -> None:
    result = ContinuityEvaluator().evaluate(
        metrics=make_metrics(turns_completed=1),
    )

    assert result.value == 1.0
    assert result.passed is True


def test_continuity_evaluator_fails_without_completed_turn() -> None:
    result = ContinuityEvaluator().evaluate(
        metrics=make_metrics(turns_completed=0),
    )

    assert result.value == 0.0
    assert result.passed is False


def test_all_evaluators_propagate_evidence_ids() -> None:
    evidence = make_evidence()

    evaluators = (
        LatencyEvaluator(),
        ReliabilityEvaluator(),
        StreamingEvaluator(),
        InterruptionEvaluator(),
        ContinuityEvaluator(),
    )

    for evaluator in evaluators:
        result = evaluator.evaluate(
            metrics=make_metrics(),
            evidence=evidence,
        )
        assert result.evidence_ids == ("evidence-1",)


def test_negative_metric_input_cannot_exist() -> None:
    with pytest.raises(ValidationError):
        make_metrics(duration_seconds=-1.0)


def test_non_finite_metric_input_cannot_exist() -> None:
    with pytest.raises(ValidationError):
        make_metrics(duration_seconds=nan)

    with pytest.raises(ValidationError):
        make_metrics(first_output_latency_seconds=inf)
