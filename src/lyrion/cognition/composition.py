"""Composition helpers for Lyrions cognitive runtime."""

from __future__ import annotations

from lyrion.cognition.model_backed_runtime import ModelBackedCognitiveRuntime
from lyrion.models.registry import ModelRegistry
from lyrion.models.resilience import FailoverModelGateway, ModelRetryPolicy
from lyrion.models.router import ModelRouter
from lyrion.models.runtime import build_model_gateway


def build_model_backed_cognitive_runtime(
    *,
    registry: ModelRegistry,
    retry_policy: ModelRetryPolicy | None = None,
) -> ModelBackedCognitiveRuntime:
    """Build the provider-neutral model-backed cognitive runtime."""
    registered_models = registry.models

    if not registered_models:
        raise ValueError("model registry must contain at least one model")

    router = ModelRouter(
        tuple(model.descriptor for model in registered_models),
    )
    routed_gateway = build_model_gateway(
        router=router,
        registry=registry,
    )
    gateway = FailoverModelGateway(
        delegate=routed_gateway,
        router=router,
        policy=retry_policy,
    )

    return ModelBackedCognitiveRuntime(gateway=gateway)
