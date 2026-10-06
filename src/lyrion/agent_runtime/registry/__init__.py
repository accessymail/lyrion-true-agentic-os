"""Agent Runtime registry coordination contracts."""

from .registry import AgentRegistrationRecord, AgentRegistry, AgentRegistryError

__all__ = [
    "AgentHarnessIdentityResolver",
    "AgentIdentityResolutionError",
    "AgentRegistrationRecord",
    "AgentRegistry",
    "AgentRegistryError",
]

from .identity_resolver import (
    AgentHarnessIdentityResolver,
    AgentIdentityResolutionError,
)
