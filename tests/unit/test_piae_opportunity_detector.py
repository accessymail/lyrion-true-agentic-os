"""Adversarial tests for deterministic PIAE opportunity detection."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lyrion.core.types import (
    CorrelationId,
    EventId,
    IdempotencyKey,
)
from lyrion.events.models import (
    Event,
    EventSensitivity,
    EventTrustLevel,
)
from lyrion.piae.contracts import (
    OpportunityStatus,
)
from lyrion.piae.opportunity_detector import OpportunityDetector


def make_event(
    *,
    now: datetime | None = None,
    payload: dict[str, object] | None = None,
    **overrides: object,
) -> Event:
    """Create a valid baseline event."""
    current_time = now or datetime.now(UTC)

    values: dict[str, object] = {
        "event_id": EventId("evt_detector_001"),
        "event_type": "test.observation",
        "source": "unit-test",
        "timestamp": current_time,
        "observed_at": current_time,
        "subject": "test-subject",
        "payload": payload or {},
        "sensitivity": EventSensitivity.INTERNAL,
        "provenance": "unit-test",
        "trust_level": EventTrustLevel.SYSTEM,
        "correlation_id": CorrelationId("corr_detector_001"),
        "idempotency_key": IdempotencyKey(
            "idem_detector_001",
        ),
    }

    values.update(overrides)

    return Event(**values)


def opportunity_payload(
    **overrides: object,
) -> dict[str, object]:
    """Create a valid explicit opportunity declaration."""
    payload: dict[str, object] = {
        "creates_opportunity": True,
        "opportunity_title": "Prepare proactive action",
        "opportunity_description": (
            "A bounded proactive action is available."
        ),
        "user_relevance": 0.90,
        "expected_benefit": 0.85,
        "interruption_cost": 0.10,
        "risk_score": 0.10,
        "reversibility": 0.90,
        "urgency": 0.50,
        "confidence": 0.95,
        "required_capabilities": (
            "development.prepare",
        ),
        "required_autonomy_level": "L1",
        "relevant_state_ids": (
            "state_detector_001",
        ),
        "goal_context": (
            "maintain-development-workflow",
        ),
    }

    payload.update(overrides)

    return payload


def test_valid_event_creates_opportunity() -> None:
    """An explicitly qualifying event should produce an opportunity."""
    now = datetime.now(UTC)

    event = make_event(
        now=now,
        payload=opportunity_payload(),
    )

    opportunity = OpportunityDetector().detect(
        event,
        now=now,
    )

    assert opportunity is not None
    assert opportunity.opportunity_id == (
        "opportunity:evt_detector_001"
    )
    assert opportunity.trigger_event_ids == (
        EventId("evt_detector_001"),
    )
    assert opportunity.title == "Prepare proactive action"
    assert opportunity.description == (
        "A bounded proactive action is available."
    )
    assert opportunity.status is OpportunityStatus.OPEN
    assert opportunity.created_at == event.observed_at
    assert opportunity.correlation_id == event.correlation_id


def test_event_without_opportunity_signal_returns_none() -> None:
    """Ordinary observations should not become opportunities."""
    event = make_event(
        payload={
            "message": "ordinary observation",
        },
    )

    assert OpportunityDetector().detect(event) is None


def test_false_opportunity_signal_returns_none() -> None:
    """A false opportunity flag should be ignored."""
    event = make_event(
        payload={
            "creates_opportunity": False,
            "opportunity_title": "Should not appear",
            "opportunity_description": "Should not appear",
        },
    )

    assert OpportunityDetector().detect(event) is None


def test_missing_title_is_rejected() -> None:
    """Declared opportunities require an explicit title."""
    payload = opportunity_payload()
    payload.pop("opportunity_title")

    with pytest.raises(
        ValueError,
        match="opportunity_title is required",
    ):
        OpportunityDetector().detect(
            make_event(payload=payload),
        )


def test_blank_title_is_rejected() -> None:
    """Whitespace-only opportunity titles are invalid."""
    payload = opportunity_payload(
        opportunity_title="   ",
    )

    with pytest.raises(
        ValueError,
        match="opportunity_title is required",
    ):
        OpportunityDetector().detect(
            make_event(payload=payload),
        )


def test_missing_description_is_rejected() -> None:
    """Declared opportunities require an explicit description."""
    payload = opportunity_payload()
    payload.pop("opportunity_description")

    with pytest.raises(
        ValueError,
        match="opportunity_description is required",
    ):
        OpportunityDetector().detect(
            make_event(payload=payload),
        )


def test_blank_description_is_rejected() -> None:
    """Whitespace-only descriptions are invalid."""
    payload = opportunity_payload(
        opportunity_description="   ",
    )

    with pytest.raises(
        ValueError,
        match="opportunity_description is required",
    ):
        OpportunityDetector().detect(
            make_event(payload=payload),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("user_relevance", -0.01),
        ("user_relevance", 1.01),
        ("expected_benefit", -0.01),
        ("expected_benefit", 1.01),
        ("interruption_cost", -0.01),
        ("interruption_cost", 1.01),
        ("risk_score", -0.01),
        ("risk_score", 1.01),
        ("reversibility", -0.01),
        ("reversibility", 1.01),
        ("urgency", -0.01),
        ("urgency", 1.01),
        ("confidence", -0.01),
        ("confidence", 1.01),
    ],
)
def test_numeric_bounds_are_enforced(
    field: str,
    value: object,
) -> None:
    """Opportunity scores must remain within 0..1."""
    payload = opportunity_payload(
        **{field: value},
    )

    with pytest.raises(ValueError):
        OpportunityDetector().detect(
            make_event(payload=payload),
        )


@pytest.mark.parametrize(
    "field",
    [
        "user_relevance",
        "expected_benefit",
        "interruption_cost",
        "risk_score",
        "reversibility",
        "urgency",
        "confidence",
    ],
)
def test_boolean_scores_are_rejected(field: str) -> None:
    """Boolean values must not masquerade as numeric scores."""
    payload = opportunity_payload(
        **{field: True},
    )

    with pytest.raises(
        ValueError,
        match="expected a numeric value",
    ):
        OpportunityDetector().detect(
            make_event(payload=payload),
        )


def test_invalid_numeric_type_is_rejected() -> None:
    """Non-numeric score values must be rejected."""
    payload = opportunity_payload(
        confidence="high",
    )

    with pytest.raises(
        ValueError,
        match="expected a numeric value",
    ):
        OpportunityDetector().detect(
            make_event(payload=payload),
        )


def test_duplicate_capabilities_are_rejected() -> None:
    """Required capability identifiers must be unique."""
    payload = opportunity_payload(
        required_capabilities=(
            "development.prepare",
            "development.prepare",
        ),
    )

    with pytest.raises(
        ValueError,
        match="sequence values must be unique",
    ):
        OpportunityDetector().detect(
            make_event(payload=payload),
        )


def test_duplicate_state_references_are_rejected() -> None:
    """Relevant state identifiers must be unique."""
    payload = opportunity_payload(
        relevant_state_ids=(
            "state_detector_001",
            "state_detector_001",
        ),
    )

    with pytest.raises(
        ValueError,
        match="sequence values must be unique",
    ):
        OpportunityDetector().detect(
            make_event(payload=payload),
        )


def test_non_string_sequence_value_is_rejected() -> None:
    """Sequence fields may contain only non-empty strings."""
    payload = opportunity_payload(
        goal_context=(
            "valid-goal",
            123,
        ),
    )

    with pytest.raises(
        ValueError,
        match="sequence values must all be non-empty strings",
    ):
        OpportunityDetector().detect(
            make_event(payload=payload),
        )


def test_blank_sequence_value_is_rejected() -> None:
    """Sequence entries must not be blank."""
    payload = opportunity_payload(
        goal_context=(
            "valid-goal",
            "   ",
        ),
    )

    with pytest.raises(
        ValueError,
        match="sequence values must all be non-empty strings",
    ):
        OpportunityDetector().detect(
            make_event(payload=payload),
        )


def test_invalid_autonomy_level_is_rejected() -> None:
    """Unknown autonomy levels must fail closed."""
    payload = opportunity_payload(
        required_autonomy_level="L99",
    )

    with pytest.raises(
        ValueError,
        match="invalid required_autonomy_level",
    ):
        OpportunityDetector().detect(
            make_event(payload=payload),
        )


def test_non_string_autonomy_level_is_rejected() -> None:
    """Autonomy level must use an explicit string identifier."""
    payload = opportunity_payload(
        required_autonomy_level=1,
    )

    with pytest.raises(
        ValueError,
        match="required_autonomy_level must be a string",
    ):
        OpportunityDetector().detect(
            make_event(payload=payload),
        )


def test_invalid_expiry_type_is_rejected() -> None:
    """Opportunity expiry must be a datetime."""
    payload = opportunity_payload(
        opportunity_expires_at="tomorrow",
    )

    with pytest.raises(
        ValueError,
        match="opportunity_expires_at must be a datetime",
    ):
        OpportunityDetector().detect(
            make_event(payload=payload),
        )


def test_timezone_aware_now_is_required() -> None:
    """Detector evaluation time must be timezone-aware."""
    event = make_event(
        payload=opportunity_payload(),
    )

    with pytest.raises(
        ValueError,
        match="now must be timezone-aware",
    ):
        OpportunityDetector().detect(
            event,
            now=datetime.now(),
        )


def test_event_observed_at_becomes_opportunity_creation_time() -> None:
    """Opportunity creation should preserve event observation timing."""
    event_time = datetime(
        2026,
        8,
        31,
        6,
        0,
        tzinfo=UTC,
    )

    detection_time = event_time + timedelta(minutes=3)

    event = make_event(
        now=event_time,
        payload=opportunity_payload(),
    )

    opportunity = OpportunityDetector().detect(
        event,
        now=detection_time,
    )

    assert opportunity is not None
    assert opportunity.created_at == event.observed_at
    assert opportunity.created_at != detection_time


def test_event_sensitivity_is_propagated() -> None:
    """Opportunity sensitivity should inherit from the source event."""
    event = make_event(
        payload=opportunity_payload(),
        sensitivity=EventSensitivity.SENSITIVE,
    )

    opportunity = OpportunityDetector().detect(event)

    assert opportunity is not None
    assert opportunity.sensitivity is EventSensitivity.SENSITIVE


def test_event_trust_is_propagated() -> None:
    """Opportunity trust should inherit from the source event."""
    event = make_event(
        payload=opportunity_payload(),
        trust_level=EventTrustLevel.HIGH,
    )

    opportunity = OpportunityDetector().detect(event)

    assert opportunity is not None
    assert opportunity.trust_level is EventTrustLevel.HIGH


def test_correlation_is_propagated() -> None:
    """Correlation identity should survive event-to-opportunity conversion."""
    correlation_id = CorrelationId(
        "corr_detector_specific",
    )

    event = make_event(
        payload=opportunity_payload(),
        correlation_id=correlation_id,
    )

    opportunity = OpportunityDetector().detect(event)

    assert opportunity is not None
    assert opportunity.correlation_id == correlation_id


def test_detector_does_not_modify_event() -> None:
    """Detection must not mutate the immutable source event."""
    event = make_event(
        payload=opportunity_payload(),
    )

    before = event.model_dump(mode="json")

    OpportunityDetector().detect(event)

    after = event.model_dump(mode="json")

    assert after == before


def test_detected_opportunity_is_immutable() -> None:
    """Detected opportunities must retain their immutable contract."""
    event = make_event(
        payload=opportunity_payload(),
    )

    opportunity = OpportunityDetector().detect(event)

    assert opportunity is not None

    with pytest.raises(ValidationError):
        opportunity.title = "changed"


def test_detection_is_deterministic_for_same_event() -> None:
    """Repeated detection of the same event should be deterministic."""
    now = datetime.now(UTC)

    event = make_event(
        now=now,
        payload=opportunity_payload(),
    )

    detector = OpportunityDetector()

    first = detector.detect(
        event,
        now=now,
    )
    second = detector.detect(
        event,
        now=now,
    )

    assert first is not None
    assert second is not None
    assert first.model_dump(mode="json") == (
        second.model_dump(mode="json")
    )


def test_explicit_expiry_is_preserved() -> None:
    """Declared opportunity expiry should survive detection."""
    now = datetime.now(UTC)
    expiry = now + timedelta(minutes=10)

    event = make_event(
        now=now,
        payload=opportunity_payload(
            opportunity_expires_at=expiry,
        ),
    )

    opportunity = OpportunityDetector().detect(
        event,
        now=now,
    )

    assert opportunity is not None
    assert opportunity.expires_at == expiry
