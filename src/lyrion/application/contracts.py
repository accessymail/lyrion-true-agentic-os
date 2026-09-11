"""Internal contracts for the Lyrion Application Runtime Boundary.

These contracts carry authenticated application identity, session binding,
correlation lineage, and turn lineage only. They never grant capability or
execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

_MAX_ID_LENGTH = 200
_MAX_AUTH_METHOD_LENGTH = 100


def _require_text(value: str, *, field: str, max_length: int = _MAX_ID_LENGTH) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")

    resolved = value.strip()

    if not resolved:
        raise ValueError(f"{field} must not be empty")

    if len(resolved) > max_length:
        raise ValueError(f"{field} exceeds maximum length")

    return resolved


def _require_timezone_aware(value: datetime, *, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value


@dataclass(frozen=True, slots=True)
class ApplicationPrincipalContext:
    """Validated application principal established by an authentication adapter."""

    principal_id: str
    authentication_method: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "principal_id",
            _require_text(
                self.principal_id,
                field="principal_id",
            ),
        )
        object.__setattr__(
            self,
            "authentication_method",
            _require_text(
                self.authentication_method,
                field="authentication_method",
                max_length=_MAX_AUTH_METHOD_LENGTH,
            ),
        )


@dataclass(frozen=True, slots=True)
class ApplicationSessionContext:
    """Validated application-session binding."""

    application_session_id: str
    principal_id: str
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "application_session_id",
            _require_text(
                self.application_session_id,
                field="application_session_id",
            ),
        )
        object.__setattr__(
            self,
            "principal_id",
            _require_text(
                self.principal_id,
                field="principal_id",
            ),
        )
        object.__setattr__(
            self,
            "created_at",
            _require_timezone_aware(
                self.created_at,
                field="created_at",
            ),
        )


@dataclass(frozen=True, slots=True)
class ApplicationCorrelationContext:
    """Immutable request/interaction lineage metadata."""

    correlation_id: str
    application_session_id: str
    voice_session_id: str | None = None
    interaction_id: str | None = None
    turn_id: str | None = None
    request_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "correlation_id",
            _require_text(
                self.correlation_id,
                field="correlation_id",
            ),
        )
        object.__setattr__(
            self,
            "application_session_id",
            _require_text(
                self.application_session_id,
                field="application_session_id",
            ),
        )

        for field in (
            "voice_session_id",
            "interaction_id",
            "turn_id",
            "request_id",
        ):
            value = getattr(self, field)

            if value is not None:
                object.__setattr__(
                    self,
                    field,
                    _require_text(
                        value,
                        field=field,
                    ),
                )


@dataclass(frozen=True, slots=True)
class ApplicationTurnContext:
    """Immutable application-level turn lineage.

    This context identifies a turn but grants no execution authority.
    """

    application_session_id: str
    turn_id: str
    correlation_id: str
    request_id: str
    sequence: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "application_session_id",
            _require_text(
                self.application_session_id,
                field="application_session_id",
            ),
        )
        object.__setattr__(
            self,
            "turn_id",
            _require_text(
                self.turn_id,
                field="turn_id",
            ),
        )
        object.__setattr__(
            self,
            "correlation_id",
            _require_text(
                self.correlation_id,
                field="correlation_id",
            ),
        )
        object.__setattr__(
            self,
            "request_id",
            _require_text(
                self.request_id,
                field="request_id",
            ),
        )

        if not isinstance(self.sequence, int):
            raise ValueError("sequence must be an integer")

        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")


class ApplicationRuntimeError(Exception):
    """Base error for application-boundary failures."""


class ApplicationSessionError(ApplicationRuntimeError):
    """Session lifecycle or ownership failure."""


class ApplicationCorrelationError(ApplicationRuntimeError):
    """Correlation or lineage validation failure."""


class ApplicationTurnError(ApplicationRuntimeError):
    """Application turn lineage validation failure."""
