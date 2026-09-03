"""Google Gemini model registrations for Lyrion's Model Fabric."""

from __future__ import annotations

from lyrion.core.types import ExecutionTarget
from lyrion.models.adapters import ModelAccessAdapter
from lyrion.models.contracts import ModelCapability, ModelModality
from lyrion.models.providers.google_gemini import GeminiClient, GeminiNativeAdapter
from lyrion.models.registry import ModelRegistry, RegisteredModel
from lyrion.models.router import ModelDescriptor

GEMINI_3_7_FLASH = "gemini-3.7-flash"
GEMINI_ADAPTER_ID = "google-gemini-native"


def create_gemini_registry(
    *,
    client: GeminiClient | None = None,
) -> ModelRegistry:
    """Create a registry containing the canonical Gemini model."""
    adapter: ModelAccessAdapter = GeminiNativeAdapter(
        client=client,
    )

    descriptor = ModelDescriptor(
        provider="google",
        model=GEMINI_3_7_FLASH,
        capabilities=frozenset(
            {
                ModelCapability.GENERATION,
                ModelCapability.REASONING,
                ModelCapability.PLANNING,
            },
        ),
        modalities=frozenset(
            {
                ModelModality.TEXT,
            },
        ),
        execution_target_name=ExecutionTarget.CLOUD_API.value,
        reasoning_quality=0.90,
        latency_score=0.80,
        cost_score=0.60,
        reliability_score=0.90,
        health_score=1.0,
        privacy_safe=False,
        network_required=True,
        available=True,
    )

    registered_model = RegisteredModel(
        descriptor=descriptor,
        adapter_id=adapter.adapter_id,
        kind=adapter.kind,
    )

    return ModelRegistry(
        adapters=(adapter,),
        models=(registered_model,),
    )
