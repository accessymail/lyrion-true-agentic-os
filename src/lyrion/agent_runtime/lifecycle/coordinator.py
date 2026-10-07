"""Module 1.6-E — Agent Runtime lifecycle/task-binding integration.

The coordinator is deliberately a coordination-plane component.

Security boundary invariant:
    Authorization
    -> Capability Gateway
    -> Execution Admission
    -> Secure Executor
    -> Agent Sandbox
    -> LHICF
    -> Host

This module does not implement or reproduce any authority from that chain.
Admission and delegated-authority identifiers are references only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from lyrion.agent_runtime.contracts.lifecycle import (
    AgentLifecycle,
    AgentLifecycleState,
)
from lyrion.agent_runtime.contracts.runtime_context import RuntimeExecutionContext
from lyrion.agent_runtime.contracts.task_binding import AgentTaskBinding


class RuntimeLifecycleError(ValueError):
    """Raised when a lifecycle integration operation is invalid."""


class LifecycleTransitionRecord(BaseModel):
    """Immutable provenance record for one coordination transition."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
    )

    event_id: UUID = Field(default_factory=uuid4)
    sequence: int = Field(ge=1)

    from_state: AgentLifecycleState
    to_state: AgentLifecycleState

    task_id: UUID
    agent_id: UUID
    binding_id: UUID
    binding_revision: int = Field(ge=1)

    context_id: UUID
    correlation_id: UUID

    reason: str = Field(min_length=1, max_length=256)

    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )


