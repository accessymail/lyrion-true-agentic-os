"""Adversarial tests for provider/inference adapter boundaries."""

from datetime import UTC, datetime

import pytest

from lyrion.core.types import ExecutionTarget
from lyrion.models.adapters import AdapterKind, ModelAccessAdapter
from lyrion.models.contracts import (
    ModelCapability,
    ModelModality,
    ModelRequest,
    ModelResponse,
)
from lyrion.models.registry import ModelRegistry, RegisteredModel
from lyrion.models.router import ModelDescriptor


class FakeAdapter:
    """Minimal provider-neutral adapter double."""

    def __init__(
        self,
        *,
        adapter_id: str = "fake",
        kind: AdapterKind = AdapterKind.NATIVE_PROVIDER,
        provider_name: str = "fake-provider",
        protocol: str = "test-api",
    ) -> None:
        self._adapter_id = adapter_id
        self._kind = kind
        self._provider_name = provider_name
        self._protocol = protocol

    @property
    def adapter_id(self) -> str:
        """Return stable adapter identity."""
        return self._adapter_id

    @property
    def kind(self) -> AdapterKind:
        """Return adapter classification."""
        return self._kind

    @property
    def provider_name(self) -> str:
        """Return provider identity."""
        return self._provider_name

    @property
    def protocol(self) -> str:
        """Return protocol identity."""
        return self._protocol

    def supports_capability(
        self,
        capability: ModelCapability,
    ) -> bool:
        """Support text generation and reasoning."""
        return capability in {
            ModelCapability.GENERATION,
            ModelCapability.REASONING,
        }

    def supports_modality(
        self,
        modality: ModelModality,
    ) -> bool:
        """Support text only."""
        return modality is ModelModality.TEXT

    async def generate(
        self,
        request: ModelRequest,
        *,
        model: str,
    ) -> ModelResponse:
        """Return a deterministic test response."""
        return ModelResponse(
            request_id=request.request_id,
            content="adapter-response",
            provider=self._provider_name,
            model=model,
            execution_target=ExecutionTarget.CLOUD_API,
            created_at=datetime.now(UTC),
        )


def make_registered_model(
    adapter: FakeAdapter,
    *,
    provider: str = "fake-provider",
    model: str = "fake-model",
) -> RegisteredModel:
    """Build a model registration bound to an adapter."""
    descriptor = ModelDescriptor(
        provider=provider,
        model=model,
        capabilities=frozenset(
            {
                ModelCapability.GENERATION,
                ModelCapability.REASONING,
            }
        ),
        modalities=frozenset(
            {ModelModality.TEXT},
        ),
        execution_target_name=ExecutionTarget.CLOUD_API.value,
    )

    return RegisteredModel(
        descriptor=descriptor,
        adapter_id=adapter.adapter_id,
        kind=adapter.kind,
    )


def make_request() -> ModelRequest:
    """Build a valid model request."""
    return ModelRequest(
        request_id="adapter:test",
        objective="Test adapter invocation.",
        created_at=datetime.now(UTC),
    )


def test_adapter_satisfies_provider_protocol() -> None:
    """A concrete adapter can satisfy the neutral adapter protocol."""
    adapter: ModelAccessAdapter = FakeAdapter()

    assert adapter.adapter_id == "fake"
    assert adapter.provider_name == "fake-provider"
    assert adapter.protocol == "test-api"


@pytest.mark.asyncio
async def test_adapter_generation_is_provider_neutral() -> None:
    """Adapter invocation returns normalized gateway data."""
    adapter: ModelAccessAdapter = FakeAdapter()

    response = await adapter.generate(
        make_request(),
        model="fake-model",
    )

    assert response.request_id == "adapter:test"
    assert response.provider == "fake-provider"
    assert response.model == "fake-model"


def test_registry_requires_unique_adapter_ids() -> None:
    """Adapter identities must be unique."""
    first = FakeAdapter(adapter_id="duplicate")

    registry = ModelRegistry(
        adapters=(first,),
    )

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        registry.register_adapter(
            FakeAdapter(adapter_id="duplicate"),
        )


