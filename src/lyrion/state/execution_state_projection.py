"""Projection of execution feedback into operational state."""

from __future__ import annotations

from datetime import UTC, datetime

from lyrion.events.models import EventSensitivity, EventTrustLevel
from lyrion.state.execution_feedback import ExecutionFeedback
from lyrion.state.models import StateRecord, StateValueType


class ExecutionStateProjectionAdapter:
    """Project trusted execution feedback into factual state."""

    def project(
        self,
        feedback: ExecutionFeedback,
        *,
        subject: str,
        now: datetime | None = None,
    ) -> StateRecord:
        """Create an immutable state record from execution evidence."""
        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        effective_time = (
            feedback.completed_at
            or feedback.started_at
        )

        if effective_time > current_time:
            raise ValueError(
                "feedback cannot become effective in the future"
            )

        value = {
            "execution_id": feedback.execution_id,
            "request_id": feedback.request_id,
            "status": feedback.status.value,
            "started_at": feedback.started_at.astimezone(
                UTC
            ).isoformat(),
            "completed_at": (
                feedback.completed_at.astimezone(
                    UTC
                ).isoformat()
                if feedback.completed_at is not None
                else None
            ),
            "output_ref": feedback.output_ref,
            "error_code": feedback.error_code,
            "checkpoint_ref": feedback.checkpoint_ref,
        }

        return StateRecord(
            state_id=(
                f"state:execution:{feedback.execution_id}"
            ),
            subject=subject,
            key="execution_outcome",
            value_type=StateValueType.OBJECT,
            value=value,
            evidence_refs=feedback.source_event_ids,
            observed_at=current_time.astimezone(UTC),
            effective_at=effective_time.astimezone(UTC),
            expires_at=None,
            confidence=1.0,
            trust_level=EventTrustLevel.SYSTEM,
            sensitivity=EventSensitivity.INTERNAL,
            revision=1,
            supersedes_state_id=None,
        )
