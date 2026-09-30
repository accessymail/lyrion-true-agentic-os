"""Immutable Agent Isolation Contract for PB-DOC-005.

The Agent Isolation Contract defines the boundaries that an individual
agent binding must preserve.

This module does NOT implement OS-level sandboxing, authorization,
capability granting, secret management, or host privilege enforcement.
Those responsibilities remain owned by the existing LYRION security
and execution layers.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AgentIsolationContract(BaseModel):
    """Fail-closed isolation boundary for one attributable agent."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    agent_id: str = Field(min_length=1, max_length=200)
    task_id: str = Field(min_length=1, max_length=500)

    # Isolation boundaries.
    authority_isolated: bool = True
    capability_isolated: bool = True
    execution_isolated: bool = True
    sandbox_isolated: bool = True
    resource_isolated: bool = True
    secret_isolated: bool = True
    context_isolated: bool = True
    provenance_isolated: bool = True
    lifecycle_isolated: bool = True
    failure_isolated: bool = True
    cross_agent_communication_controlled: bool = True

    @property
    def valid(self) -> bool:
        """Return True only when every mandatory boundary is enabled."""
        return all(
            (
                self.authority_isolated,
                self.capability_isolated,
                self.execution_isolated,
                self.sandbox_isolated,
                self.resource_isolated,
                self.secret_isolated,
                self.context_isolated,
                self.provenance_isolated,
                self.lifecycle_isolated,
                self.failure_isolated,
                self.cross_agent_communication_controlled,
            )
        )


__all__ = ["AgentIsolationContract"]
