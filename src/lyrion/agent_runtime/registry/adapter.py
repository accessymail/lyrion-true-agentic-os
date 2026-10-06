"""Compatibility adapter between Agent Runtime and Agent Harness."""

from __future__ import annotations

from typing import Protocol, TypeVar

from lyrion.agent_harness.contracts import AgentIdentity as HarnessAgentIdentity
from lyrion.agent_runtime.contracts.agent import AgentIdentity

HarnessIdentityT = TypeVar("HarnessIdentityT", covariant=True)


class AgentHarnessIdentityAdapter(Protocol[HarnessIdentityT]):
    """Translate Agent Runtime identity into Harness identity only."""

    def to_harness_identity(
        self,
        identity: AgentIdentity,
        *,
        identity_provenance_ref: str,
    ) -> HarnessIdentityT:
        """Create a Harness identity from reconciled identity data."""
        ...


class AgentIdentityAdapter:
    """Production-boundary identity adapter.

    Security properties:
        - Performs deterministic identity translation only.
        - Does not authorize.
        - Does not grant capabilities.
        - Does not create delegated authority.
        - Does not create ExecutionAdmission.
        - Does not invoke SecureExecutor.
        - Does not access the host.
    """

    def to_harness_identity(
        self,
        identity: AgentIdentity,
        *,
        identity_provenance_ref: str,
    ) -> HarnessAgentIdentity:
        """Translate a Runtime identity into the existing Harness identity."""
        if not identity_provenance_ref.strip():
            raise ValueError("identity_provenance_ref must not be blank")

        return HarnessAgentIdentity(
            agent_id=str(identity.agent_id),
            identity_provenance_ref=identity_provenance_ref,
        )


__all__ = [
    "AgentHarnessIdentityAdapter",
    "AgentIdentityAdapter",
]
