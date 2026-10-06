"""Task-to-agent binding contract."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class AgentTaskBinding(BaseModel):
    """Immutable binding between an existing LYRION task and an agent.

    This object records coordination state only.

    It does not:
      * grant authority;
      * grant capabilities;
      * authorize execution;
      * bypass admission;
      * authorize host operations.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
    )

    binding_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    agent_id: UUID
    parent_task_id: UUID | None = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    binding_revision: int = Field(default=1, ge=1)

    # Explicitly descriptive coordination metadata.
    purpose: str = Field(default="task_execution", min_length=1, max_length=128)
