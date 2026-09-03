"""Native Google Gemini adapter for Lyrion's Model Access Layer."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Protocol

from google import genai
from google.genai import types

from lyrion.core.types import ExecutionTarget
from lyrion.models.adapters import AdapterKind
from lyrion.models.contracts import (
    ModelCapability,
    ModelModality,
    ModelRequest,
    ModelResponse,
)


class GeminiModelsClient(Protocol):
    """Minimal async Gemini models client surface required by the adapter."""

    async def generate_content(
        self,
        *,
        model: str,
        contents: str,
        config: types.GenerateContentConfig,
    ) -> object:
        """Generate content asynchronously."""


class GeminiAsyncClient(Protocol):
    """Minimal async Gemini client surface required by the adapter."""

    @property
    def models(self) -> GeminiModelsClient:
        """Return the async models client."""


class GeminiClient(Protocol):
    """Minimal Gemini client surface required by the adapter."""

    @property
    def aio(self) -> GeminiAsyncClient:
        """Return the asynchronous client."""


class GeminiNativeAdapter:
    """Native Google Gemini implementation of Lyrion's model-access contract."""

    ADAPTER_ID = "google-gemini-native"
    PROVIDER_NAME = "google"
    PROTOCOL = "gemini-native"

    def __init__(
        self,
        client: GeminiClient | None = None,
    ) -> None:
        """Initialize the Gemini adapter."""
        self._client = client if client is not None else genai.Client()

    @property
    def adapter_id(self) -> str:
        """Return the stable adapter identifier."""
        return self.ADAPTER_ID

    @property
    def kind(self) -> AdapterKind:
        """Return the adapter classification."""
        return AdapterKind.NATIVE_PROVIDER

    @property
    def provider_name(self) -> str:
        """Return the provider identity."""
        return self.PROVIDER_NAME

    @property
    def protocol(self) -> str:
        """Return the native protocol identity."""
        return self.PROTOCOL

    def supports_capability(
        self,
        capability: ModelCapability,
    ) -> bool:
        """Return whether the adapter supports the capability."""
        return capability in {
            ModelCapability.GENERATION,
            ModelCapability.REASONING,
            ModelCapability.PLANNING,
        }

    def supports_modality(
        self,
        modality: ModelModality,
    ) -> bool:
        """Return whether the adapter currently supports the modality."""
        return modality is ModelModality.TEXT

    async def generate(
        self,
        request: ModelRequest,
        *,
        model: str,
    ) -> ModelResponse:
        """Generate one bounded text response through native Gemini."""
        normalized_model = model.strip()

        if not normalized_model:
            raise ValueError("model must not be empty")

        if request.modality is not ModelModality.TEXT:
            raise ValueError(
                "GeminiNativeAdapter currently supports TEXT modality only",
            )

        config = types.GenerateContentConfig(
            max_output_tokens=request.budget.max_output_tokens,
        )

        try:
            response = await asyncio.wait_for(
                self._generate(
                    model=normalized_model,
                    contents=request.objective,
                    config=config,
                ),
                timeout=request.budget.max_runtime_seconds,
            )
        except TimeoutError as exc:
            raise TimeoutError(
                "Gemini request timed out after "
                f"{request.budget.max_runtime_seconds} seconds",
            ) from exc

        content = getattr(response, "text", None)

        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(
                "Gemini response contained no text content",
            )

        return ModelResponse(
            request_id=request.request_id,
            content=content.strip(),
            provider=self.PROVIDER_NAME,
            model=normalized_model,
            execution_target=ExecutionTarget.CLOUD_API,
            confidence=0.0,
            created_at=datetime.now(UTC),
        )

    async def _generate(
        self,
        *,
        model: str,
        contents: str,
        config: types.GenerateContentConfig,
    ) -> object:
        """Call Gemini's native asynchronous generation API."""
        return await self._client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )