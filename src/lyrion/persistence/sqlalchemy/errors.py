"""Errors raised by durable persistence adapters."""

from __future__ import annotations


class PersistenceConflictError(ValueError):
    """Raised when an optimistic-concurrency transition loses its race."""