class AgentRuntimeLifecycleCoordinator:
    """Coordinate lifecycle, task binding, runtime context and provenance.

    This class intentionally has no authorization or execution-admission
    authority.

    In particular:

    * lifecycle state is not authorization;
    * task binding is not authorization;
    * an admission reference is not an admission decision;
    * delegated_authority_id is a reference only;
    * recovery clears security references;
    * consequential execution must re-enter the authoritative security chain.
    """

    def __init__(
        self,
        *,
        binding: AgentTaskBinding,
        lifecycle: AgentLifecycle | None = None,
        context: RuntimeExecutionContext | None = None,
    ) -> None:
        if lifecycle is None:
            lifecycle = AgentLifecycle(
                state=AgentLifecycleState.REGISTERED
            )

        if context is None:
            context = RuntimeExecutionContext(
                task_id=binding.task_id,
                agent_id=binding.agent_id,
            )

        self._validate_correlation(binding, context)

        self._binding = binding
        self._lifecycle = lifecycle
        self._context = context
        self._history: tuple[LifecycleTransitionRecord, ...] = ()

    @staticmethod
    def _validate_correlation(
        binding: AgentTaskBinding,
        context: RuntimeExecutionContext,
    ) -> None:
        if context.task_id != binding.task_id:
            raise RuntimeLifecycleError(
                "runtime context task identity does not match task binding"
            )

        if context.agent_id != binding.agent_id:
            raise RuntimeLifecycleError(
                "runtime context agent identity does not match task binding"
            )

    @property
    def lifecycle(self) -> AgentLifecycle:
        return self._lifecycle

    @property
    def state(self) -> AgentLifecycleState:
        return self._lifecycle.state

    @property
    def binding(self) -> AgentTaskBinding:
        return self._binding

    @property
    def context(self) -> RuntimeExecutionContext:
        return self._context

    @property
    def provenance(self) -> tuple[LifecycleTransitionRecord, ...]:
        return self._history

    @property
    def is_terminal(self) -> bool:
        return self.state in {
            AgentLifecycleState.COMPLETED,
            AgentLifecycleState.CANCELLED,
            AgentLifecycleState.FAILED,
            AgentLifecycleState.QUARANTINED,
        }

    def transition(
        self,
        target: AgentLifecycleState,
        *,
        reason: str,
    ) -> AgentLifecycle:
        """Perform one governed coordination transition.

        Invalid transitions fail closed through the existing lifecycle
        contract. No security decision is created here.
        """
        if not reason or not reason.strip():
            raise RuntimeLifecycleError("transition reason is required")

        current = self._lifecycle

        try:
            next_lifecycle = current.transition(target)
        except ValueError as exc:
            raise RuntimeLifecycleError(str(exc)) from exc

        record = LifecycleTransitionRecord(
            sequence=len(self._history) + 1,
            from_state=current.state,
            to_state=target,
            task_id=self._binding.task_id,
            agent_id=self._binding.agent_id,
            binding_id=self._binding.binding_id,
            binding_revision=self._binding.binding_revision,
            context_id=self._context.context_id,
            correlation_id=self._context.correlation_id,
            reason=reason.strip(),
        )

        self._lifecycle = next_lifecycle
        self._history = (*self._history, record)

        return next_lifecycle

    def attach_admission_reference(
        self,
        admission_id: UUID,
        *,
        delegated_authority_id: UUID | None = None,
    ) -> RuntimeExecutionContext:
        """Attach security references without validating or creating authority.

        The authoritative admission/security layer remains responsible for
        determining whether those references are valid, current, authorized,
        and executable.
        """
        if self.is_terminal:
            raise RuntimeLifecycleError(
                "terminal lifecycle cannot receive an admission reference"
            )

        if not isinstance(admission_id, UUID):
            raise TypeError("admission_id must be a UUID")

        if (
            delegated_authority_id is not None
            and not isinstance(delegated_authority_id, UUID)
        ):
            raise TypeError("delegated_authority_id must be a UUID")

        self._context = self._context.model_copy(
            update={
                "admission_id": admission_id,
                "delegated_authority_id": delegated_authority_id,
            }
        )

        return self._context

    def clear_security_references(self) -> RuntimeExecutionContext:
        """Clear admission/authority references without creating authority."""
        self._context = self._context.model_copy(
            update={
                "admission_id": None,
                "delegated_authority_id": None,
            }
        )
        return self._context

    def request_cancellation(self) -> AgentLifecycle:
        """Move an active coordination state into CANCELLING."""
        return self.transition(
            AgentLifecycleState.CANCELLING,
            reason="cancellation requested",
        )

    def complete_cancellation(self) -> AgentLifecycle:
        """Finalize a previously requested cancellation."""
        if self.state is not AgentLifecycleState.CANCELLING:
            raise RuntimeLifecycleError(
                "cancellation can only be finalized from CANCELLING"
            )

        return self.transition(
            AgentLifecycleState.CANCELLED,
            reason="cancellation completed",
        )

    def mark_recoverable(self) -> AgentLifecycle:
        """Mark failed/running work as recoverable."""
        return self.transition(
            AgentLifecycleState.RECOVERABLE,
            reason="runtime work marked recoverable",
        )

    def begin_recovery(self) -> AgentLifecycle:
        """Begin recovery and invalidate runtime-held security references."""
        if self.state is not AgentLifecycleState.RECOVERABLE:
            raise RuntimeLifecycleError(
                "recovery can only begin from RECOVERABLE"
            )

        # Recovery cannot restore or carry forward stale authority.
        self.clear_security_references()

        return self.transition(
            AgentLifecycleState.RECOVERING,
            reason="recovery begun; security references cleared",
        )

    def finish_recovery(self) -> AgentLifecycle:
        """Return recovered work to ASSIGNED, never directly to RUNNING."""
        if self.state is not AgentLifecycleState.RECOVERING:
            raise RuntimeLifecycleError(
                "recovery can only finish from RECOVERING"
            )

        # Fresh security validation must occur before consequential execution.
        return self.transition(
            AgentLifecycleState.ASSIGNED,
            reason="recovery completed; fresh security validation required",
        )

    def quarantine(self, *, reason: str) -> AgentLifecycle:
        """Terminate consequential progression through quarantine."""
        return self.transition(
            AgentLifecycleState.QUARANTINED,
            reason=reason,
        )

    def verify_execution_context_correlation(self) -> None:
        """Verify coordination identities remain correlated.

        This is not an authorization check.
        """
        self._validate_correlation(self._binding, self._context)

    def snapshot(self) -> tuple[
        AgentLifecycle,
        AgentTaskBinding,
        RuntimeExecutionContext,
    ]:
        """Return the immutable coordination snapshot."""
        return self._lifecycle, self._binding, self._context
