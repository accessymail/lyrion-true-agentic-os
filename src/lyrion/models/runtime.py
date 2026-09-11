"""Runtime Model Gateway implementation for Lyrion."""

from __future__ import annotations

from lyrion.models.contracts import ModelRequest, ModelResponse
from lyrion.models.registry import ModelRegistry
from lyrion.models.router import ModelRouter, ModelSelection


class RoutedModelGateway:
    """Route model requests and invoke the selected access adapter."""

    def __init__(
        self,
        *,
        router: ModelRouter,
        registry: ModelRegistry,
    ) -> None:
        """Initialize the provider-neutral gateway runtime."""
        self._router = router
        self._registry = registry

    @property
    def router(self) -> ModelRouter:
        """Return the configured model router."""
        return self._router

    @property
    def registry(self) -> ModelRegistry:
        """Return the configured model registry."""
        return self._registry

    async def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        """Route and execute one bounded model request."""
        selection = self._router.route(request)

        registered_model = self._registry.resolve(
            provider=selection.provider,
            model=selection.model,
        )
        adapter = self._registry.resolve_adapter(
            registered_model.adapter_id,
        )

        return await adapter.generate(
            request,
            model=registered_model.descriptor.model,
        )



    async def generate_for_selection(
        self,
        request: ModelRequest,
        selection: ModelSelection,
    ) -> ModelResponse:
        registered_model = self._registry.resolve(
            provider=selection.provider,
            model=selection.model,
        )
        adapter = self._registry.resolve_adapter(
            registered_model.adapter_id,
        )
        return await adapter.generate(
            request,
            model=registered_model.descriptor.model,
        )

def build_model_gateway(
    *,
    router: ModelRouter,
    registry: ModelRegistry,
) -> RoutedModelGateway:
    """Build the provider-neutral routed model runtime."""
    return RoutedModelGateway(
        router=router,
        registry=registry,
    )
