"""Trusted child-process entry point for the LYRION process boundary.

This module establishes the child-side security boundary before any native
enforcement is introduced.

Security invariants:
- The handoff is transferred through an inherited file descriptor.
- The handoff is never supplied through command-line arguments.
- The handoff is bounded before parsing.
- The integrity digest is verified before bootstrap acceptance.
- The ChildExecutionContext is created inside the child process.
- PID/PGID identity is verified before handoff acceptance.
- No operating-system security mutation occurs in this increment.
"""

from __future__ import annotations

import argparse
import os
from typing import BinaryIO

from lyrion.execution.process_boundary.bootstrap import (
    ChildBootstrap,
)
from lyrion.execution.process_boundary.bootstrap_contracts import (
    BootstrapContractError,
    LaunchHandoff,
)
from lyrion.execution.process_boundary.child_context import (
    ChildContextError,
    ChildExecutionContext,
)

DEFAULT_HANDOFF_FD = 3
DEFAULT_MAX_HANDOFF_BYTES = 1_048_576


class ChildEntryError(RuntimeError):
    """Raised when trusted child-entry initialization fails."""


def read_handoff(
    stream: BinaryIO,
    *,
    max_bytes: int = DEFAULT_MAX_HANDOFF_BYTES,
) -> LaunchHandoff:
    """Read and validate one bounded serialized launch handoff."""
    if max_bytes <= 0:
        raise ChildEntryError(
            "maximum handoff size must be greater than zero"
        )

    data = stream.read(max_bytes + 1)

    if len(data) > max_bytes:
        raise ChildEntryError(
            "launch handoff exceeds maximum permitted size"
        )

    if not data:
        raise ChildEntryError(
            "launch handoff is empty"
        )

    try:
        handoff = LaunchHandoff.model_validate_json(data)
    except Exception as exc:
        raise ChildEntryError(
            "launch handoff deserialization failed"
        ) from exc

    try:
        handoff.verify_integrity()
    except BootstrapContractError as exc:
        raise ChildEntryError(
            "launch handoff integrity verification failed"
        ) from exc

    return handoff


def establish_child_bootstrap(
    handoff: LaunchHandoff,
) -> ChildBootstrap:
    """Establish the verified bootstrap inside the current child process."""
    try:
        context = ChildExecutionContext.create(handoff)

        bootstrap = ChildBootstrap(handoff)
        bootstrap.bind_identity(handoff.execution_id)
        bootstrap.bind_process_context(context)
        bootstrap.validate_handoff()

        return bootstrap
    except (ChildContextError, BootstrapContractError) as exc:
        raise ChildEntryError(
            "child bootstrap establishment failed"
        ) from exc


def _open_handoff_fd(fd: int) -> BinaryIO:
    """Open the inherited handoff descriptor without taking ownership."""
    if fd < 0:
        raise ChildEntryError(
            "handoff file descriptor must not be negative"
        )

    try:
        return os.fdopen(
            os.dup(fd),
            "rb",
            closefd=True,
        )
    except OSError as exc:
        raise ChildEntryError(
            "unable to open inherited handoff descriptor"
        ) from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="LYRION trusted child-entry bootstrap",
    )
    parser.add_argument(
        "--handoff-fd",
        type=int,
        default=DEFAULT_HANDOFF_FD,
    )
    parser.add_argument(
        "--max-handoff-bytes",
        type=int,
        default=DEFAULT_MAX_HANDOFF_BYTES,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the contract-only trusted child bootstrap."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        with _open_handoff_fd(args.handoff_fd) as stream:
            handoff = read_handoff(
                stream,
                max_bytes=args.max_handoff_bytes,
            )

        bootstrap = establish_child_bootstrap(handoff)

        if bootstrap.child_context is None:
            raise ChildEntryError(
                "child bootstrap completed without a process context"
            )

        bootstrap.child_context.verify_current_process()
        bootstrap.child_context.verify_handoff()

        return 0
    except ChildEntryError:
        return 70


__all__ = [
    "DEFAULT_HANDOFF_FD",
    "DEFAULT_MAX_HANDOFF_BYTES",
    "ChildEntryError",
    "establish_child_bootstrap",
    "main",
    "read_handoff",
]


if __name__ == "__main__":
    raise SystemExit(main())
