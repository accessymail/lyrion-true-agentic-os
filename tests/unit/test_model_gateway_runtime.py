from datetime import UTC, datetime

import pytest

from lyrion.core.types import ExecutionTarget
from lyrion.models.adapters import AdapterKind
from lyrion.models.contracts import ModelCapability, ModelModality, ModelRequest, ModelResponse
from lyrion.models.registry import ModelRegistry, RegisteredModel
from lyrion.models.router import ModelDescriptor, ModelRouter
from lyrion.models.runtime import RoutedModelGateway, build_model_gateway

BASE_TIME = datetime(2026, 9, 2, 10, 0, tzinfo=UTC)


class FakeAdapter:
    adapter_id = "fake-native"
    kind = AdapterKind.NATIVE_PROVIDER
    provider_name = "fake"
    protocol = "fake-native"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def supports_capability(self, capability: ModelCapability) -> bool:
        return capability in {
            ModelCapability.GENERATION,
            ModelCapability.REASONING,
        }

    def supports_modality(self, modality: ModelModality) -> bool:
        return modality is ModelModality.TEXT

    async def generate(self, request: ModelRequest, *, model: str) -> ModelResponse:
        self.calls.append((request.request_id, model))
        return ModelResponse(
            request_id=request.request_id,
            content=f"response from {model}",
            provider=self.provider_name,
            model=model,
            execution_target=ExecutionTarget.CLOUD_API,
            confidence=0.8,
            created_at=BASE_TIME,
        )


def make_request(
    *,
    reasoning_difficulty: float = 0.8,
    required_capabilities: tuple[ModelCapability, ...] = (
        ModelCapability.GENERATION,
    ),
) -> ModelRequest:
    return ModelRequest(
        request_id="request:gateway:001",
        objective="Analyze this request.",
        required_capabilities=required_capabilities,
        modality=ModelModality.TEXT,
        reasoning_difficulty=reasoning_difficulty,
        network_required=True,
        created_at=BASE_TIME,
    )


def make_gateway() -> tuple[RoutedModelGateway, FakeAdapter]:
    adapter = FakeAdapter()
    descriptor = ModelDescriptor(
        provider="fake",
        model="fake-model",
        capabilities=frozenset({
            ModelCapability.GENERATION,
            ModelCapability.REASONING,
        }),
        modalities=frozenset({ModelModality.TEXT}),
        execution_target_name=ExecutionTarget.CLOUD_API.value,
        reasoning_quality=0.9,
        latency_score=0.8,
        cost_score=0.7,
        reliability_score=0.9,
        health_score=1.0,
        privacy_safe=False,
        network_required=True,
        available=True,
    )
    registry = ModelRegistry(
        adapters=(adapter,),
        models=(
            RegisteredModel(
                descriptor=descriptor,
                adapter_id=adapter.adapter_id,
                kind=adapter.kind,
            ),
        ),
    )
    router = ModelRouter(tuple(model.descriptor for model in registry.models))
    return RoutedModelGateway(router=router, registry=registry), adapter


@pytest.mark.asyncio
async def test_gateway_routes_and_invokes_selected_adapter() -> None:
    gateway, adapter = make_gateway()
    result = await gateway.generate(make_request())
    assert result.content == "response from fake-model"
    assert result.provider == "fake"
    assert result.model == "fake-model"
    assert adapter.calls == [("request:gateway:001", "fake-model")]


@pytest.mark.asyncio
async def test_gateway_preserves_normalized_model_response() -> None:
    gateway, _ = make_gateway()
    result = await gateway.generate(make_request())
    assert result.request_id == "request:gateway:001"
    assert result.execution_target is ExecutionTarget.CLOUD_API
    assert result.confidence == 0.8
    assert result.created_at == BASE_TIME


def test_build_model_gateway_returns_gateway_implementation() -> None:
    gateway, _ = make_gateway()
    contract = build_model_gateway(
        router=gateway.router,
        registry=gateway.registry,
    )
    assert isinstance(contract, RoutedModelGateway)


@pytest.mark.asyncio
async def test_gateway_exposes_routing_failure() -> None:
    gateway, _ = make_gateway()
    request = make_request(
        required_capabilities=(ModelCapability.PLANNING,),
    )
    with pytest.raises(RuntimeError, match="no compatible model"):
        await gateway.generate(request)


@pytest.mark.asyncio
async def test_gateway_resolves_adapter_through_registry() -> None:
    gateway, adapter = make_gateway()
    result = await gateway.generate(
        make_request(reasoning_difficulty=0.2),
    )
    assert result.model == "fake-model"
    assert adapter.calls[-1] == (
        "request:gateway:001",
        "fake-model",
    )
