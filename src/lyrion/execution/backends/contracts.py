from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class BackendCapabilityState(StrEnum):
    AVAILABLE = "available"
    AVAILABLE_LIMITED = "available_limited"
    REQUIRES_CONFIGURATION = "requires_configuration"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class BackendCapabilities:
    backend_id: str
    state: BackendCapabilityState
    details: Mapping[str, Any]


class ExecutionBackend(ABC):
    """
    Backend-neutral execution contract.

    Backends provide execution mechanics only. Authorization remains owned
    by the existing Aegis/capability control plane.
    """

    @property
    @abstractmethod
    def backend_id(self) -> str:
        """Return the stable backend identifier."""

    @abstractmethod
    def capabilities(self) -> BackendCapabilities:
        """Return the current backend capability assessment."""

    @abstractmethod
    def prepare(self, *args: Any, **kwargs: Any) -> Any:
        """Prepare execution without launching a process."""

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Execute an already-admitted request."""

    @abstractmethod
    def cleanup(self, *args: Any, **kwargs: Any) -> None:
        """Release backend resources."""

    @abstractmethod
    def close(self) -> None:
        """Release persistent backend resources."""
