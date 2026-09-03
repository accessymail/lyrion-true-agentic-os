"""Tests for the Cognitive Runtime implementation boundary."""

from datetime import UTC, datetime

import pytest

from lyrion.cognition.contracts import (
    CognitiveRequestStatus,
    ReasonRequest,
)
from lyrion.cognition.runtime import (
    CognitiveRuntime,
    UnavailableCognitiveRuntime,
)


def make_request() -> ReasonRequest:
    """Build a valid bounded cognitive request."""
    return ReasonRequest(
        request_id="reason:test",
        objective="Determine the next safe step.",
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_unavailable_runtime_fails_closed() -> None:
    """No configured provider must never silently fabricate cognition."""
    runtime = UnavailableCognitiveRuntime()

    result = await runtime.reason(make_request())

    assert result.status is CognitiveRequestStatus.REJECTED
    assert result.request_id == "reason:test"
    assert result.answer is None
    assert result.proposed_plan == ()
    assert result.confidence == 0.0
    assert result.uncertainty == 1.0
    assert result.verification_required is True
    assert result.provider is None
    assert result.model is None


@pytest.mark.asyncio
async def test_runtime_implements_cognitive_protocol() -> None:
    """The concrete runtime must satisfy the provider-neutral protocol."""
    runtime: CognitiveRuntime = UnavailableCognitiveRuntime()

    result = await runtime.reason(make_request())

    assert result.status is CognitiveRequestStatus.REJECTED
