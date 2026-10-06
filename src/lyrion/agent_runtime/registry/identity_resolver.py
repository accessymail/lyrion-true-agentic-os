"""Agent Runtime to Agent Harness identity-resolution boundary.

This module provides the controlled identity-resolution boundary between
the Agent Runtime coordination plane and the existing Agent Harness.

Security properties
-------------------
- Registration is required before identity resolution.
- Runtime identity is translated deterministically.
- Identity provenance must be supplied explicitly by the caller.
- Registry membership does not grant authorization.
- Runtime trust state does not grant authorization.
- Declared capabilities are never promoted into granted capabilities.
- No AuthorizationResult is created.
- No CapabilityRequest is created.
- No DelegatedAuthority is created.
- No ExecutionAdmission is created.
- SecureExecutor is never invoked.
- LHICF and host access are never exposed.
"""

from __future__ import annotations

from uuid import UUID

from lyrion.agent_harness.contracts import (
    AgentIdentity as HarnessAgentIdentity,
)
from lyrion.agent_runtime.contracts.agent import AgentIdentity
from lyrion.agent_runtime.registry.adapter import AgentIdentityAdapter
from lyrion.agent_runtime.registry.registry import AgentRegistry


class AgentIdentityResolutionError(ValueError):
    """Raised when Runtime-to-Harness identity resolution fails."""


class AgentHarnessIdentityResolver:
    """Resolve a registered Runtime identity into Harness identity.

    This class belongs to the Agent Runtime coordination boundary.

    It deliberately does not perform authorization, capability resolution,
    execution admission, execution, sandboxing, or host integration.
    """

    def __init__(
        self,
        *,
        registry: AgentRegistry,
        adapter: AgentIdentityAdapter | None = None,
    ) -> None:
        self._registry = registry
        self._adapter = adapter or AgentIdentityAdapter()

    def resolve(
        self,
        agent_id: UUID,
        *,
        identity_provenance_ref: str,
    ) -> HarnessAgentIdentity:
        """Resolve one registered Runtime agent into Harness identity.

        The registration itself is only an identity/coordination record.
        It is never interpreted as authorization or execution permission.
        """
        if not identity_provenance_ref.strip():
            raise AgentIdentityResolutionError(
                "identity_provenance_ref must not be blank"
            )

        try:
            registration = self._registry.get(agent_id)
        except Exception as exc:
            # Do not expose registry internals through the integration
            # boundary. Resolution fails closed for every lookup failure.
            raise AgentIdentityResolutionError(
                "registered agent identity could not be resolved"
            ) from exc

        identity: AgentIdentity = registration.identity

        if identity.agent_id != agent_id:
            raise AgentIdentityResolutionError(
                "registry identity does not match requested agent_id"
            )

        try:
            return self._adapter.to_harness_identity(
                identity,
                identity_provenance_ref=identity_provenance_ref,
            )
        except (TypeError, ValueError) as exc:
            raise AgentIdentityResolutionError(
                "agent identity translation failed"
            ) from exc


__all__ = [
    "AgentHarnessIdentityResolver",
    "AgentIdentityResolutionError",
]
