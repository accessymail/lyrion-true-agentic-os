"""Parent-to-child process-boundary qualification launcher.

This module qualifies the trusted child-entry boundary only.

It deliberately does NOT:
- apply Linux security controls;
- execute the workload;
- mutate the controller process;
- authorize capabilities;
- bypass the Capability Gateway;
- replace ProcessBoundary or SecureExecutor.

The parent transfers an integrity-bound LaunchHandoff through an inherited
anonymous pipe to a separately created child process.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from types import MappingProxyType

from lyrion.execution.process_boundary.bootstrap_contracts import (
    LaunchHandoff,
)

DEFAULT_MAX_HANDOFF_BYTES = 256 * 1024
DEFAULT_CHILD_TIMEOUT_SECONDS = 10.0
CHILD_ENTRY_MODULE = (
    "lyrion.execution.process_boundary.child_entry"
)


class ChildLaunchError(RuntimeError):
    """Raised when the parent-to-child qualification contract fails."""


@dataclass(frozen=True, slots=True)
class ChildLaunchResult:
    """Immutable observation of one qualified child bootstrap."""

    parent_pid: int
    child_pid: int
    child_returncode: int
    handoff_bytes: int

    @property
    def succeeded(self) -> bool:
        """Return whether the child bootstrap completed successfully."""
        return (
            self.child_returncode == 0
            and self.parent_pid != self.child_pid
        )


class ChildLauncher:
    """Launch the trusted child-entry point across a real process boundary."""

    def __init__(
        self,
        *,
        python_executable: str | None = None,
        max_handoff_bytes: int = DEFAULT_MAX_HANDOFF_BYTES,
        timeout_seconds: float = DEFAULT_CHILD_TIMEOUT_SECONDS,
    ) -> None:
        if max_handoff_bytes <= 0:
            raise ValueError("max_handoff_bytes must be positive")

        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        executable = python_executable or sys.executable

        if not executable:
            raise ValueError("python executable must not be empty")

        self._python_executable = executable
        self._max_handoff_bytes = max_handoff_bytes
        self._timeout_seconds = timeout_seconds

    @property
    def max_handoff_bytes(self) -> int:
        """Return the maximum serialized handoff size."""
        return self._max_handoff_bytes

    @property
    def timeout_seconds(self) -> float:
        """Return the child qualification timeout."""
        return self._timeout_seconds

    def qualify(self, handoff: LaunchHandoff) -> ChildLaunchResult:
        """Transfer one handoff to a separate child and qualify bootstrap."""
        payload = handoff.model_dump_json().encode("utf-8")

        if not payload:
            raise ChildLaunchError("serialized handoff is empty")

        if len(payload) > self._max_handoff_bytes:
            raise ChildLaunchError(
                "serialized handoff exceeds configured maximum"
            )

        parent_pid = os.getpid()
        read_fd, write_fd = os.pipe()

        child: subprocess.Popen[bytes] | None = None

        try:
            child = self._spawn_child(read_fd)

            os.close(read_fd)
            read_fd = -1

            with os.fdopen(
                write_fd,
                "wb",
                closefd=True,
            ) as stream:
                stream.write(payload)
                stream.flush()

            write_fd = -1

            try:
                returncode = child.wait(
                    timeout=self._timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                self._terminate_child(child)
                raise ChildLaunchError(
                    "child bootstrap timed out"
                ) from exc

            result = ChildLaunchResult(
                parent_pid=parent_pid,
                child_pid=child.pid,
                child_returncode=returncode,
                handoff_bytes=len(payload),
            )

            if result.child_pid == result.parent_pid:
                raise ChildLaunchError(
                    "child process identity is not distinct from parent"
                )

            if result.child_returncode != 0:
                raise ChildLaunchError(
                    "child bootstrap failed "
                    f"with return code {result.child_returncode}"
                )

            return result

        except OSError as exc:
            if child is not None and child.poll() is None:
                self._terminate_child(child)

            raise ChildLaunchError(
                "failed to establish parent-to-child boundary"
            ) from exc

        finally:
            if read_fd >= 0:
                os.close(read_fd)

            if write_fd >= 0:
                os.close(write_fd)

    def _spawn_child(
        self,
        read_fd: int,
    ) -> subprocess.Popen[bytes]:
        """Spawn only the trusted child-entry module."""
        command = (
            self._python_executable,
            "-m",
            CHILD_ENTRY_MODULE,
            "--handoff-fd",
            str(read_fd),
            "--max-handoff-bytes",
            str(self._max_handoff_bytes),
        )

        environment = MappingProxyType(
            {
                key: value
                for key, value in os.environ.items()
            }
        )

        return subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            close_fds=True,
            pass_fds=(read_fd,),
            cwd=os.getcwd(),
            env=dict(environment),
        )

    @staticmethod
    def _terminate_child(
        child: subprocess.Popen[bytes],
    ) -> None:
        """Terminate a failed qualification child."""
        if child.poll() is not None:
            return

        try:
            child.terminate()
            child.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()


__all__ = [
    "CHILD_ENTRY_MODULE",
    "DEFAULT_CHILD_TIMEOUT_SECONDS",
    "DEFAULT_MAX_HANDOFF_BYTES",
    "ChildLaunchError",
    "ChildLaunchResult",
    "ChildLauncher",
]
