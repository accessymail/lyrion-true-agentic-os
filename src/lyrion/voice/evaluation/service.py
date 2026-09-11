"""Orchestration service for provider-neutral voice evaluation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from lyrion.voice.evaluation.aggregation import VoiceEvaluationAggregator
from lyrion.voice.evaluation.contracts import (
    VoiceEvaluationEvidence,
    VoiceEvaluationFinding,
    VoiceEvaluationMetricKind,
    VoiceEvaluationResult,
    VoiceEvaluationStatus,
)
from lyrion.voice.evaluation.evaluators import (
    DEFAULT_VOICE_EVALUATORS,
    VoiceMetricEvaluator,
)
from lyrion.voice.streaming.contracts import VoiceStreamMetrics


class EvaluationClock(Protocol):
    """Clock boundary used by the evaluation service."""

    def __call__(self) -> datetime:
        """Return the current timezone-aware UTC time."""


def utc_now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(UTC)


class VoiceEvaluationService:
    """Controlled orchestration boundary for voice evaluation.

    Evaluation is observational only. This service does not authenticate,
    authorize capabilities, modify policy, or execute actions.
    """

    def __init__(
        self,
        *,
        evaluators: tuple[VoiceMetricEvaluator, ...] = DEFAULT_VOICE_EVALUATORS,
        aggregator: VoiceEvaluationAggregator | None = None,
        clock: EvaluationClock = utc_now,
    ) -> None:
        if not evaluators:
            raise ValueError("at least one evaluator must be configured")

        evaluator_ids = [evaluator.evaluator_id for evaluator in evaluators]
        if len(evaluator_ids) != len(set(evaluator_ids)):
            raise ValueError("evaluator IDs must be unique")

        self._evaluators = evaluators
        self._aggregator = aggregator or VoiceEvaluationAggregator()
        self._clock = clock

    def evaluate(
        self,
        *,
        metrics: VoiceStreamMetrics,
        evidence: tuple[VoiceEvaluationEvidence, ...] = (),
        evaluation_id: str | None = None,
        turn_id: str | None = None,
        evaluator_version: str = "1.0",
        provenance: str = "voice-runtime",
    ) -> VoiceEvaluationResult:
        """Evaluate one voice runtime metric snapshot."""

        now = self._clock().astimezone(UTC)
        evaluation_identifier = (evaluation_id or str(uuid4())).strip()

        if not evaluation_identifier:
            raise ValueError("evaluation_id must not be blank")

        all_evidence_ids = tuple(
            dict.fromkeys(item.evidence_id for item in evidence)
        )

        metric_results = []
        findings: list[VoiceEvaluationFinding] = []

        for evaluator in self._evaluators:
            try:
                metric_results.append(
                    evaluator.evaluate(
                        metrics=metrics,
                        evidence=evidence,
                    )
                )
            except Exception as exc:
                findings.append(
                    VoiceEvaluationFinding(
                        finding_id=f"evaluator-error-{evaluator.evaluator_id}",
                        severity=3,
                        category=VoiceEvaluationMetricKind.RELIABILITY,
                        message=(
                            f"Evaluator {evaluator.evaluator_id!r} failed closed: "
                            f"{type(exc).__name__}."
                        ),
                    )
                )

        if findings:
            if len(findings) == len(self._evaluators):
                return VoiceEvaluationResult(
                    evaluation_id=evaluation_identifier,
                    session_id=metrics.session_id,
                    turn_id=turn_id,
                    evaluator_id="voice-evaluation-service",
                    evaluator_version=evaluator_version,
                    status=VoiceEvaluationStatus.ERROR,
                    overall_score=None,
                    metrics=tuple(metric_results),
                    findings=tuple(findings),
                    evidence_ids=all_evidence_ids,
                    evaluated_at=now,
                    provenance=provenance,
                )

            result = self._aggregator.aggregate(
                evaluation_id=evaluation_identifier,
                session_id=metrics.session_id,
                turn_id=turn_id,
                evaluator_id="voice-evaluation-service",
                evaluator_version=evaluator_version,
                metrics=tuple(metric_results),
                findings=tuple(findings),
                evidence_ids=all_evidence_ids,
                evaluated_at=now,
                provenance=provenance,
            )

            return result.model_copy(
                update={"status": VoiceEvaluationStatus.DEGRADED}
                if result.status is VoiceEvaluationStatus.PASSED
                else {}
            )

        return self._aggregator.aggregate(
            evaluation_id=evaluation_identifier,
            session_id=metrics.session_id,
            turn_id=turn_id,
            evaluator_id="voice-evaluation-service",
            evaluator_version=evaluator_version,
            metrics=tuple(metric_results),
            findings=tuple(findings),
            evidence_ids=all_evidence_ids,
            evaluated_at=now,
            provenance=provenance,
        )
