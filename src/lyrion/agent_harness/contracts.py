"""Bounded Agent Harness contracts for LYRION True Agentic OS.

The Agent Harness is an attribution and binding layer. It consumes existing
identity/task/authorization/capability/admission contracts and never creates
execution authority.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from lyrion.capabilities.contracts import (
    AuthorizationResult,
    CapabilityRequest,
)
from lyrion.capabilities.gateway import ExecutionAdmission
from lyrion.core.types import TaskId

from .isolation import AgentIsolationContract


class AgentBindingState(StrEnum):
    """Local orchestration state for one immutable agent binding."""

    BOUND = "BOUND"
    VALIDATED = "VALIDATED"
    DELEGATED = "DELEGATED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVOKED = "REVOKED"


class AgentIdentity(BaseModel):
    """Explicit attributable agent identity.

    This contract deliberately does not infer identity from model output,
    prompts, memory, tool output, or free-form agent content. The identity
    must be supplied by a trusted caller together with an attribution/
    registration reference. Authentication of that reference remains owned
    by the platform identity/registry boundary; this model does not grant
    authority.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    agent_id: str = Field(min_length=1, max_length=200)
    identity_provenance_ref: str = Field(min_length=1, max_length=500)

    @field_validator("agent_id", "identity_provenance_ref")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        """Normalize and reject blank identity values."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("identity values must not be empty")
        return normalized


class AgentBinding(BaseModel):
    """Immutable binding between an agent and an already-authorized task."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    identity: AgentIdentity
    task_id: TaskId
    authority_context: AuthorizationResult
    capability_context: CapabilityRequest
    execution_admission: ExecutionAdmission
    isolation_contract: AgentIsolationContract
    lifecycle_state: AgentBindingState = AgentBindingState.BOUND
    provenance_context: str = Field(min_length=1, max_length=500)

    @field_validator("provenance_context")
    @classmethod
    def normalize_provenance(cls, value: str) -> str:
        """Normalize the binding provenance reference."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("provenance_context must not be empty")
        return normalized

    def transition(self, target: AgentBindingState) -> AgentBinding:
        """Return a new binding after a valid local lifecycle transition."""
        allowed: dict[AgentBindingState, frozenset[AgentBindingState]] = {
            AgentBindingState.BOUND: frozenset(
                {AgentBindingState.VALIDATED, AgentBindingState.REVOKED}
            ),
            AgentBindingState.VALIDATED: frozenset(
                {AgentBindingState.DELEGATED, AgentBindingState.REVOKED}
            ),
            AgentBindingState.DELEGATED: frozenset(
                {AgentBindingState.COMPLETED, AgentBindingState.FAILED, AgentBindingState.REVOKED}
            ),
            AgentBindingState.COMPLETED: frozenset(),
            AgentBindingState.FAILED: frozenset(),
            AgentBindingState.REVOKED: frozenset(),
        }

        if target not in allowed[self.lifecycle_state]:
            raise ValueError(
                "invalid agent binding lifecycle transition: "
                f"{self.lifecycle_state} -> {target}"
            )

        return self.model_copy(update={"lifecycle_state": target})


class BindingValidationResult(BaseModel):
    """Immutable fail-closed validation result for an agent binding."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    valid: bool
    failure_reason: str | None = Field(default=None, max_length=4000)
    validated_agent_id: str | None = Field(default=None, max_length=200)
    validated_task_id: TaskId | None = None
    validated_admission: ExecutionAdmission | None = None

    @model_validator(mode="after")
    def validate_consistency(self) -> BindingValidationResult:
        """Keep valid and invalid result states mutually exclusive."""
        if self.valid and self.failure_reason is not None:
            raise ValueError("valid result cannot contain failure_reason")
        if not self.valid and self.failure_reason is None:
            raise ValueError("invalid result requires failure_reason")
        return self


class AgentExecutionProvenance(BaseModel):
    """Immutable attribution record derived from a validated binding."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    agent_id: str = Field(min_length=1, max_length=200)
    identity_provenance_ref: str = Field(min_length=1, max_length=500)
    task_id: TaskId
    principal_id: str = Field(min_length=1, max_length=500)
    request_id: str = Field(min_length=1, max_length=500)
    execution_id: str = Field(min_length=1, max_length=500)
    capability_id: str = Field(min_length=1, max_length=500)
    target_scope: str = Field(min_length=1, max_length=1000)
    authorization_reference: str = Field(min_length=1, max_length=500)
    policy_version: str = Field(min_length=1, max_length=200)
    provenance_context: str = Field(min_length=1, max_length=500)
    correlation_id: str | None = None


__all__ = [
    "AgentBinding",
    "AgentBindingState",
    "AgentExecutionProvenance",
    "AgentIdentity",
    "BindingValidationResult",
]
