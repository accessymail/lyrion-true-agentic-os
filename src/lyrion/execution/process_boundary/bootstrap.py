"""Contract-only child bootstrap for the LYRION process boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import NoReturn

from lyrion.execution.process_boundary.bootstrap_contracts import (
    BootstrapContractError,
    BootstrapState,
    BootstrapStateMachine,
    LaunchHandoff,
)
from lyrion.execution.process_boundary.child_context import (
    ChildContextError,
    ChildExecutionContext,
)


@dataclass(frozen=True, slots=True)
class BootstrapContext:
    """Immutable observation of the current bootstrap state."""

    handoff: LaunchHandoff
    state: BootstrapState
    child_context: ChildExecutionContext | None = None


class ChildBootstrap:
    """
    Track one security-bound child bootstrap.

    This increment deliberately performs no operating-system mutation.
    Native enforcement will be attached only after this contract is validated.

    The ChildExecutionContext must be created by the actual child process and
    explicitly attached here. This prevents the supervising controller from
    accidentally becoming the enforcement target.
    """

    def __init__(self, handoff: LaunchHandoff) -> None:
        self._handoff = handoff
        self._state_machine = BootstrapStateMachine(
            handoff.execution_id,
        )
        self._child_context: ChildExecutionContext | None = None

    @property
    def handoff(self) -> LaunchHandoff:
        """Return the immutable handoff."""
        return self._handoff

    @property
    def state(self) -> BootstrapState:
        """Return the current bootstrap state."""
        return self._state_machine.state

    @property
    def child_context(self) -> ChildExecutionContext | None:
        """Return the verified child-process context, when attached."""
        return self._child_context

    def bind_identity(self, execution_id: str) -> BootstrapContext:
        """Bind the observed child execution identity."""
        if execution_id != self._handoff.execution_id:
            self._fail(
                "execution identity does not match launch handoff"
            )

        self._state_machine.transition(
            BootstrapState.IDENTITY_BOUND,
        )

        return self._context()

    def bind_process_context(
        self,
        context: ChildExecutionContext,
    ) -> BootstrapContext:
        """
        Attach and verify the context created by the actual child process.

        The context must describe this launch handoff and the currently
        executing process. No operating-system state is mutated here.
        """
        self._state_machine.require(
            BootstrapState.IDENTITY_BOUND,
        )

        try:
            context.verify_current_process()
            context.verify_handoff()
        except ChildContextError as exc:
            self._fail(str(exc))

        if context.handoff is not self._handoff:
            if context.handoff.model_dump() != self._handoff.model_dump():
                self._fail(
                    "child execution context handoff does not match "
                    "launch handoff"
                )

        self._child_context = context

        return self._context()

    def validate_handoff(self) -> BootstrapContext:
        """Validate the integrity-bound handoff."""
        self._state_machine.require(
            BootstrapState.IDENTITY_BOUND,
        )

        child_context = self._child_context

        if child_context is None:
            self._fail(
                "child execution context must be bound before "
                "handoff validation"
            )

        try:
            child_context.verify_current_process()
            child_context.verify_handoff()
            self._handoff.verify_integrity()
        except ChildContextError as exc:
            self._fail(str(exc))
        except BootstrapContractError:
            self._fail(
                "launch handoff integrity verification failed"
            )

        self._state_machine.transition(
            BootstrapState.HANDOFF_VALIDATED,
        )

        return self._context()

    def transition(
        self,
        target: BootstrapState,
    ) -> BootstrapContext:
        """
        Advance the bootstrap after the corresponding operation succeeds.

        The native launcher will own the actual operations in a later
        implementation increment.
        """
        self._state_machine.transition(target)
        return self._context()

    def require_exec_ready(self) -> None:
        """Require complete verified enforcement before exec."""
        self._state_machine.require(
            BootstrapState.EXEC_READY,
        )

    def fail(self, reason: str) -> BootstrapContext:
        """Enter the terminal fail-closed state."""
        if not reason.strip():
            raise BootstrapContractError(
                "bootstrap failure reason must not be empty"
            )

        self._state_machine.transition(
            BootstrapState.FAILED,
        )

        return self._context()

    def _fail(self, reason: str) -> NoReturn:
        """Fail closed and raise a contract error."""
        self._state_machine.transition(
            BootstrapState.FAILED,
        )
        raise BootstrapContractError(reason)

    def _context(self) -> BootstrapContext:
        return BootstrapContext(
            handoff=self._handoff,
            state=self._state_machine.state,
            child_context=self._child_context,
        )


__all__ = [
    "BootstrapContext",
    "ChildBootstrap",
]
