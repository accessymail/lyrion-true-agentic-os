"""Provider-neutral Model Gateway interface."""

from __future__ import annotations

from typing import Protocol

from lyrion.models.contracts import ModelRequest, ModelResponse


class ModelGateway(Protocol):
    """Abstract boundary for provider-neutral model access."""

    async def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        """Generate one bounded model response."""
