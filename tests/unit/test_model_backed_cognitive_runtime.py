"""Tests for the model-backed Cognitive Runtime."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lyrion.cognition.contracts import (
    CognitiveBudget,
    CognitiveConstraints,
    CognitiveRequestStatus,
    ReasonRequest,
)
from lyrion.cognition.model_backed_runtime import ModelBackedCognitiveRuntime
from lyrion.core.types import ExecutionTarget
from lyrion.models.contracts import (
    ModelCapability,
    ModelModality,
    ModelRequest,
    ModelResponse,
)
from lyrion.models.gateway import ModelGateway

BASE_TIME = datetime(2026, 9, 2, 10, 0, tzinfo=UTC)


class FakeGateway:
    """Deterministic fake Model Gateway."""

    def __init__(
        self,
        *,
        response: ModelResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        """Initialize fake gateway behavior."""
        self.response = response
        self.error = error
        self.requests: list[ModelRequest] = []

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Return a deterministic response or raise an error."""
        self.requests.append(request)

        if self.error is not None:
            raise self.error

        if self.response is None:
            raise AssertionError("fake response was not configured")

        return self.response


def make_response() -> ModelResponse:
    """Create a deterministic model response."""
    return ModelResponse(
        request_id="reason:runtime:001",
        content="Model-backed answer.",
        provider="fake",
        model="fake-model",
        execution_target=ExecutionTarget.CLOUD_API,
        confidence=0.85,
        created_at=BASE_TIME,
    )


def make_request(
    *,
    required_capabilities: tuple[str, ...] = (),
    max_model_calls: int = 1,
    require_verification: bool = True,
    verification_requirements: tuple[str, ...] = (),
) -> ReasonRequest:
    """Create a valid reasoning request."""
    return ReasonRequest(
        request_id="reason:runtime:001",
        objective="Analyze the supplied architecture.",
        context_refs=("context:001",),
        evidence_refs=("evidence:001",),
        constraints=CognitiveConstraints(
            require_verification=require_verification,
        ),
        budget=CognitiveBudget(
            max_model_calls=max_model_calls,
            max_runtime_seconds=10.0,
            max_cost_units=1.0,
        ),
        required_capabilities=required_capabilities,
        verification_requirements=verification_requirements,
        created_at=BASE_TIME,
    )


def make_runtime(gateway: ModelGateway) -> ModelBackedCognitiveRuntime:
    """Build a model-backed runtime for tests."""
    return ModelBackedCognitiveRuntime(gateway=gateway)


@pytest.mark.asyncio
async def test_reason_routes_request_through_model_gateway() -> None:
    """Reasoning request is translated and sent to the gateway."""
    gateway = FakeGateway(response=make_response())
    runtime = make_runtime(gateway)

    result = await runtime.reason(make_request())

    assert result.status is CognitiveRequestStatus.COMPLETED
    assert result.answer == "Model-backed answer."
    assert result.provider == "fake"
    assert result.model == "fake-model"
    assert result.confidence == 0.85
    assert result.uncertainty == pytest.approx(0.15)
    assert result.evidence_refs == ("evidence:001",)
    assert result.verification_required is True
    assert len(gateway.requests) == 1


@pytest.mark.asyncio
async def test_reason_preserves_request_context() -> None:
    """Context and evidence references cross the runtime boundary."""
    gateway = FakeGateway(response=make_response())
    runtime = make_runtime(gateway)

    await runtime.reason(make_request())

    model_request = gateway.requests[0]

    assert model_request.request_id == "reason:runtime:001"
    assert model_request.objective == "Analyze the supplied architecture."
    assert model_request.context_refs == ("context:001",)
    assert model_request.evidence_refs == ("evidence:001",)
    assert model_request.modality is ModelModality.TEXT


@pytest.mark.asyncio
async def test_reason_normalizes_capabilities() -> None:
    """Cognitive capability names become model capability enums."""
    gateway = FakeGateway(response=make_response())
    runtime = make_runtime(gateway)

    await runtime.reason(
        make_request(required_capabilities=("GENERATION", "REASONING")),
    )

    model_request = gateway.requests[0]

    assert model_request.required_capabilities == (
        ModelCapability.GENERATION,
        ModelCapability.REASONING,
    )


@pytest.mark.asyncio
async def test_reason_rejects_unknown_capability() -> None:
    """Unknown model capabilities fail closed before the gateway call."""
    gateway = FakeGateway(response=make_response())
    runtime = make_runtime(gateway)

    result = await runtime.reason(
        make_request(required_capabilities=("UNKNOWN_CAPABILITY",)),
    )

    assert result.status is CognitiveRequestStatus.REJECTED
    assert result.answer is None
    assert result.provider is None
    assert result.model is None
    assert result.confidence == 0.0
    assert result.uncertainty == 1.0
    assert gateway.requests == []


def test_cognitive_budget_rejects_zero_model_calls() -> None:
    """The cognitive budget contract rejects zero model calls."""
    with pytest.raises(ValueError):
        CognitiveBudget(max_model_calls=0)


@pytest.mark.asyncio
async def test_reason_requires_verification_from_request() -> None:
    """Explicit verification requirements force verification."""
    gateway = FakeGateway(response=make_response())
    runtime = make_runtime(gateway)

    result = await runtime.reason(
        make_request(
            require_verification=False,
            verification_requirements=("source-check",),
        ),
    )

    assert result.status is CognitiveRequestStatus.COMPLETED
    assert result.verification_required is True


@pytest.mark.asyncio
async def test_reason_can_disable_verification() -> None:
    """Verification stays disabled when no requirement is present."""
    gateway = FakeGateway(response=make_response())
    runtime = make_runtime(gateway)

    result = await runtime.reason(make_request(require_verification=False))

    assert result.status is CognitiveRequestStatus.COMPLETED
    assert result.verification_required is False


@pytest.mark.asyncio
async def test_reason_maps_timeout_to_timeout_result() -> None:
    """Gateway timeouts become bounded cognitive timeout results."""
    gateway = FakeGateway(error=TimeoutError("gateway timeout"))
    runtime = make_runtime(gateway)

    result = await runtime.reason(make_request())

    assert result.status is CognitiveRequestStatus.TIMEOUT
    assert result.answer is None
    assert result.provider is None
    assert result.model is None
    assert result.confidence == 0.0
    assert result.uncertainty == 1.0


@pytest.mark.asyncio
async def test_reason_maps_validation_error_to_rejected_result() -> None:
    """Gateway validation failures become rejected cognitive results."""
    gateway = FakeGateway(error=ValueError("invalid gateway request"))
    runtime = make_runtime(gateway)

    result = await runtime.reason(make_request())

    assert result.status is CognitiveRequestStatus.REJECTED
    assert result.answer is None
    assert result.provider is None
    assert result.model is None


@pytest.mark.asyncio
async def test_reason_maps_unexpected_error_to_failed_result() -> None:
    """Unexpected gateway failures become failed cognitive results."""
    gateway = FakeGateway(error=RuntimeError("unexpected gateway failure"))
    runtime = make_runtime(gateway)

    result = await runtime.reason(make_request())

    assert result.status is CognitiveRequestStatus.FAILED
    assert result.answer is None
    assert result.provider is None
    assert result.model is None
