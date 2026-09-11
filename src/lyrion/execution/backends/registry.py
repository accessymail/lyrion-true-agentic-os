"""Execution backend registry."""

from __future__ import annotations

from collections.abc import Iterable

from lyrion.execution.backends.contracts import ExecutionBackend


class ExecutionBackendRegistry:
    """Explicit registry for execution backends.

    Backend selection is infrastructure behavior. Authorization remains
    owned by the existing LYRION security/control plane.
    """

    def __init__(self, backends: Iterable[ExecutionBackend] = ()) -> None:
        self._backends: dict[str, ExecutionBackend] = {}

        for backend in backends:
            self.register(backend)

    def register(self, backend: ExecutionBackend) -> None:
        """Register a backend and reject duplicate identifiers."""
        backend_id = backend.backend_id.strip()

        if not backend_id:
            raise ValueError("backend_id must not be empty")

        if backend_id in self._backends:
            raise ValueError(
                f"execution backend already registered: {backend_id}"
            )

        self._backends[backend_id] = backend

    def resolve(self, backend_id: str) -> ExecutionBackend:
        """Resolve a backend or fail closed."""
        normalized = backend_id.strip()

        if not normalized:
            raise ValueError("backend_id must not be empty")

        try:
            return self._backends[normalized]
        except KeyError as exc:
            raise LookupError(
                f"execution backend is not registered: {normalized}"
            ) from exc

    def contains(self, backend_id: str) -> bool:
        """Return whether a backend identifier is registered."""
        return backend_id.strip() in self._backends

    def identifiers(self) -> tuple[str, ...]:
        """Return deterministic registered backend identifiers."""
        return tuple(sorted(self._backends))

    def close(self) -> None:
        """Close all registered backends."""
        for backend in self._backends.values():
            backend.close()
