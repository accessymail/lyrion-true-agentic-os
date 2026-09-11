"""Tests for the native Google Gemini model-access adapter."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Final

import pytest
from google.genai import types

from lyrion.models.contracts import (
    ModelBudget,
    ModelModality,
    ModelRequest,
)
from lyrion.models.providers.google_gemini import GeminiNativeAdapter

BASE_TIME: Final = datetime(
    2026,
    9,
    2,
    10,
    0,
    tzinfo=UTC,
)


class FakeGeminiResponse:
    """Deterministic Gemini response."""

    def __init__(self, text: str | None) -> None:
        """Initialize the fake response."""
        self.text = text


class FakeGeminiModels:
    """Deterministic async Gemini models surface."""

    def __init__(
        self,
        *,
        response: FakeGeminiResponse | None = None,
        error: Exception | None = None,
        delay_seconds: float = 0.0,
    ) -> None:
        """Initialize fake model behavior."""
        self.response = response
        self.error = error
        self.delay_seconds = delay_seconds
        self.calls: list[dict[str, object]] = []

    async def generate_content(
        self,
        *,
        model: str,
        contents: str,
        config: types.GenerateContentConfig,
    ) -> object:
        """Return a deterministic fake response."""
        self.calls.append(
            {
                "model": model,
                "contents": contents,
                "config": config,
            },
        )

        if self.delay_seconds > 0.0:
            await asyncio.sleep(self.delay_seconds)

        if self.error is not None:
            raise self.error

        if self.response is None:
            raise AssertionError("fake response was not configured")

        return self.response


class FakeGeminiAio:
    """Deterministic async Gemini client."""

    def __init__(self, models: FakeGeminiModels) -> None:
        """Initialize the fake async client."""
        self.models = models


class FakeGeminiClient:
    """Deterministic Gemini client compatible with the adapter."""

    def __init__(self, models: FakeGeminiModels) -> None:
        """Initialize the fake client."""
        self.aio = FakeGeminiAio(models)


def make_request(
    *,
    objective: str = "Explain the architecture.",
    modality: ModelModality = ModelModality.TEXT,
    budget: ModelBudget | None = None,
) -> ModelRequest:
    """Create a valid model request."""
    return ModelRequest(
        request_id="request:gemini:test:001",
        objective=objective,
        modality=modality,
        budget=budget if budget is not None else ModelBudget(),
        created_at=BASE_TIME,
    )


@pytest.mark.asyncio
async def test_adapter_metadata() -> None:
    """Adapter exposes stable provider-neutral metadata."""
    models = FakeGeminiModels(
        response=FakeGeminiResponse("Hello from Gemini."),
    )
    adapter = GeminiNativeAdapter(
        client=FakeGeminiClient(models),
    )

    assert adapter.adapter_id == "google-gemini-native"
    assert adapter.provider_name == "google"
    assert adapter.protocol == "gemini-native"
    assert adapter.kind.value == "NATIVE_PROVIDER"


@pytest.mark.asyncio
async def test_adapter_supports_initial_capabilities() -> None:
    """Adapter reports its currently supported capabilities."""
    from lyrion.models.contracts import ModelCapability

    models = FakeGeminiModels(
        response=FakeGeminiResponse("ok"),
    )
    adapter = GeminiNativeAdapter(
        client=FakeGeminiClient(models),
    )

    assert adapter.supports_capability(ModelCapability.GENERATION)
    assert adapter.supports_capability(ModelCapability.REASONING)
    assert adapter.supports_capability(ModelCapability.PLANNING)
    assert not adapter.supports_capability(ModelCapability.VISION)


@pytest.mark.asyncio
async def test_adapter_supports_text_only_for_initial_slice() -> None:
    """Initial adapter deliberately exposes only text modality."""
    models = FakeGeminiModels(
        response=FakeGeminiResponse("ok"),
    )
    adapter = GeminiNativeAdapter(
        client=FakeGeminiClient(models),
    )

    assert adapter.supports_modality(ModelModality.TEXT)
    assert not adapter.supports_modality(ModelModality.AUDIO)
    assert not adapter.supports_modality(ModelModality.IMAGE)
    assert not adapter.supports_modality(ModelModality.VIDEO)


@pytest.mark.asyncio
async def test_generate_normalizes_gemini_response() -> None:
    """Gemini output is converted into Lyrion's response contract."""
    models = FakeGeminiModels(
        response=FakeGeminiResponse("  Gemini answer.  "),
    )
    adapter = GeminiNativeAdapter(
        client=FakeGeminiClient(models),
    )

    result = await adapter.generate(
        make_request(),
        model="gemini-test-model",
    )

    assert result.request_id == "request:gemini:test:001"
    assert result.content == "Gemini answer."
    assert result.provider == "google"
    assert result.model == "gemini-test-model"
    assert result.execution_target.value == "CLOUD_API"
    assert result.confidence == 0.0
    assert result.created_at.tzinfo is not None


