"""Runtime execution-context contract."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class RuntimeExecutionContext(BaseModel):
    """Immutable correlation context for runtime coordination.

    Security invariant:
        This context carries references to authorization/admission state;
        it does not itself create or grant authority.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
    )

    context_id: UUID = Field(default_factory=uuid4)
    correlation_id: UUID = Field(default_factory=uuid4)

    task_id: UUID
    agent_id: UUID

    parent_context_id: UUID | None = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    # These are references/identifiers only.
    # Their existence does not imply validity.
    admission_id: UUID | None = None
    delegated_authority_id: UUID | None = None

    @property
    def has_admission_reference(self) -> bool:
        """Whether an admission reference is attached.

        This does NOT mean that the admission is valid, current,
        authorized, or executable. Validation must occur at the
        security/admission boundary.
        """
        return self.admission_id is not None
