"""Aggregate deterministic voice evaluation metrics into one result."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from lyrion.voice.evaluation.contracts import (
    VoiceEvaluationFinding,
    VoiceEvaluationMetric,
    VoiceEvaluationResult,
    VoiceEvaluationStatus,
)


class VoiceEvaluationAggregator:
    """Combine metric and finding results without granting authority."""

    def aggregate(
        self,
        *,
        evaluation_id: str,
        session_id: str,
        turn_id: str | None,
        evaluator_id: str,
        evaluator_version: str,
        metrics: Iterable[VoiceEvaluationMetric],
        findings: Iterable[VoiceEvaluationFinding] = (),
        evidence_ids: Iterable[str] = (),
        evaluated_at: datetime,
        provenance: str,
    ) -> VoiceEvaluationResult:
        metric_items = tuple(metrics)
        finding_items = tuple(findings)
        evidence_items = tuple(dict.fromkeys(evidence_ids))

        statuses = [metric.passed for metric in metric_items]

        if not metric_items:
            status = VoiceEvaluationStatus.INCONCLUSIVE
            overall_score = None
        else:
            overall_score = sum(metric.value for metric in metric_items) / len(
                metric_items
            )

            critical_security_failure = any(
                finding.severity >= 4
                and finding.category.value == "SECURITY"
                for finding in finding_items
            )

            if critical_security_failure:
                status = VoiceEvaluationStatus.FAILED
            elif not all(statuses):
                status = VoiceEvaluationStatus.FAILED
            elif any(metric.value < 1.0 for metric in metric_items):
                status = VoiceEvaluationStatus.DEGRADED
            else:
                status = VoiceEvaluationStatus.PASSED

        return VoiceEvaluationResult(
            evaluation_id=evaluation_id,
            session_id=session_id,
            turn_id=turn_id,
            evaluator_id=evaluator_id,
            evaluator_version=evaluator_version,
            status=status,
            overall_score=overall_score,
            metrics=metric_items,
            findings=finding_items,
            evidence_ids=evidence_items,
            evaluated_at=evaluated_at,
            provenance=provenance,
        )
