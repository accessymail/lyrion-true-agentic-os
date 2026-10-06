"""Agent identity and registration contracts.

Security invariant:
    Agent identity and registration are coordination-plane concepts.
    They do not constitute authorization, delegated authority, or
    capability grants.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

NonEmptyName = Annotated[str, Field(min_length=1, max_length=128)]
VersionString = Annotated[str, Field(min_length=1, max_length=64)]


class AgentTrustState(StrEnum):
    """Runtime trust classification.

    Trust state is descriptive runtime metadata only. It cannot grant
    execution authority.
    """

    UNKNOWN = "unknown"
    UNTRUSTED = "untrusted"
    EVALUATING = "evaluating"
    TRUSTED = "trusted"
    QUARANTINED = "quarantined"


class AgentIdentity(BaseModel):
    """Stable identity of a registered agent."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
    )

    agent_id: UUID = Field(default_factory=uuid4)
    agent_type: NonEmptyName
    instance_name: NonEmptyName
    version: VersionString

    @field_validator("agent_type", "instance_name", "version")
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("agent identity fields must not be blank")
        return value


class AgentRegistration(BaseModel):
    """Immutable registration record for an agent.

    Registration does not authorize the agent to perform any operation.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
    )

    identity: AgentIdentity
    registered_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    trust_state: AgentTrustState = AgentTrustState.UNKNOWN

    # Deliberately descriptive only.
    declared_capabilities: tuple[str, ...] = Field(default_factory=tuple)

    registration_revision: int = Field(default=1, ge=1)

    @field_validator("declared_capabilities")
    @classmethod
    def validate_declared_capabilities(
        cls,
        values: tuple[str, ...],
    ) -> tuple[str, ...]:
        normalized: list[str] = []

        for capability in values:
            value = capability.strip()

            if not value:
                raise ValueError(
                    "declared capability names must not be blank"
                )

            if len(value) > 128:
                raise ValueError(
                    "declared capability names must not exceed 128 characters"
                )

            normalized.append(value)

        if len(normalized) != len(set(normalized)):
            raise ValueError(
                "declared capabilities must not contain duplicates"
            )

        return tuple(normalized)
