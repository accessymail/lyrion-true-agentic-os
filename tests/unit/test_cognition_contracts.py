"""Tests for the provider-neutral Cognitive Runtime contracts."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lyrion.cognition.contracts import (
    CognitiveBudget,
    CognitiveConstraints,
    CognitiveRequestStatus,
    CognitiveResult,
    ReasonRequest,
)
from lyrion.cognition.runtime import CognitiveRuntime
from lyrion.core.types import RiskLevel


def make_request(
    *,
    request_id: str = "reason:test",
    objective: str = "Determine the next safe step.",
    context_refs: tuple[str, ...] = (),
    evidence_refs: tuple[str, ...] = (),
    constraints: CognitiveConstraints | None = None,
    budget: CognitiveBudget | None = None,
    risk_class: RiskLevel = RiskLevel.LOW,
    required_capabilities: tuple[str, ...] = (),
    verification_requirements: tuple[str, ...] = (),
    created_at: datetime | None = None,
) -> ReasonRequest:
    """Build a valid baseline reasoning request."""
    return ReasonRequest(
        request_id=request_id,
        objective=objective,
        context_refs=context_refs,
        evidence_refs=evidence_refs,
        constraints=constraints or CognitiveConstraints(),
        budget=budget or CognitiveBudget(),
        risk_class=risk_class,
        required_capabilities=required_capabilities,
        verification_requirements=verification_requirements,
        created_at=created_at or datetime.now(UTC),
    )


def test_reason_request_is_immutable() -> None:
    """Reason requests must be immutable."""
    request = make_request()

    with pytest.raises(ValidationError):
        request.objective = "changed"


def test_reason_request_rejects_naive_timestamp() -> None:
    """Naive timestamps must fail closed."""
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        make_request(
            created_at=datetime.now(),
        )


def test_reason_request_has_explicit_defaults() -> None:
    """The first cognitive contract should have bounded defaults."""
    request = make_request()

    assert request.constraints == CognitiveConstraints()
    assert request.budget == CognitiveBudget()
    assert request.risk_class.value == "LOW"
    assert request.constraints.require_verification is True


def test_reason_request_preserves_context_and_evidence_refs() -> None:
    """Context and evidence references must remain explicit."""
    request = make_request(
        context_refs=("ctx:1", "ctx:2"),
        evidence_refs=("evidence:1",),
    )

    assert request.context_refs == ("ctx:1", "ctx:2")
    assert request.evidence_refs == ("evidence:1",)


def test_cognitive_result_is_immutable() -> None:
    """Cognitive results must be immutable."""
    result = CognitiveResult(
        request_id="reason:test",
        status=CognitiveRequestStatus.COMPLETED,
        answer="safe",
        created_at=datetime.now(UTC),
    )

    with pytest.raises(ValidationError):
        result.answer = "changed"


def test_cognitive_result_normalizes_timestamp_to_utc() -> None:
    """Result timestamps must normalize safely to UTC."""
    result = CognitiveResult(
        request_id="reason:test",
        status=CognitiveRequestStatus.COMPLETED,
        created_at=datetime.now(UTC),
    )

    assert result.normalized_created_at().tzinfo == UTC


def test_cognitive_runtime_protocol_can_be_implemented() -> None:
    """A concrete implementation can satisfy the provider-neutral contract."""

    class FakeRuntime:
        async def reason(
            self,
            request: ReasonRequest,
        ) -> CognitiveResult:
            return CognitiveResult(
                request_id=request.request_id,
                status=CognitiveRequestStatus.COMPLETED,
                answer="ok",
                created_at=datetime.now(UTC),
            )

    runtime: CognitiveRuntime = FakeRuntime()

    assert runtime is not None