@pytest.mark.asyncio
async def test_generate_passes_objective_and_output_budget() -> None:
    """Adapter forwards the objective and bounded output configuration."""
    models = FakeGeminiModels(
        response=FakeGeminiResponse("bounded answer"),
    )
    adapter = GeminiNativeAdapter(
        client=FakeGeminiClient(models),
    )

    request = make_request(
        objective="Describe the Model Fabric.",
        budget=ModelBudget(
            max_runtime_seconds=5.0,
            max_cost_units=1.0,
            max_output_tokens=123,
        ),
    )

    await adapter.generate(
        request,
        model="gemini-test-model",
    )

    assert len(models.calls) == 1
    call = models.calls[0]

    assert call["model"] == "gemini-test-model"
    assert call["contents"] == "Describe the Model Fabric."

    config = call["config"]
    assert isinstance(config, types.GenerateContentConfig)
    assert config.max_output_tokens == 123


@pytest.mark.asyncio
async def test_generate_rejects_empty_model() -> None:
    """Adapter rejects an empty model identifier."""
    models = FakeGeminiModels(
        response=FakeGeminiResponse("unused"),
    )
    adapter = GeminiNativeAdapter(
        client=FakeGeminiClient(models),
    )

    with pytest.raises(ValueError, match="model must not be empty"):
        await adapter.generate(
            make_request(),
            model="   ",
        )


@pytest.mark.asyncio
async def test_generate_rejects_non_text_modality() -> None:
    """Initial Gemini adapter rejects unsupported modalities."""
    models = FakeGeminiModels(
        response=FakeGeminiResponse("unused"),
    )
    adapter = GeminiNativeAdapter(
        client=FakeGeminiClient(models),
    )

    with pytest.raises(
        ValueError,
        match="supports TEXT modality only",
    ):
        await adapter.generate(
            make_request(
                modality=ModelModality.IMAGE,
            ),
            model="gemini-test-model",
        )


@pytest.mark.asyncio
async def test_generate_rejects_empty_text_response() -> None:
    """Adapter fails closed when Gemini provides no text."""
    models = FakeGeminiModels(
        response=FakeGeminiResponse("   "),
    )
    adapter = GeminiNativeAdapter(
        client=FakeGeminiClient(models),
    )

    with pytest.raises(
        RuntimeError,
        match="contained no text content",
    ):
        await adapter.generate(
            make_request(),
            model="gemini-test-model",
        )


@pytest.mark.asyncio
async def test_generate_propagates_provider_error() -> None:
    """Provider failures remain visible to the upper model-access layer."""
    provider_error = RuntimeError("provider failure")

    models = FakeGeminiModels(
        error=provider_error,
    )
    adapter = GeminiNativeAdapter(
        client=FakeGeminiClient(models),
    )

    with pytest.raises(RuntimeError, match="provider failure"):
        await adapter.generate(
            make_request(),
            model="gemini-test-model",
        )


@pytest.mark.asyncio
async def test_generate_enforces_runtime_budget() -> None:
    """Adapter enforces the request runtime budget."""
    models = FakeGeminiModels(
        response=FakeGeminiResponse("late response"),
        delay_seconds=0.2,
    )
    adapter = GeminiNativeAdapter(
        client=FakeGeminiClient(models),
    )

    request = make_request(
        budget=ModelBudget(
            max_runtime_seconds=0.01,
            max_cost_units=1.0,
            max_output_tokens=100,
        ),
    )

    with pytest.raises(
        TimeoutError,
        match="Gemini request timed out",
    ):
        await adapter.generate(
            request,
            model="gemini-test-model",
        )