def test_registry_rejects_unknown_adapter() -> None:
    """Models cannot reference missing adapters."""
    adapter = FakeAdapter()

    registry = ModelRegistry(
        adapters=(adapter,),
    )

    with pytest.raises(
        ValueError,
        match="unregistered adapter",
    ):
        registry.register_model(
            RegisteredModel(
                descriptor=make_registered_model(
                    adapter,
                ).descriptor,
                adapter_id="missing",
                kind=AdapterKind.NATIVE_PROVIDER,
            )
        )


def test_registry_rejects_kind_mismatch() -> None:
    """Model registration must match adapter classification."""
    adapter = FakeAdapter(
        kind=AdapterKind.AGGREGATOR,
    )

    registry = ModelRegistry(
        adapters=(adapter,),
    )

    with pytest.raises(
        ValueError,
        match="kind does not match",
    ):
        registry.register_model(
            RegisteredModel(
                descriptor=make_registered_model(
                    adapter,
                ).descriptor,
                adapter_id=adapter.adapter_id,
                kind=AdapterKind.NATIVE_PROVIDER,
            )
        )


def test_registry_rejects_duplicate_models() -> None:
    """The same provider/model pair cannot be registered twice."""
    adapter = FakeAdapter()

    registered = make_registered_model(
        adapter,
    )

    registry = ModelRegistry(
        adapters=(adapter,),
        models=(registered,),
    )

    with pytest.raises(
        ValueError,
        match="model already registered",
    ):
        registry.register_model(
            registered,
        )


def test_registry_resolves_model_and_adapter() -> None:
    """Registry resolution must return stable objects."""
    adapter = FakeAdapter()

    registered = make_registered_model(
        adapter,
    )

    registry = ModelRegistry(
        adapters=(adapter,),
        models=(registered,),
    )

    resolved = registry.resolve(
        provider="fake-provider",
        model="fake-model",
    )
    resolved_adapter = registry.resolve_adapter(
        "fake",
    )

    assert resolved == registered
    assert resolved_adapter is adapter


def test_registry_order_is_deterministic() -> None:
    """Registry exposure must not depend on insertion order."""
    adapter_a = FakeAdapter(
        adapter_id="b",
        provider_name="provider-b",
    )
    adapter_b = FakeAdapter(
        adapter_id="a",
        provider_name="provider-a",
    )

    registry = ModelRegistry(
        adapters=(adapter_a, adapter_b),
        models=(
            make_registered_model(
                adapter_a,
                provider="provider-b",
                model="model-b",
            ),
            make_registered_model(
                adapter_b,
                provider="provider-a",
                model="model-a",
            ),
        ),
    )

    assert tuple(
        adapter.adapter_id
        for adapter in registry.adapters
    ) == ("a", "b")

    assert tuple(
        entry.descriptor.provider
        for entry in registry.models
    ) == ("provider-a", "provider-b")


def test_adapter_kinds_distinguish_access_mechanisms() -> None:
    """Different model-access mechanisms must remain distinguishable."""
    kinds = (
        AdapterKind.NATIVE_PROVIDER,
        AdapterKind.PROTOCOL_COMPATIBILITY,
        AdapterKind.AGGREGATOR,
        AdapterKind.INFERENCE_RUNTIME,
        AdapterKind.SELF_HOSTED,
    )

    assert len(set(kinds)) == 5


def test_registry_preserves_adapter_kind() -> None:
    """Registry entries must preserve adapter classification."""
    adapter = FakeAdapter(
        kind=AdapterKind.AGGREGATOR,
    )

    registry = ModelRegistry(
        adapters=(adapter,),
        models=(
            make_registered_model(adapter),
        ),
    )

    resolved = registry.resolve(
        provider="fake-provider",
        model="fake-model",
    )

    assert resolved.kind is AdapterKind.AGGREGATOR
