"""Tests for Google Gemini model registration."""

from __future__ import annotations

from lyrion.core.types import ExecutionTarget
from lyrion.models.adapters import AdapterKind
from lyrion.models.contracts import ModelCapability, ModelModality
from lyrion.models.providers.google_gemini_registry import (
    GEMINI_3_7_FLASH,
    GEMINI_ADAPTER_ID,
    create_gemini_registry,
)
from lyrion.models.registry import ModelRegistry


class FakeGeminiModels:
    async def generate_content(self, *, model: str, contents: str, config: object) -> object:
        del model
        del contents
        del config
        return object()


class FakeGeminiAio:
    def __init__(self) -> None:
        self.models = FakeGeminiModels()


class FakeGeminiClient:
    def __init__(self) -> None:
        self.aio = FakeGeminiAio()


def make_registry() -> ModelRegistry:
    return create_gemini_registry(client=FakeGeminiClient())


def test_gemini_registry_registers_native_adapter() -> None:
    """Gemini is registered through the native provider adapter."""
    registry = make_registry()

    assert len(registry.adapters) == 1
    adapter = registry.resolve_adapter(GEMINI_ADAPTER_ID)

    assert adapter.adapter_id == GEMINI_ADAPTER_ID
    assert adapter.kind is AdapterKind.NATIVE_PROVIDER
    assert adapter.provider_name == "google"
    assert adapter.protocol == "gemini-native"


def test_gemini_registry_registers_canonical_model() -> None:
    """The canonical Gemini model is present in the registry."""
    registry = make_registry()

    registered = registry.resolve(
        provider="google",
        model=GEMINI_3_7_FLASH,
    )

    assert registered.adapter_id == GEMINI_ADAPTER_ID
    assert registered.kind is AdapterKind.NATIVE_PROVIDER

    descriptor = registered.descriptor

    assert descriptor.provider == "google"
    assert descriptor.model == GEMINI_3_7_FLASH
    assert descriptor.execution_target_name == ExecutionTarget.CLOUD_API.value
    assert descriptor.modalities == frozenset(
        {ModelModality.TEXT},
    )

    assert descriptor.capabilities == frozenset(
        {
            ModelCapability.GENERATION,
            ModelCapability.REASONING,
            ModelCapability.PLANNING,
        },
    )


def test_gemini_registry_uses_cloud_api_boundary() -> None:
    """Native Gemini API access is represented as a cloud target."""
    registry = make_registry()

    registered = registry.resolve(
        provider="google",
        model=GEMINI_3_7_FLASH,
    )

    assert (
        registered.descriptor.execution_target_name
        == ExecutionTarget.CLOUD_API.value
    )
    assert registered.descriptor.network_required is True
    assert registered.descriptor.privacy_safe is False


def test_gemini_registry_is_router_compatible() -> None:
    """The registered model can satisfy a matching text request."""
    from datetime import UTC, datetime

    from lyrion.models.contracts import ModelRequest
    from lyrion.models.router import ModelRouter

    registry = make_registry()

    request = ModelRequest(
        request_id="request:gemini:registry:001",
        objective="Analyze the Lyrion model architecture.",
        required_capabilities=(
            ModelCapability.GENERATION,
            ModelCapability.REASONING,
        ),
        modality=ModelModality.TEXT,
        reasoning_difficulty=0.8,
        network_required=True,
        created_at=datetime(
            2026,
            9,
            2,
            10,
            0,
            tzinfo=UTC,
        ),
    )

    router = ModelRouter(
        tuple(
            registered.descriptor
            for registered in registry.models
        ),
    )

    selection = router.route(request)

    assert selection.provider == "google"
    assert selection.model == GEMINI_3_7_FLASH
    assert (
        selection.execution_target_name
        == ExecutionTarget.CLOUD_API.value
    )
