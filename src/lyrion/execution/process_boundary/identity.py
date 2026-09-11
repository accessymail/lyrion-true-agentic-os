"""Immutable workload process identity for Lyrion execution."""

from __future__ import annotations

import os
from dataclasses import dataclass


class ProcessIdentityError(ValueError):
    """Raised when workload process identity is invalid."""


@dataclass(frozen=True, slots=True)
class ProcessIdentity:
    """Identity of the OS process created for one execution."""

    execution_id: str
    pid: int
    pgid: int

    def __post_init__(self) -> None:
        if not self.execution_id.strip():
            raise ProcessIdentityError("execution_id must not be empty")

        if self.pid <= 0:
            raise ProcessIdentityError("pid must be greater than zero")

        if self.pgid <= 0:
            raise ProcessIdentityError("pgid must be greater than zero")

    @classmethod
    def capture(cls, execution_id: str, pid: int) -> ProcessIdentity:
        """Capture and validate the process-group identity."""
        if pid <= 0:
            raise ProcessIdentityError("pid must be greater than zero")

        try:
            pgid = os.getpgid(pid)
        except OSError as exc:
            raise ProcessIdentityError(
                "unable to capture process-group identity"
            ) from exc

        return cls(
            execution_id=execution_id,
            pid=pid,
            pgid=pgid,
        )

    def matches(self, *, execution_id: str, pid: int, pgid: int) -> bool:
        """Return whether supplied identity matches this execution."""
        return (
            self.execution_id == execution_id
            and self.pid == pid
            and self.pgid == pgid
        )
