"""Module 1.6-F — Agent Runtime supervision/failure/recovery coordination.

Security boundary:

    Authorization
        -> Capability Gateway
        -> Execution Admission
        -> Secure Executor
        -> Agent Sandbox
        -> LHICF
        -> Host

This module is coordination-plane only.

Supervision != authorization
Runtime health != authorization
Recovery != authority restoration
Cancellation != authority
Quarantine != authority
Provenance != authority
Retry != authorization
Runtime context != execution admission
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Final
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from lyrion.agent_runtime.contracts.lifecycle import AgentLifecycleState
from lyrion.agent_runtime.lifecycle.coordinator import (
    AgentRuntimeLifecycleCoordinator,
    RuntimeLifecycleError,
)


class RuntimeSupervisionError(ValueError):
    """Raised when a supervision operation violates runtime invariants."""


class FailureCategory(StrEnum):
    """Controlled runtime failure classifications."""

    RUNTIME = "runtime"
    AGENT = "agent"
    TASK = "task"
    DEPENDENCY = "dependency"
    CANCELLATION = "cancellation"
    INTEGRITY = "integrity"
    SECURITY_BOUNDARY = "security_boundary"
    RECOVERY = "recovery"


class RuntimeFailure(BaseModel):
    """Immutable failure evidence.

    Failure evidence is provenance/diagnostic data only and never grants
    authorization, capability, admission, or delegated authority.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
    )

    failure_id: UUID = Field(default_factory=uuid4)
    category: FailureCategory
    task_id: UUID
    agent_id: UUID
    context_id: UUID
    correlation_id: UUID
    message: str = Field(min_length=1, max_length=512)
    recoverable: bool
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SupervisionEvent(BaseModel):
    """Immutable supervision provenance event."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
    )

    event_id: UUID = Field(default_factory=uuid4)
    sequence: int = Field(ge=1)
    event_type: str = Field(min_length=1, max_length=64)
    task_id: UUID
    agent_id: UUID
    context_id: UUID
    correlation_id: UUID
    lifecycle_state: AgentLifecycleState
    failure_id: UUID | None = None
    reason: str = Field(min_length=1, max_length=512)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


_ACTIVE_STATES: Final[frozenset[AgentLifecycleState]] = frozenset(
    {
        AgentLifecycleState.ASSIGNED,
        AgentLifecycleState.ADMITTED,
        AgentLifecycleState.RUNNING,
        AgentLifecycleState.CANCELLING,
    }
)


class RuntimeSupervisionCoordinator:
    """Coordinate runtime health, failure, cancellation, quarantine and recovery.

    IMPORTANT SECURITY BOUNDARY:

    This component does not:
      * authorize actions;
      * grant capabilities;
      * create delegated authority;
      * make execution-admission decisions;
      * execute host operations;
      * restore revoked/expired authority;
      * bypass Capability Gateway or Execution Admission.

    Recovery only restores runtime coordination state. Consequential work
    must subsequently pass through fresh authoritative security validation.
    """

    def __init__(self, lifecycle: AgentRuntimeLifecycleCoordinator) -> None:
        self._lifecycle = lifecycle
        self._events: tuple[SupervisionEvent, ...] = ()
        self._failures: tuple[RuntimeFailure, ...] = ()

        self._validate_runtime_integrity()

    @property
    def lifecycle(self) -> AgentRuntimeLifecycleCoordinator:
        """Return the underlying lifecycle coordinator."""
        return self._lifecycle

    @property
    def state(self) -> AgentLifecycleState:
        """Return the current lifecycle state."""
        return self._lifecycle.state

    @property
    def events(self) -> tuple[SupervisionEvent, ...]:
        """Return immutable supervision provenance."""
        return self._events

    @property
    def failures(self) -> tuple[RuntimeFailure, ...]:
        """Return immutable failure evidence."""
        return self._failures

    @property
    def is_terminal(self) -> bool:
        """Return whether consequential progression has terminated."""
        return self._lifecycle.is_terminal

    def _validate_runtime_integrity(self) -> None:
        """Fail closed if runtime correlation is inconsistent."""
        try:
            self._lifecycle.verify_execution_context_correlation()
        except (RuntimeLifecycleError, ValueError) as exc:
            raise RuntimeSupervisionError(
                "runtime integrity validation failed"
            ) from exc

    def _record(
        self,
        event_type: str,
        *,
        reason: str,
        failure_id: UUID | None = None,
    ) -> SupervisionEvent:
        self._validate_runtime_integrity()

        binding = self._lifecycle.binding
        context = self._lifecycle.context

        event = SupervisionEvent(
            sequence=len(self._events) + 1,
            event_type=event_type,
            task_id=binding.task_id,
            agent_id=binding.agent_id,
            context_id=context.context_id,
            correlation_id=context.correlation_id,
            lifecycle_state=self._lifecycle.state,
            failure_id=failure_id,
            reason=reason,
        )

        self._events = (*self._events, event)
        return event

    def observe_health(self, *, reason: str = "runtime health observed") -> SupervisionEvent:
        """Record a health observation without creating authority."""
        if self.is_terminal:
            raise RuntimeSupervisionError(
                "terminal runtime cannot continue consequential supervision"
            )

        return self._record("health_observed", reason=reason)

    def report_failure(
        self,
        *,
        category: FailureCategory,
        message: str,
        recoverable: bool,
    ) -> RuntimeFailure:
        """Record and classify a runtime failure.

        Failure classification is diagnostic evidence only.
        """
        if self.is_terminal:
            raise RuntimeSupervisionError(
                "terminal runtime cannot accept a new consequential failure"
            )

        self._validate_runtime_integrity()

        binding = self._lifecycle.binding
        context = self._lifecycle.context

        failure = RuntimeFailure(
            category=category,
            task_id=binding.task_id,
            agent_id=binding.agent_id,
            context_id=context.context_id,
            correlation_id=context.correlation_id,
            message=message,
            recoverable=recoverable,
        )

        self._failures = (*self._failures, failure)

        self._record(
            "failure_reported",
            reason=message,
            failure_id=failure.failure_id,
        )

        return failure

    def request_cancellation(self) -> SupervisionEvent:
        """Request cancellation; cancellation creates no authority."""
        if self.is_terminal:
            raise RuntimeSupervisionError(
                "terminal runtime cannot be cancelled"
            )

        try:
            self._lifecycle.request_cancellation()
        except RuntimeLifecycleError as exc:
            raise RuntimeSupervisionError(str(exc)) from exc

        return self._record(
            "cancellation_requested",
            reason="runtime cancellation requested",
        )

    def complete_cancellation(self) -> SupervisionEvent:
        """Complete cancellation and prevent consequential continuation."""
        try:
            self._lifecycle.complete_cancellation()
        except RuntimeLifecycleError as exc:
            raise RuntimeSupervisionError(str(exc)) from exc

        return self._record(
            "cancellation_completed",
            reason="runtime cancellation completed",
        )

    def contain_failure(
        self,
        *,
        reason: str,
    ) -> SupervisionEvent:
        """Contain a failure without creating authority."""
        if not reason.strip():
            raise RuntimeSupervisionError("containment reason is required")

        if self.is_terminal:
            raise RuntimeSupervisionError(
                "terminal runtime is already contained"
            )

        failure_id = (
            self._failures[-1].failure_id
            if self._failures
            else None
        )

        return self._record(
            "failure_contained",
            reason=reason.strip(),
            failure_id=failure_id,
        )

    def quarantine(
        self,
        *,
        reason: str,
    ) -> SupervisionEvent:
        """Quarantine runtime progression.

        Quarantine terminates consequential progression and grants no
        authorization, capability, admission, or delegated authority.
        """
        if not reason.strip():
            raise RuntimeSupervisionError("quarantine reason is required")

        if self.is_terminal:
            raise RuntimeSupervisionError(
                "terminal runtime cannot be quarantined again"
            )

        try:
            self._lifecycle.quarantine(reason=reason.strip())
        except RuntimeLifecycleError as exc:
            raise RuntimeSupervisionError(str(exc)) from exc

        self._lifecycle.clear_security_references()

        return self._record(
            "runtime_quarantined",
            reason=reason.strip(),
        )

    def mark_failure_recoverable(self) -> SupervisionEvent:
        """Mark current runtime work recoverable."""
        if self.is_terminal:
            raise RuntimeSupervisionError(
                "terminal runtime cannot become recoverable"
            )

        try:
            self._lifecycle.mark_recoverable()
        except RuntimeLifecycleError as exc:
            raise RuntimeSupervisionError(str(exc)) from exc

        return self._record(
            "recovery_eligible",
            reason="runtime marked recoverable",
        )

    def begin_recovery(self) -> SupervisionEvent:
        """Begin recovery after invalidating runtime-held security references."""
        try:
            self._lifecycle.begin_recovery()
        except RuntimeLifecycleError as exc:
            raise RuntimeSupervisionError(str(exc)) from exc

        if self._lifecycle.context.admission_id is not None:
            raise RuntimeSupervisionError(
                "recovery retained an admission reference"
            )

        if self._lifecycle.context.delegated_authority_id is not None:
            raise RuntimeSupervisionError(
                "recovery retained a delegated-authority reference"
            )

        return self._record(
            "recovery_started",
            reason="recovery started; fresh security validation required",
        )

    def finish_recovery(self) -> SupervisionEvent:
        """Finish runtime recovery without restoring security authority.

        The lifecycle returns to ASSIGNED. It must not transition directly
        to RUNNING. Fresh security validation/admission is required before
        consequential execution.
        """
        try:
            self._lifecycle.finish_recovery()
        except RuntimeLifecycleError as exc:
            raise RuntimeSupervisionError(str(exc)) from exc

        if self._lifecycle.context.admission_id is not None:
            raise RuntimeSupervisionError(
                "recovery restored an admission reference"
            )

        if self._lifecycle.context.delegated_authority_id is not None:
            raise RuntimeSupervisionError(
                "recovery restored delegated authority"
            )

        return self._record(
            "recovery_completed",
            reason="runtime recovery completed; fresh security validation required",
        )

    def retry_allowed(self) -> bool:
        """Return whether runtime coordination permits another attempt.

        This method is deliberately not an authorization decision.
        It only checks runtime state. Consequential retry must still pass
        the authoritative security chain.
        """
        self._validate_runtime_integrity()
        return self.state in _ACTIVE_STATES

    def validate_retry_context(self) -> None:
        """Validate retry correlation without validating authorization."""
        if not self.retry_allowed():
            raise RuntimeSupervisionError(
                "runtime state does not permit retry coordination"
            )

        if self._lifecycle.context.admission_id is None:
            raise RuntimeSupervisionError(
                "retry has no runtime admission reference; fresh security "
                "validation is required before consequential execution"
            )

        self._validate_runtime_integrity()

    def snapshot(self) -> tuple[
        AgentLifecycleState,
        tuple[SupervisionEvent, ...],
        tuple[RuntimeFailure, ...],
    ]:
        """Return immutable supervision state."""
        return self.state, self._events, self._failures
