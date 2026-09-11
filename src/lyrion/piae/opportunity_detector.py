"""Deterministic opportunity detection for PIAE."""

from __future__ import annotations

from datetime import UTC, datetime

from lyrion.core.types import AutonomyLevel, OpportunityId
from lyrion.events.models import Event
from lyrion.piae.contracts import Opportunity, OpportunityStatus


class OpportunityDetector:
    """Detect explicitly declared proactive opportunities from events."""

    def detect(
        self,
        event: Event,
        *,
        now: datetime | None = None,
    ) -> Opportunity | None:
        """Convert an eligible event into an opportunity."""
        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        payload = event.payload

        if payload.get("creates_opportunity") is not True:
            return None

        title = payload.get("opportunity_title")
        description = payload.get("opportunity_description")

        if not isinstance(title, str) or not title.strip():
            raise ValueError(
                "opportunity_title is required when an opportunity is declared"
            )

        if not isinstance(description, str) or not description.strip():
            raise ValueError(
                "opportunity_description is required when an opportunity "
                "is declared"
            )

        expires_at = payload.get("opportunity_expires_at")

        if expires_at is not None and not isinstance(
            expires_at,
            datetime,
        ):
            raise ValueError(
                "opportunity_expires_at must be a datetime"
            )

        return Opportunity(
            opportunity_id=OpportunityId(
                f"opportunity:{event.event_id}",
            ),
            correlation_id=event.correlation_id,
            trigger_event_ids=(event.event_id,),
            relevant_state_ids=self._string_tuple(
                payload.get("relevant_state_ids"),
            ),
            goal_context=self._string_tuple(
                payload.get("goal_context"),
            ),
            title=title.strip(),
            description=description.strip(),
            user_relevance=self._bounded_float(
                payload.get("user_relevance"),
                default=0.0,
            ),
            expected_benefit=self._bounded_float(
                payload.get("expected_benefit"),
                default=0.0,
            ),
            interruption_cost=self._bounded_float(
                payload.get("interruption_cost"),
                default=0.0,
            ),
            risk_score=self._bounded_float(
                payload.get("risk_score"),
                default=0.0,
            ),
            reversibility=self._bounded_float(
                payload.get("reversibility"),
                default=1.0,
            ),
            urgency=self._bounded_float(
                payload.get("urgency"),
                default=0.0,
            ),
            confidence=self._bounded_float(
                payload.get("confidence"),
                default=0.0,
            ),
            required_capabilities=self._string_tuple(
                payload.get("required_capabilities"),
            ),
            required_autonomy_level=self._autonomy_level(
                payload.get("required_autonomy_level"),
            ),
            sensitivity=event.sensitivity,
            trust_level=event.trust_level,
            status=OpportunityStatus.OPEN,
            created_at=event.observed_at,
            expires_at=expires_at,
        )

    @staticmethod
    def _string_tuple(value: object) -> tuple[str, ...]:
        """Convert a sequence of strings to a validated tuple."""
        if value is None:
            return ()

        if not isinstance(value, (list, tuple)):
            raise ValueError("expected a sequence of strings")

        result = tuple(
            item.strip()
            for item in value
            if isinstance(item, str) and item.strip()
        )

        if len(result) != len(value):
            raise ValueError(
                "sequence values must all be non-empty strings"
            )

        if len(set(result)) != len(result):
            raise ValueError(
                "sequence values must be unique"
            )

        return result

    @staticmethod
    def _bounded_float(
        value: object,
        *,
        default: float,
    ) -> float:
        """Return a validated 0..1 numeric value."""
        if value is None:
            return default

        if isinstance(value, bool) or not isinstance(
            value,
            (int, float),
        ):
            raise ValueError("expected a numeric value")

        numeric = float(value)

        if not 0.0 <= numeric <= 1.0:
            raise ValueError(
                "numeric opportunity values must be between 0 and 1"
            )

        return numeric

    @staticmethod
    def _autonomy_level(
        value: object,
    ) -> AutonomyLevel:
        """Parse the requested autonomy level."""
        if value is None:
            return AutonomyLevel.L0

        if not isinstance(value, str):
            raise ValueError(
                "required_autonomy_level must be a string"
            )

        try:
            return AutonomyLevel(
                value.strip().upper(),
            )
        except ValueError as exc:
            raise ValueError(
                "invalid required_autonomy_level"
            ) from exc
