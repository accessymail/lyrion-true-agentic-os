"""Deterministic provider-neutral voice evaluation metrics."""

from __future__ import annotations

from math import isfinite
from typing import Protocol

from lyrion.voice.evaluation.contracts import (
    VoiceEvaluationEvidence,
    VoiceEvaluationMetric,
    VoiceEvaluationMetricKind,
)
from lyrion.voice.streaming.contracts import VoiceStreamMetrics


class VoiceMetricEvaluator(Protocol):
    """Protocol for one deterministic voice metric evaluator."""

    @property
    def evaluator_id(self) -> str:
        """Return the stable evaluator identifier."""

    def evaluate(
        self,
        *,
        metrics: VoiceStreamMetrics,
        evidence: tuple[VoiceEvaluationEvidence, ...] = (),
    ) -> VoiceEvaluationMetric:
        """Evaluate one runtime metric set."""


def _evidence_ids(
    evidence: tuple[VoiceEvaluationEvidence, ...],
) -> tuple[str, ...]:
    return tuple(item.evidence_id for item in evidence)


def _normalized_inverse(value: float, *, acceptable: float) -> float:
    """Convert a non-negative measurement to a bounded quality score."""
    if not isfinite(value) or value < 0:
        raise ValueError("measurement must be finite and non-negative")

    if acceptable <= 0 or not isfinite(acceptable):
        raise ValueError("acceptable threshold must be finite and greater than zero")

    return max(0.0, min(1.0, acceptable / max(value, acceptable)))


class LatencyEvaluator:
    """Evaluate first-output latency."""

    evaluator_id = "latency.first_output"

    def evaluate(
        self,
        *,
        metrics: VoiceStreamMetrics,
        evidence: tuple[VoiceEvaluationEvidence, ...] = (),
    ) -> VoiceEvaluationMetric:
        latency = metrics.first_output_latency_seconds

        if latency is None:
            return VoiceEvaluationMetric(
                metric_id=self.evaluator_id,
                kind=VoiceEvaluationMetricKind.LATENCY,
                value=0.0,
                passed=False,
                threshold=0.8,
                evidence_ids=_evidence_ids(evidence),
                detail="No first-output latency measurement was recorded.",
            )

        value = _normalized_inverse(latency, acceptable=1.0)

        return VoiceEvaluationMetric(
            metric_id=self.evaluator_id,
            kind=VoiceEvaluationMetricKind.LATENCY,
            value=value,
            passed=latency <= 1.0,
            threshold=0.8,
            evidence_ids=_evidence_ids(evidence),
            detail=f"first_output_latency_seconds={latency:.6f}",
        )


class ReliabilityEvaluator:
    """Evaluate provider/runtime failure behavior."""

    evaluator_id = "reliability.provider"

    def evaluate(
        self,
        *,
        metrics: VoiceStreamMetrics,
        evidence: tuple[VoiceEvaluationEvidence, ...] = (),
    ) -> VoiceEvaluationMetric:
        failures = metrics.provider_failures
        turns = metrics.turns_completed

        if failures == 0:
            value = 1.0
        elif turns == 0:
            value = 0.0
        else:
            value = max(0.0, 1.0 - (failures / (turns + failures)))

        return VoiceEvaluationMetric(
            metric_id=self.evaluator_id,
            kind=VoiceEvaluationMetricKind.RELIABILITY,
            value=value,
            passed=failures == 0,
            threshold=0.8,
            evidence_ids=_evidence_ids(evidence),
            detail=(
                f"provider_failures={failures}, "
                f"turns_completed={turns}"
            ),
        )


class StreamingEvaluator:
    """Evaluate whether a streaming session produced usable output."""

    evaluator_id = "streaming.integrity"

    def evaluate(
        self,
        *,
        metrics: VoiceStreamMetrics,
        evidence: tuple[VoiceEvaluationEvidence, ...] = (),
    ) -> VoiceEvaluationMetric:
        inputs = metrics.input_chunks
        outputs = metrics.output_chunks

        if inputs == 0:
            value = 0.0
        elif outputs == 0:
            value = 0.0
        else:
            value = min(1.0, outputs / inputs)

        return VoiceEvaluationMetric(
            metric_id=self.evaluator_id,
            kind=VoiceEvaluationMetricKind.STREAMING,
            value=value,
            passed=outputs > 0,
            threshold=0.8,
            evidence_ids=_evidence_ids(evidence),
            detail=f"input_chunks={inputs}, output_chunks={outputs}",
        )


class InterruptionEvaluator:
    """Evaluate interruption behavior from normalized runtime metrics."""

    evaluator_id = "interruption.runtime"

    def evaluate(
        self,
        *,
        metrics: VoiceStreamMetrics,
        evidence: tuple[VoiceEvaluationEvidence, ...] = (),
    ) -> VoiceEvaluationMetric:
        interruptions = metrics.interruptions
        cancellations = metrics.cancellations

        if interruptions == 0:
            value = 1.0
        elif cancellations >= interruptions:
            value = 1.0
        else:
            value = cancellations / interruptions

        return VoiceEvaluationMetric(
            metric_id=self.evaluator_id,
            kind=VoiceEvaluationMetricKind.INTERRUPTION,
            value=value,
            passed=value >= 0.8,
            threshold=0.8,
            evidence_ids=_evidence_ids(evidence),
            detail=(
                f"interruptions={interruptions}, "
                f"cancellations={cancellations}"
            ),
        )


class ContinuityEvaluator:
    """Evaluate basic turn continuity from stream metrics."""

    evaluator_id = "continuity.turns"

    def evaluate(
        self,
        *,
        metrics: VoiceStreamMetrics,
        evidence: tuple[VoiceEvaluationEvidence, ...] = (),
    ) -> VoiceEvaluationMetric:
        completed = metrics.turns_completed

        value = 1.0 if completed > 0 else 0.0

        return VoiceEvaluationMetric(
            metric_id=self.evaluator_id,
            kind=VoiceEvaluationMetricKind.CONTINUITY,
            value=value,
            passed=completed > 0,
            threshold=0.8,
            evidence_ids=_evidence_ids(evidence),
            detail=f"turns_completed={completed}",
        )


DEFAULT_VOICE_EVALUATORS: tuple[VoiceMetricEvaluator, ...] = (
    LatencyEvaluator(),
    ReliabilityEvaluator(),
    StreamingEvaluator(),
    InterruptionEvaluator(),
    ContinuityEvaluator(),
)
