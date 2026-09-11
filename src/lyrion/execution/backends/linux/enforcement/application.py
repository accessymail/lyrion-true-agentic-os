"""Immutable contracts for applying and verifying Linux enforcement."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lyrion.execution.backends.linux.enforcement.contracts import (
    EnforcementPrimitive,
    EnforcementState,
    LinuxEnforcementPlan,
)


class EnforcementApplicationStatus(StrEnum):
    """Overall result status for one enforcement application attempt."""

    VERIFIED = "verified"
    FAILED = "failed"
    ABORTED = "aborted"


class EnforcementApplicationContext(BaseModel):
    """Immutable context supplied to the enforcement application layer."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    execution_id: str = Field(
        min_length=1,
        max_length=500,
    )
    backend_id: str = Field(
        min_length=1,
        max_length=200,
    )
    started_at: datetime
    metadata: tuple[tuple[str, str], ...] = ()

    @classmethod
    def create(
        cls,
        *,
        execution_id: str,
        backend_id: str,
        started_at: datetime,
        metadata: dict[str, str] | None = None,
    ) -> EnforcementApplicationContext:
        """Create a deterministic immutable application context."""
        if started_at.tzinfo is None or started_at.utcoffset() is None:
            raise ValueError("started_at must be timezone-aware")

        normalized_metadata = tuple(
            sorted(
                (key, value)
                for key, value in (metadata or {}).items()
            )
        )

        return cls(
            execution_id=execution_id,
            backend_id=backend_id,
            started_at=started_at.astimezone(UTC),
            metadata=normalized_metadata,
        )

    @model_validator(mode="after")
    def validate_timestamp(self) -> EnforcementApplicationContext:
        """Require a timezone-aware context timestamp."""
        if (
            self.started_at.tzinfo is None
            or self.started_at.utcoffset() is None
        ):
            raise ValueError("started_at must be timezone-aware")

        return self


class EnforcementEvidence(BaseModel):
    """Immutable evidence describing one observed enforcement control."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    primitive: EnforcementPrimitive
    observed_state: EnforcementState
    evidence_type: str = Field(
        min_length=1,
        max_length=200,
    )
    evidence_ref: str | None = Field(
        default=None,
        min_length=1,
        max_length=1000,
    )
    observation: str = Field(
        min_length=1,
        max_length=4000,
    )

    @classmethod
    def verified(
        cls,
        *,
        primitive: EnforcementPrimitive,
        evidence_type: str,
        observation: str,
        evidence_ref: str | None = None,
    ) -> EnforcementEvidence:
        """Construct evidence explicitly recording VERIFIED state."""
        return cls(
            primitive=primitive,
            observed_state=EnforcementState.VERIFIED,
            evidence_type=evidence_type,
            evidence_ref=evidence_ref,
            observation=observation,
        )


class EnforcementPrimitiveResult(BaseModel):
    """Immutable result for one Linux enforcement primitive."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    primitive: EnforcementPrimitive
    required: bool
    state: EnforcementState
    success: bool
    reason: str = Field(
        min_length=1,
        max_length=2000,
    )
    evidence: tuple[EnforcementEvidence, ...] = ()

    @model_validator(mode="after")
    def validate_consistency(self) -> EnforcementPrimitiveResult:
        """Enforce primitive-level fail-closed invariants."""
        if self.state is EnforcementState.VERIFIED:
            if not self.success:
                raise ValueError(
                    "verified enforcement result must be successful"
                )

            if not self.evidence:
                raise ValueError(
                    "verified enforcement result requires evidence"
                )

            if any(
                item.primitive is not self.primitive
                or item.observed_state is not EnforcementState.VERIFIED
                for item in self.evidence
            ):
                raise ValueError(
                    "verified evidence must match the verified primitive"
                )

        if self.state is EnforcementState.APPLIED and not self.success:
            raise ValueError(
                "applied enforcement result must be successful"
            )

        if self.state is EnforcementState.FAILED and self.success:
            raise ValueError(
                "failed enforcement result cannot be successful"
            )

        return self


class EnforcementApplicationResult(BaseModel):
    """Immutable result of applying and verifying an enforcement plan."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    execution_id: str = Field(
        min_length=1,
        max_length=500,
    )
    backend_id: str = Field(
        min_length=1,
        max_length=200,
    )
    status: EnforcementApplicationStatus
    primitive_results: tuple[EnforcementPrimitiveResult, ...]
    failure_reason: str | None = Field(
        default=None,
        min_length=1,
        max_length=4000,
    )

    @model_validator(mode="after")
    def validate_consistency(self) -> EnforcementApplicationResult:
        """Enforce application-level fail-closed invariants."""
        required_results = tuple(
            result
            for result in self.primitive_results
            if result.required
        )

        if self.status is EnforcementApplicationStatus.VERIFIED:
            if not required_results:
                raise ValueError(
                    "verified enforcement requires required primitive results"
                )

            if any(
                result.state is not EnforcementState.VERIFIED
                for result in required_results
            ):
                raise ValueError(
                    "verified application requires every required primitive "
                    "to be verified"
                )

            if self.failure_reason is not None:
                raise ValueError(
                    "verified application cannot contain a failure reason"
                )

        elif self.status in {
            EnforcementApplicationStatus.FAILED,
            EnforcementApplicationStatus.ABORTED,
        }:
            if self.failure_reason is None:
                raise ValueError(
                    "failed or aborted application requires a failure reason"
                )

        return self

    @property
    def execution_permitted(self) -> bool:
        """Return whether enforcement verification permits execution."""
        return self.status is EnforcementApplicationStatus.VERIFIED


class EnforcementApplication(Protocol):
    """Contract implemented by the future Linux enforcement application."""

    def apply(
        self,
        plan: LinuxEnforcementPlan,
        context: EnforcementApplicationContext,
    ) -> EnforcementApplicationResult:
        """Apply and verify one immutable enforcement plan."""
        ...
