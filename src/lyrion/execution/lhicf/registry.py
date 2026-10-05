"""Controlled LHICF adapter registry and deterministic selector."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .contracts import (
    AdapterLifecycleState,
    AdapterRegistration,
)


class AdapterSelectionError(RuntimeError):
    """Raised when adapter selection cannot safely produce one adapter."""


@dataclass(frozen=True, slots=True)
class AdapterRegistry:
    """Immutable registry snapshot.

    Registration is treated as configuration, not authority.
    """

    _adapters: tuple[AdapterRegistration, ...]

    @classmethod
    def from_adapters(
        cls,
        adapters: Iterable[AdapterRegistration],
    ) -> AdapterRegistry:
        ordered = tuple(adapters)

        ids = [adapter.adapter_id for adapter in ordered]

        if len(ids) != len(set(ids)):
            raise ValueError("duplicate adapter_id detected")

        if ids != sorted(ids):
            raise ValueError(
                "adapter registrations must be deterministically sorted"
            )

        for adapter in ordered:
            if adapter.lifecycle_state is AdapterLifecycleState.REVOKED:
                continue

            if adapter.lifecycle_state not in {
                AdapterLifecycleState.VALIDATED,
                AdapterLifecycleState.REGISTERED,
                AdapterLifecycleState.AVAILABLE,
            }:
                raise ValueError(
                    f"adapter {adapter.adapter_id!r} is not registered/validated"
                )

        return cls(_adapters=ordered)

    @property
    def adapters(self) -> tuple[AdapterRegistration, ...]:
        return self._adapters

    def select(
        self,
        *,
        adapter_id: str,
        operation: str,
        target_scope: str,
        host_capabilities: Iterable[str] = (),
        host_qualification: Iterable[str] = (),
    ) -> AdapterRegistration:
        """Select exactly one adapter.

        Determinism is mandatory. Unknown, revoked, unsupported, or ambiguous
        selection fails closed.
        """

        if not adapter_id.strip():
            raise AdapterSelectionError("adapter_id is required")

        if not operation.strip():
            raise AdapterSelectionError("operation is required")

        if not target_scope.strip():
            raise AdapterSelectionError("target_scope is required")

        normalized_operation = operation.strip().upper()

        available_host_capabilities = frozenset(
            capability.strip()
            for capability in host_capabilities
            if capability.strip()
        )
        available_host_qualification = frozenset(
            qualification.strip()
            for qualification in host_qualification
            if qualification.strip()
        )

        candidates = tuple(
            adapter
            for adapter in self._adapters
            if adapter.adapter_id == adapter_id
            and adapter.lifecycle_state is AdapterLifecycleState.AVAILABLE
            and normalized_operation in adapter.supported_operations
            and target_scope in adapter.supported_target_scopes
            and adapter.required_host_capabilities.issubset(
                available_host_capabilities
            )
            and adapter.required_host_qualification.issubset(
                available_host_qualification
            )
        )

        if not candidates:
            raise AdapterSelectionError(
                "no available adapter satisfies the requested operation "
                "and target scope"
            )

        if len(candidates) != 1:
            raise AdapterSelectionError(
                "ambiguous adapter selection; boundary is fail-closed"
            )

        return candidates[0]
