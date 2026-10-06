"""Bounded agent lifecycle state machine."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class AgentLifecycleState(StrEnum):
    """Authoritative runtime lifecycle states.

    These states describe coordination/execution lifecycle only.
    They are not security authorization states.
    """

    REGISTERED = "registered"
    READY = "ready"
    ASSIGNED = "assigned"
    ADMITTED = "admitted"
    RUNNING = "running"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"
    RECOVERABLE = "recoverable"
    RECOVERING = "recovering"
    QUARANTINED = "quarantined"


class AgentLifecycle(BaseModel):
    """Immutable lifecycle transition result/state."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
    )

    state: AgentLifecycleState

    @staticmethod
    def allowed_transitions() -> dict[
        AgentLifecycleState,
        frozenset[AgentLifecycleState],
    ]:
        return {
            AgentLifecycleState.REGISTERED: frozenset(
                {
                    AgentLifecycleState.READY,
                    AgentLifecycleState.QUARANTINED,
                }
            ),
            AgentLifecycleState.READY: frozenset(
                {
                    AgentLifecycleState.ASSIGNED,
                    AgentLifecycleState.QUARANTINED,
                }
            ),
            AgentLifecycleState.ASSIGNED: frozenset(
                {
                    AgentLifecycleState.ADMITTED,
                    AgentLifecycleState.CANCELLING,
                    AgentLifecycleState.QUARANTINED,
                }
            ),
            AgentLifecycleState.ADMITTED: frozenset(
                {
                    AgentLifecycleState.RUNNING,
                    AgentLifecycleState.CANCELLING,
                    AgentLifecycleState.QUARANTINED,
                }
            ),
            AgentLifecycleState.RUNNING: frozenset(
                {
                    AgentLifecycleState.COMPLETED,
                    AgentLifecycleState.FAILED,
                    AgentLifecycleState.RECOVERABLE,
                    AgentLifecycleState.CANCELLING,
                    AgentLifecycleState.QUARANTINED,
                }
            ),
            AgentLifecycleState.CANCELLING: frozenset(
                {
                    AgentLifecycleState.CANCELLED,
                    AgentLifecycleState.FAILED,
                    AgentLifecycleState.QUARANTINED,
                }
            ),
            AgentLifecycleState.RECOVERABLE: frozenset(
                {
                    AgentLifecycleState.RECOVERING,
                    AgentLifecycleState.QUARANTINED,
                }
            ),
            AgentLifecycleState.RECOVERING: frozenset(
                {
                    AgentLifecycleState.ASSIGNED,
                    AgentLifecycleState.QUARANTINED,
                    AgentLifecycleState.FAILED,
                }
            ),
            AgentLifecycleState.COMPLETED: frozenset(),
            AgentLifecycleState.CANCELLED: frozenset(),
            AgentLifecycleState.FAILED: frozenset(),
            AgentLifecycleState.QUARANTINED: frozenset(),
        }

    def can_transition_to(self, target: AgentLifecycleState) -> bool:
        """Return whether the requested lifecycle transition is allowed."""
        return target in self.allowed_transitions().get(self.state, frozenset())

    def transition(self, target: AgentLifecycleState) -> AgentLifecycle:
        """Return a new lifecycle state or reject the transition."""
        if not self.can_transition_to(target):
            raise ValueError(
                f"invalid agent lifecycle transition: "
                f"{self.state.value} -> {target.value}"
            )

        return AgentLifecycle(state=target)
