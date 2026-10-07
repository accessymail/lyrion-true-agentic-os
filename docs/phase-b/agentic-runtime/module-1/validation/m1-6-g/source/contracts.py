"""Module 1.6-G coordination-plane contracts.

These contracts represent scheduling, routing, resource, communication,
correlation, and provenance state only. They never constitute authorization.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class CoordinationError(ValueError):
    """Raised when a coordination invariant is violated."""


class CoordinationDecision(StrEnum):
    ACCEPTED = "accepted"
    DEFERRED = "deferred"
    REJECTED = "rejected"


class RouteKind(StrEnum):
    AGENT = "agent"
    QUEUE = "queue"


class CoordinationResourceState(StrEnum):
    RESERVED = "reserved"
    RELEASED = "released"


class ScheduleRequest(BaseModel):
    """Immutable scheduling request; scheduling is not authorization."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    request_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    agent_id: UUID
    priority: int = Field(default=0, ge=-1000, le=1000)
    dependencies: tuple[UUID, ...] = ()
    completed_dependencies: frozenset[UUID] = frozenset()
    deadline: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def dependencies_satisfied(self) -> bool:
        return set(self.dependencies).issubset(self.completed_dependencies)


class ScheduleResult(BaseModel):
    """Immutable scheduling outcome without security authority."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    request_id: UUID
    task_id: UUID
    agent_id: UUID
    decision: CoordinationDecision
    reason: str = Field(min_length=1, max_length=256)
    scheduled_at: datetime | None = None


class CoordinationSecurityContext(BaseModel):
    """Immutable references preserved across coordination boundaries.

    These references identify externally governed security context. They never
    authorize, grant capabilities, create admission, or restore authority.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    principal_id: UUID
    delegated_authority_ref: UUID
    capability_ref: UUID
    policy_context_ref: UUID


class RouteRequest(BaseModel):
    """Immutable dispatch-routing request; routing never executes a task."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    request_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    source_agent_id: UUID
    target_id: UUID
    route_kind: RouteKind = RouteKind.AGENT
    correlation_id: UUID
    security_context: CoordinationSecurityContext
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RouteDecision(BaseModel):
    """Immutable routing decision with no admission or execution effect."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    request_id: UUID
    task_id: UUID
    target_id: UUID
    decision: CoordinationDecision
    reason: str = Field(min_length=1, max_length=256)


class ResourceRequest(BaseModel):
    """Coordination-only resource reservation request."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    request_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    agent_id: UUID
    resource: str = Field(min_length=1, max_length=128)
    units: int = Field(gt=0, le=1_000_000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ResourceAllocation(BaseModel):
    """Immutable coordination resource state, not a capability grant."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    allocation_id: UUID = Field(default_factory=uuid4)
    request_id: UUID
    task_id: UUID
    agent_id: UUID
    resource: str
    units: int
    state: CoordinationResourceState


class CoordinationMessage(BaseModel):
    """Immutable inter-agent coordination message envelope."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    message_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    sender_agent_id: UUID
    recipient_agent_id: UUID
    correlation_id: UUID
    sequence: int = Field(ge=1)
    payload_digest: str = Field(min_length=1, max_length=128)
    security_context: CoordinationSecurityContext
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CoordinationEvent(BaseModel):
    """Immutable coordination provenance event."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    event_id: UUID = Field(default_factory=uuid4)
    sequence: int = Field(ge=1)
    event_type: str = Field(min_length=1, max_length=64)
    task_id: UUID
    agent_id: UUID
    correlation_id: UUID
    reason: str = Field(min_length=1, max_length=512)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
