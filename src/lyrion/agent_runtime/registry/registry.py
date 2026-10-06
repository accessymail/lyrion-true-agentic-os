"""Bounded coordination-plane registry for LYRION agents.

Security invariant:
    Registration is descriptive coordination state.

This registry MUST NOT:
    - authorize execution;
    - grant delegated authority;
    - grant capabilities;
    - create ExecutionAdmission;
    - invoke SecureExecutor;
    - bypass AgentHarness;
    - provide direct host access.

The registry is intentionally in-memory at this stage. Durable persistence
belongs to the existing persistence architecture and will be integrated
through an explicit adapter rather than duplicated here.
"""

from __future__ import annotations

from threading import RLock
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from lyrion.agent_runtime.contracts.agent import (
    AgentRegistration,
    AgentTrustState,
)


class AgentRegistryError(ValueError):
    """Raised when a registry invariant is violated."""


class AgentRegistrationRecord(BaseModel):
    """Immutable registry snapshot.

    This object represents registration metadata only. It is not an
    authorization or execution object.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
    )

    registration: AgentRegistration


class AgentRegistry:
    """Thread-safe coordination-plane registry.

    Ownership:
        Agent identity
        Agent registration
        Registration lookup
        Registration revision replacement
        Trust metadata storage

    Explicitly NOT owned:
        Authorization
        Capability grants
        Execution admission
        Secure execution
        Host integration
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._registrations: dict[UUID, AgentRegistration] = {}

    def register(self, registration: AgentRegistration) -> AgentRegistration:
        """Register a new agent identity.

        Registration is idempotent only when the exact registration revision
        already exists. Conflicting registrations are rejected rather than
        silently overwritten.
        """
        agent_id = registration.identity.agent_id

        with self._lock:
            existing = self._registrations.get(agent_id)

            if existing is None:
                self._registrations[agent_id] = registration
                return registration

            if existing == registration:
                return existing

            raise AgentRegistryError(
                f"agent already registered with conflicting state: {agent_id}"
            )

    def replace(
        self,
        registration: AgentRegistration,
    ) -> AgentRegistration:
        """Replace registration metadata using an explicit revision.

        Replacement requires a strictly greater registration revision.
        This prevents stale callers from overwriting newer state.
        """
        agent_id = registration.identity.agent_id

        with self._lock:
            existing = self._registrations.get(agent_id)

            if existing is None:
                raise AgentRegistryError(
                    f"cannot replace unregistered agent: {agent_id}"
                )

            if registration.registration_revision <= (
                existing.registration_revision
            ):
                raise AgentRegistryError(
                    "registration revision must increase monotonically"
                )

            self._registrations[agent_id] = registration
            return registration

    def get(self, agent_id: UUID) -> AgentRegistration:
        """Return a registration or fail closed."""
        with self._lock:
            registration = self._registrations.get(agent_id)

        if registration is None:
            raise AgentRegistryError(f"agent is not registered: {agent_id}")

        return registration

    def contains(self, agent_id: UUID) -> bool:
        """Return whether an identity is registered."""
        with self._lock:
            return agent_id in self._registrations

    def unregister(self, agent_id: UUID) -> AgentRegistration:
        """Remove coordination registration.

        This operation does NOT revoke authorization or capabilities.
        Security revocation remains owned by the security architecture.
        """
        with self._lock:
            registration = self._registrations.pop(agent_id, None)

        if registration is None:
            raise AgentRegistryError(f"agent is not registered: {agent_id}")

        return registration

    def snapshot(self) -> tuple[AgentRegistrationRecord, ...]:
        """Return a deterministic immutable registry snapshot."""
        with self._lock:
            registrations = tuple(
                AgentRegistrationRecord(registration=value)
                for value in self._registrations.values()
            )

        return tuple(
            sorted(
                registrations,
                key=lambda record: str(record.registration.identity.agent_id),
            )
        )

    def set_trust_state(
        self,
        agent_id: UUID,
        trust_state: AgentTrustState,
    ) -> AgentRegistration:
        """Update descriptive trust metadata.

        Trust state is metadata only and can never grant execution authority.
        """
        current = self.get(agent_id)

        updated = current.model_copy(
            update={
                "trust_state": trust_state,
                "registration_revision": current.registration_revision + 1,
            }
        )

        return self.replace(updated)
