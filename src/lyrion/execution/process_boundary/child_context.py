"""Child-process execution context for LYRION enforcement.

This module defines the explicit boundary between the supervising controller
and the workload child.

Security invariants:
- The context is immutable.
- The execution identity comes from the authorized LaunchHandoff.
- Native enforcement operations execute against the CURRENT CHILD PROCESS.
- The controller process must never be mutated by child enforcement.
- No authorization decision is performed here.
- No policy is generated or weakened here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from lyrion.execution.process_boundary.bootstrap_contracts import (
    BootstrapContractError,
    LaunchHandoff,
)


class ChildContextError(RuntimeError):
    """Raised when a child execution context violates an invariant."""


@dataclass(frozen=True, slots=True)
class ChildExecutionContext:
    """Immutable identity of the process executing workload enforcement."""

    handoff: LaunchHandoff
    pid: int
    pgid: int

    @classmethod
    def create(
        cls,
        handoff: LaunchHandoff,
    ) -> ChildExecutionContext:
        """Create a context bound to the current child process."""
        if handoff.execution_id.strip() == "":
            raise ChildContextError(
                "launch handoff execution_id must not be empty"
            )

        pid = os.getpid()

        if pid <= 0:
            raise ChildContextError(
                "current child process returned an invalid PID"
            )

        try:
            pgid = os.getpgid(pid)
        except OSError as exc:
            raise ChildContextError(
                "unable to establish child process-group identity"
            ) from exc

        if pgid <= 0:
            raise ChildContextError(
                "current child process returned an invalid PGID"
            )

        return cls(
            handoff=handoff,
            pid=pid,
            pgid=pgid,
        )

    def verify_current_process(self) -> None:
        """Prove that this context still describes the current process."""
        current_pid = os.getpid()

        if current_pid != self.pid:
            raise ChildContextError(
                "child enforcement context PID mismatch"
            )

        try:
            current_pgid = os.getpgid(current_pid)
        except OSError as exc:
            raise ChildContextError(
                "unable to revalidate child process-group identity"
            ) from exc

        if current_pgid != self.pgid:
            raise ChildContextError(
                "child enforcement context PGID mismatch"
            )

        if self.handoff.execution_id.strip() == "":
            raise ChildContextError(
                "launch handoff execution_id must not be empty"
            )

    def verify_handoff(self) -> None:
        """Revalidate the integrity-bound launch handoff."""
        try:
            self.handoff.verify_integrity()
        except BootstrapContractError as exc:
            raise ChildContextError(
                "child launch handoff integrity verification failed"
            ) from exc


__all__ = [
    "ChildContextError",
    "ChildExecutionContext",
]
