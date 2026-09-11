"""Deterministic provider-neutral model routing."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

from lyrion.models.contracts import ModelCapability, ModelModality, ModelRequest
from lyrion.models.failure_state import ModelTarget


@dataclass(frozen=True)
class ModelDescriptor:
    """Describe one model available to the Model Fabric."""

    provider: str
    model: str
    capabilities: frozenset[ModelCapability]
    modalities: frozenset[ModelModality]
    execution_target_name: str
    reasoning_quality: float = 0.0
    latency_score: float = 0.0
    cost_score: float = 0.0
    reliability_score: float = 0.0
    health_score: float = 1.0
    privacy_safe: bool = False
    network_required: bool = True
    available: bool = True

    def __post_init__(self) -> None:
        """Validate descriptor boundaries."""
        if not self.provider.strip():
            raise ValueError("provider must not be empty")
        if not self.model.strip():
            raise ValueError("model must not be empty")
        if not self.execution_target_name.strip():
            raise ValueError("execution_target_name must not be empty")
        for field_name in (
            "reasoning_quality",
            "latency_score",
            "cost_score",
            "reliability_score",
            "health_score",
        ):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0.0 and 1.0")


@dataclass(frozen=True)
class ModelSelection:
    """Immutable result of deterministic model selection."""

    provider: str
    model: str
    execution_target_name: str

    def target(self) -> ModelTarget:
        """Return the stable failure-tracking target identity."""
        return ModelTarget(
            provider=self.provider,
            model=self.model,
            execution_target_name=self.execution_target_name,
        )


class ModelRoutingError(RuntimeError):
    """Raised when no compatible model can satisfy a request."""


class ModelRouter:
    """Select a compatible model deterministically."""

    def __init__(
        self,
        models: tuple[ModelDescriptor, ...],
    ) -> None:
        """Initialize the router with an immutable model registry."""
        self._models = models

    @property
    def models(self) -> tuple[ModelDescriptor, ...]:
        """Return the registered model descriptors."""
        return self._models

    def route(
        self,
        request: ModelRequest,
        *,
        excluded_targets: Collection[ModelTarget] = (),
    ) -> ModelSelection:
        """Select the best compatible model excluding failed targets."""
        excluded = frozenset(excluded_targets)
        candidates = tuple(
            model
            for model in self._models
            if self._is_compatible(model, request)
            and ModelTarget(
                provider=model.provider,
                model=model.model,
                execution_target_name=model.execution_target_name,
            ) not in excluded
        )

        if not candidates:
            raise ModelRoutingError(
                "no compatible model is available for request",
            )

        selected = max(
            candidates,
            key=lambda model: self._score(model, request),
        )

        return ModelSelection(
            provider=selected.provider,
            model=selected.model,
            execution_target_name=selected.execution_target_name,
        )

    @staticmethod
    def _is_compatible(
        model: ModelDescriptor,
        request: ModelRequest,
    ) -> bool:
        """Apply hard routing constraints."""
        if not model.available:
            return False
        if request.modality not in model.modalities:
            return False
        if not frozenset(request.required_capabilities).issubset(model.capabilities):
            return False
        if request.privacy_required and not model.privacy_safe:
            return False
        if request.network_required and not model.network_required:
            return False
        if (
            model.execution_target_name not in {
                target.value for target in request.preferred_targets
            }
            and request.preferred_targets
        ):
            return False
        if model.health_score <= 0.0:
            return False
        return True

    @staticmethod
    def _score(
        model: ModelDescriptor,
        request: ModelRequest,
    ) -> tuple[float, float, float, float, float, float, str, str]:
        """Build a deterministic routing score."""
        reasoning_fit = 1.0 - abs(
            model.reasoning_quality - request.reasoning_difficulty,
        )
        weighted_score = (
            reasoning_fit * 0.30
            + model.reliability_score * 0.20
            + model.health_score * 0.20
            + model.latency_score * 0.10
            + model.cost_score * 0.10
            + float(
                model.privacy_safe == request.privacy_required,
            ) * 0.10
        )
        return (
            weighted_score,
            reasoning_fit,
            model.reliability_score,
            model.health_score,
            model.latency_score,
            model.cost_score,
            model.provider,
            model.model,
        )
