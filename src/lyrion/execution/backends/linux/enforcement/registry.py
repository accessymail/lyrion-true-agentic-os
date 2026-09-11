from __future__ import annotations

from collections.abc import Iterable
from types import MappingProxyType

from lyrion.execution.backends.linux.enforcement.adapter import PrimitiveAdapter
from lyrion.execution.backends.linux.enforcement.contracts import (
    EnforcementPrimitive,
)


class PrimitiveAdapterRegistry:
    """
    Deterministic registry for Linux enforcement primitive adapters.

    The registry is intentionally explicit. Adapters are registered by the
    trusted application code and are resolved only by EnforcementPrimitive.

    No dynamic module loading, reflection-based discovery, or untrusted
    adapter registration is performed here.
    """

    def __init__(self, adapters: Iterable[PrimitiveAdapter] = ()) -> None:
        mapping: dict[EnforcementPrimitive, PrimitiveAdapter] = {}

        for adapter in adapters:
            primitive = adapter.primitive

            if primitive in mapping:
                raise ValueError(
                    f"Duplicate primitive adapter registration: {primitive.value}"
                )

            mapping[primitive] = adapter

        self._adapters = MappingProxyType(mapping)

    def resolve(self, primitive: EnforcementPrimitive) -> PrimitiveAdapter:
        """Resolve the trusted adapter for a primitive."""
        try:
            return self._adapters[primitive]
        except KeyError as exc:
            raise KeyError(
                f"No adapter registered for primitive: {primitive.value}"
            ) from exc

    def contains(self, primitive: EnforcementPrimitive) -> bool:
        """Return whether an adapter is registered for the primitive."""
        return primitive in self._adapters

    def identifiers(self) -> tuple[EnforcementPrimitive, ...]:
        """Return registered primitives in deterministic enum order."""
        registered = set(self._adapters)
        return tuple(
            primitive
            for primitive in EnforcementPrimitive
            if primitive in registered
        )

    def __len__(self) -> int:
        return len(self._adapters)
