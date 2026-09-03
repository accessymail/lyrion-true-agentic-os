"""Provider, protocol, aggregator, and inference adapter contracts for Lyrion."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from lyrion.models.contracts import (
    ModelCapability,
    ModelModality,
    ModelRequest,
    ModelResponse,
)


class AdapterKind(StrEnum):
    """Classification of model-access implementations."""

    NATIVE_PROVIDER = "NATIVE_PROVIDER"
    PROTOCOL_COMPATIBILITY = "PROTOCOL_COMPATIBILITY"
    AGGREGATOR = "AGGREGATOR"
    INFERENCE_RUNTIME = "INFERENCE_RUNTIME"
    SELF_HOSTED = "SELF_HOSTED"


class ModelAccessAdapter(Protocol):
    """Provider-neutral contract for model access."""

    @property
    def adapter_id(self) -> str:
        """Return the stable adapter identifier."""

    @property
    def kind(self) -> AdapterKind:
        """Return the adapter classification."""

    @property
    def provider_name(self) -> str:
        """Return the provider or runtime identity."""

    @property
    def protocol(self) -> str:
        """Return the access protocol identity."""

    def supports_capability(
        self,
        capability: ModelCapability,
    ) -> bool:
        """Return whether the adapter supports a capability."""

    def supports_modality(
        self,
        modality: ModelModality,
    ) -> bool:
        """Return whether the adapter supports a modality."""

    async def generate(
        self,
        request: ModelRequest,
        *,
        model: str,
    ) -> ModelResponse:
        """Generate one bounded model response."""
