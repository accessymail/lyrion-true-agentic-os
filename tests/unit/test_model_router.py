"""Adversarial tests for deterministic model routing."""

from datetime import UTC, datetime

import pytest

from lyrion.core.types import ExecutionTarget, RiskLevel
from lyrion.models.contracts import (
    ModelCapability,
    ModelModality,
    ModelRequest,
)
from lyrion.models.router import (
    ModelDescriptor,
    ModelRouter,
    ModelRoutingError,
)


def make_request(
    *,
    required_capabilities: tuple[ModelCapability, ...] = (),
    modality: ModelModality = ModelModality.TEXT,
    reasoning_difficulty: float = 0.0,
    privacy_required: bool = False,
    network_required: bool = False,
    preferred_targets: tuple[ExecutionTarget, ...] = (),
) -> ModelRequest:
    """Build a valid routing request."""
    return ModelRequest(
        request_id="route:test",
        objective="Select a suitable model.",
        required_capabilities=required_capabilities,
        modality=modality,
        reasoning_difficulty=reasoning_difficulty,
        risk_level=RiskLevel.LOW,
        privacy_required=privacy_required,
        network_required=network_required,
        preferred_targets=preferred_targets,
        created_at=datetime.now(UTC),
    )


def make_model(
    *,
    provider: str = "provider-a",
    model: str = "model-a",
    capabilities: frozenset[ModelCapability] = frozenset(
        {ModelCapability.GENERATION},
    ),
    modalities: frozenset[ModelModality] = frozenset(
        {ModelModality.TEXT},
    ),
    execution_target_name: str = ExecutionTarget.CLOUD_API.value,
    reasoning_quality: float = 0.5,
    latency_score: float = 0.5,
    cost_score: float = 0.5,
    reliability_score: float = 0.5,
    health_score: float = 1.0,
    privacy_safe: bool = False,
    network_required: bool = True,
    available: bool = True,
) -> ModelDescriptor:
    """Build a valid model descriptor."""
    return ModelDescriptor(
        provider=provider,
        model=model,
        capabilities=capabilities,
        modalities=modalities,
        execution_target_name=execution_target_name,
        reasoning_quality=reasoning_quality,
        latency_score=latency_score,
        cost_score=cost_score,
        reliability_score=reliability_score,
        health_score=health_score,
        privacy_safe=privacy_safe,
        network_required=network_required,
        available=available,
    )


def test_selects_compatible_model() -> None:
    """A compatible model should be selected."""
    router = ModelRouter(
        (
            make_model(
                capabilities=frozenset(
                    {
                        ModelCapability.GENERATION,
                        ModelCapability.REASONING,
                    }
                ),
            ),
        )
    )

    selection = router.route(
        make_request(
            required_capabilities=(
                ModelCapability.REASONING,
            ),
        )
    )

    assert selection.provider == "provider-a"
    assert selection.model == "model-a"


def test_rejects_wrong_modality() -> None:
    """Unsupported modality must fail closed."""
    router = ModelRouter(
        (
            make_model(
                modalities=frozenset(
                    {ModelModality.TEXT},
                ),
            ),
        )
    )

    with pytest.raises(ModelRoutingError):
        router.route(
            make_request(
                modality=ModelModality.IMAGE,
            )
        )


def test_rejects_missing_capability() -> None:
    """Missing required capability must fail closed."""
    router = ModelRouter(
        (
            make_model(
                capabilities=frozenset(
                    {ModelCapability.GENERATION},
                ),
            ),
        )
    )

    with pytest.raises(ModelRoutingError):
        router.route(
            make_request(
                required_capabilities=(
                    ModelCapability.REASONING,
                ),
            )
        )


def test_rejects_privacy_unsafe_model() -> None:
    """Privacy-sensitive requests require privacy-safe models."""
    router = ModelRouter(
        (
            make_model(
                privacy_safe=False,
            ),
        )
    )

    with pytest.raises(ModelRoutingError):
        router.route(
            make_request(
                privacy_required=True,
            )
        )


def test_respects_preferred_execution_target() -> None:
    """Preferred execution targets act as hard constraints."""
    router = ModelRouter(
        (
            make_model(
                execution_target_name=ExecutionTarget.CLOUD_API.value,
            ),
            make_model(
                provider="provider-b",
                model="model-b",
                execution_target_name=ExecutionTarget.CLOUD_GPU.value,
            ),
        )
    )

    selection = router.route(
        make_request(
            preferred_targets=(ExecutionTarget.CLOUD_GPU,),
        )
    )

    assert selection.provider == "provider-b"
    assert selection.model == "model-b"


def test_unavailable_model_is_excluded() -> None:
    """Unavailable models must never be selected."""
    router = ModelRouter(
        (
            make_model(
                available=False,
            ),
        )
    )

    with pytest.raises(ModelRoutingError):
        router.route(make_request())


def test_reasoning_difficulty_influences_selection() -> None:
    """Reasoning difficulty should favor better reasoning quality."""
    router = ModelRouter(
        (
            make_model(
                provider="provider-a",
                model="basic",
                reasoning_quality=0.2,
                reliability_score=0.5,
            ),
            make_model(
                provider="provider-b",
                model="reasoning",
                reasoning_quality=0.9,
                reliability_score=0.5,
            ),
        )
    )

    selection = router.route(
        make_request(
            reasoning_difficulty=0.9,
        )
    )

    assert selection.provider == "provider-b"
    assert selection.model == "reasoning"


def test_selection_is_deterministic() -> None:
    """Repeated routing of the same request must be stable."""
    router = ModelRouter(
        (
            make_model(
                provider="provider-b",
                model="model-b",
            ),
            make_model(
                provider="provider-a",
                model="model-a",
            ),
        )
    )

    request = make_request(
        reasoning_difficulty=0.5,
    )

    first = router.route(request)
    second = router.route(request)

    assert first == second
