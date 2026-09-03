"""Tests for the Cognitive Runtime composition boundary."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lyrion.cognition.composition import build_model_backed_cognitive_runtime
from lyrion.cognition.contracts import (
    CognitiveConstraints,
    CognitiveRequestStatus,
    ReasonRequest,
)
from lyrion.core.types import ExecutionTarget
from lyrion.models.adapters import AdapterKind
from lyrion.models.contracts import (
    ModelCapability,
    ModelModality,
    ModelRequest,
    ModelResponse,
)
from lyrion.models.registry import ModelRegistry, RegisteredModel
from lyrion.models.router import ModelDescriptor

BASE_TIME = datetime(2026, 9, 2, 10, 0, tzinfo=UTC)


class FakeAdapter:
    """Deterministic model adapter for composition tests."""

    adapter_id = "fake-composition"
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

    async def generate(
        self,
        request: ModelRequest,
        *,
        model: str,
    ) -> ModelResponse:
        self.calls.append((request.request_id, model))
        return ModelResponse(
            request_id=request.request_id,
            content="composition response",
            provider=self.provider_name,
            model=model,
            execution_target=ExecutionTarget.CLOUD_API,
            confidence=0.91,
            created_at=BASE_TIME,
        )


def make_registry() -> tuple[ModelRegistry, FakeAdapter]:
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
        reliability_score=0.95,
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
    return registry, adapter


def make_request() -> ReasonRequest:
    return ReasonRequest(
        request_id="reason:composition:001",
        objective="Evaluate the composed model runtime.",
        context_refs=("context:composition",),
        evidence_refs=("evidence:composition",),
        constraints=CognitiveConstraints(require_verification=True),
        created_at=BASE_TIME,
    )


@pytest.mark.asyncio
async def test_composition_builds_full_model_backed_runtime() -> None:
    registry, adapter = make_registry()
    runtime = build_model_backed_cognitive_runtime(registry=registry)

    result = await runtime.reason(make_request())

    assert result.status is CognitiveRequestStatus.COMPLETED
    assert result.answer == "composition response"
    assert result.provider == "fake"
    assert result.model == "fake-model"
    assert result.confidence == pytest.approx(0.91)
    assert result.verification_required is True
    assert adapter.calls == [(
        "reason:composition:001",
        "fake-model",
    )]


def test_composition_rejects_empty_registry() -> None:
    registry = ModelRegistry()

    with pytest.raises(ValueError, match="at least one model"):
        build_model_backed_cognitive_runtime(registry=registry)
