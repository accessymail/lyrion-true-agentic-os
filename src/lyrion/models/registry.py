"""Model registry metadata for Lyrion's Model Fabric."""

from __future__ import annotations

from dataclasses import dataclass

from lyrion.models.adapters import AdapterKind, ModelAccessAdapter
from lyrion.models.router import ModelDescriptor


@dataclass(frozen=True)
class RegisteredModel:
    """Immutable registry entry connecting metadata to an adapter."""

    descriptor: ModelDescriptor
    adapter_id: str
    kind: AdapterKind


class ModelRegistry:
    """Register and resolve model metadata without provider coupling."""

    def __init__(
        self,
        *,
        adapters: tuple[ModelAccessAdapter, ...] = (),
        models: tuple[RegisteredModel, ...] = (),
    ) -> None:
        """Initialize the registry with immutable bootstrap entries."""
        self._adapters: dict[str, ModelAccessAdapter] = {}
        self._models: dict[tuple[str, str], RegisteredModel] = {}

        for adapter in adapters:
            self.register_adapter(adapter)

        for model in models:
            self.register_model(model)

    @property
    def adapters(self) -> tuple[ModelAccessAdapter, ...]:
        """Return adapters in deterministic identifier order."""
        return tuple(
            self._adapters[key]
            for key in sorted(self._adapters)
        )

    @property
    def models(self) -> tuple[RegisteredModel, ...]:
        """Return registered models in deterministic provider/model order."""
        return tuple(
            self._models[key]
            for key in sorted(self._models)
        )

    def register_adapter(
        self,
        adapter: ModelAccessAdapter,
    ) -> None:
        """Register one adapter under a unique stable identifier."""
        adapter_id = adapter.adapter_id.strip()

        if not adapter_id:
            raise ValueError("adapter_id must not be empty")

        if adapter_id in self._adapters:
            raise ValueError(
                f"adapter already registered: {adapter_id}",
            )

        self._adapters[adapter_id] = adapter

    def register_model(
        self,
        registered_model: RegisteredModel,
    ) -> None:
        """Register one model bound to an existing adapter."""
        key = (
            registered_model.descriptor.provider,
            registered_model.descriptor.model,
        )

        if registered_model.adapter_id not in self._adapters:
            raise ValueError(
                "model references an unregistered adapter",
            )

        if registered_model.kind is not self._adapters[
            registered_model.adapter_id
        ].kind:
            raise ValueError(
                "model adapter kind does not match registered adapter",
            )

        if key in self._models:
            raise ValueError(
                f"model already registered: "
                f"{key[0]}/{key[1]}",
            )

        self._models[key] = registered_model

    def resolve(
        self,
        *,
        provider: str,
        model: str,
    ) -> RegisteredModel:
        """Resolve one model registration."""
        key = (provider, model)

        try:
            return self._models[key]
        except KeyError as exc:
            raise KeyError(
                f"model not registered: {provider}/{model}",
            ) from exc

    def resolve_adapter(
        self,
        adapter_id: str,
    ) -> ModelAccessAdapter:
        """Resolve one adapter by stable identifier."""
        try:
            return self._adapters[adapter_id]
        except KeyError as exc:
            raise KeyError(
                f"adapter not registered: {adapter_id}",
            ) from exc
