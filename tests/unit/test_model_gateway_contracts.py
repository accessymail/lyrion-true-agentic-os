"""Tests for the provider-neutral Model Gateway contracts."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lyrion.core.types import ExecutionTarget, RiskLevel
from lyrion.models.contracts import (
    ModelBudget,
    ModelCapability,
    ModelModality,
    ModelRequest,
    ModelResponse,
)
from lyrion.models.gateway import ModelGateway


def make_request(
    *,
    request_id: str = "model:test",
    objective: str = "Solve the task safely.",
    required_capabilities: tuple[ModelCapability, ...] = (),
    modality: ModelModality = ModelModality.TEXT,
    risk_level: RiskLevel = RiskLevel.LOW,
    preferred_targets: tuple[ExecutionTarget, ...] = (),
    created_at: datetime | None = None,
) -> ModelRequest:
    """Build a valid baseline model request."""
    return ModelRequest(
        request_id=request_id,
        objective=objective,
        required_capabilities=required_capabilities,
        modality=modality,
        risk_level=risk_level,
        preferred_targets=preferred_targets,
        created_at=created_at or datetime.now(UTC),
    )


def test_model_request_is_immutable() -> None:
    """Model requests must be immutable."""
    request = make_request()

    with pytest.raises(ValidationError):
        request.objective = "changed"


def test_model_request_rejects_naive_timestamp() -> None:
    """Naive timestamps must fail closed."""
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        make_request(
            created_at=datetime.now(),
        )


def test_model_request_is_provider_neutral() -> None:
    """Model requests must not require a specific provider."""
    request = make_request(
        required_capabilities=(
            ModelCapability.REASONING,
            ModelCapability.PLANNING,
        ),
        modality=ModelModality.TEXT,
        risk_level=RiskLevel.LOW,
        preferred_targets=(
            ExecutionTarget.CLOUD_API,
            ExecutionTarget.CLOUD_GPU,
        ),
    )

    assert request.required_capabilities == (
        ModelCapability.REASONING,
        ModelCapability.PLANNING,
    )
    assert request.preferred_targets == (
        ExecutionTarget.CLOUD_API,
        ExecutionTarget.CLOUD_GPU,
    )


def test_model_budget_is_explicitly_bounded() -> None:
    """Model requests must carry explicit resource bounds."""
    request = make_request()

    assert request.budget == ModelBudget()
    assert request.budget.max_runtime_seconds == 30.0
    assert request.budget.max_output_tokens == 4096


def test_model_response_is_immutable() -> None:
    """Gateway responses must be immutable."""
    response = ModelResponse(
        request_id="model:test",
        content="result",
        provider="test-provider",
        model="test-model",
        execution_target=ExecutionTarget.CLOUD_API,
        created_at=datetime.now(UTC),
    )

    with pytest.raises(ValidationError):
        response.content = "changed"


@pytest.mark.asyncio
async def test_model_gateway_protocol_can_be_implemented() -> None:
    """A concrete gateway can satisfy the provider-neutral protocol."""

    class FakeGateway:
        async def generate(
            self,
            request: ModelRequest,
        ) -> ModelResponse:
            return ModelResponse(
                request_id=request.request_id,
                content="result",
                provider="test-provider",
                model="test-model",
                execution_target=ExecutionTarget.CLOUD_API,
                created_at=datetime.now(UTC),
            )

    gateway: ModelGateway = FakeGateway()
    response = await gateway.generate(make_request())

    assert response.request_id == "model:test"
    assert response.provider == "test-provider"
