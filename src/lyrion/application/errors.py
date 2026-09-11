"""Safe Application Runtime error normalization."""

from __future__ import annotations

from lyrion.application.contracts import (
    ApplicationCorrelationError,
    ApplicationRuntimeError,
    ApplicationSessionError,
    ApplicationTurnError,
)


def public_error_code(error: Exception) -> str:
    """Return a stable, non-sensitive public application error code."""

    if isinstance(error, ApplicationCorrelationError):
        return "INVALID_CORRELATION"

    if isinstance(error, ApplicationSessionError):
        return "INVALID_SESSION"

    if isinstance(error, ApplicationTurnError):
        return "INVALID_TURN"

    if isinstance(error, ApplicationRuntimeError):
        return "APPLICATION_ERROR"

    return "APPLICATION_ERROR"
