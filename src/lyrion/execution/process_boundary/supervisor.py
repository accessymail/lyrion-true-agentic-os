"""Controlled real-process boundary for Lyrion.

This module owns the operating-system process boundary only.

Authorization remains outside this module. The boundary accepts an already
authorized launch specification and never grants capabilities itself.

Security properties:
- shell execution is never used;
- argv is immutable and explicit;
- environment is explicitly supplied;
- file descriptors are closed on exec;
- the child becomes a new session/process group;
- stdout/stderr are bounded;
- timeout terminates the complete process group;
- cancellation/termination are fail-closed;
- the returned identity is bound to the observed child PID/PGID;
- no arbitrary privilege escalation is attempted.
"""

from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


class ProcessBoundaryError(RuntimeError):
    """Base exception for controlled process-boundary failures."""


class ProcessLaunchRejected(ProcessBoundaryError):
    """Raised when a launch specification violates boundary invariants."""


@dataclass(frozen=True, slots=True)
class ProcessLaunchSpec:
    """Immutable specification for one already-authorized workload launch."""

    execution_id: str
    argv: tuple[str, ...]
    cwd: Path
    environment: Mapping[str, str]
    timeout_seconds: float
    max_output_bytes: int = 1_048_576

    def __post_init__(self) -> None:
        if not self.execution_id.strip():
            raise ProcessLaunchRejected("execution_id must not be empty")

        if not self.argv:
            raise ProcessLaunchRejected("argv must not be empty")

        if any(not isinstance(item, str) or not item for item in self.argv):
            raise ProcessLaunchRejected(
                "argv must contain only non-empty strings"
            )

        if self.timeout_seconds <= 0:
            raise ProcessLaunchRejected(
                "timeout_seconds must be greater than zero"
            )

        if self.max_output_bytes <= 0:
            raise ProcessLaunchRejected(
                "max_output_bytes must be greater than zero"
            )

        if not self.cwd.is_absolute():
            raise ProcessLaunchRejected("cwd must be an absolute path")

        for key, value in self.environment.items():
            if not isinstance(key, str) or not key:
                raise ProcessLaunchRejected(
                    "environment keys must be non-empty strings"
                )
            if "\x00" in key or "\x00" in value:
                raise ProcessLaunchRejected(
                    "environment must not contain NUL characters"
                )

        for argument in self.argv:
            if "\x00" in argument:
                raise ProcessLaunchRejected(
                    "argv must not contain NUL characters"
                )


@dataclass(frozen=True, slots=True)
class ProcessResult:
    """Immutable observation of a completed workload process."""

    execution_id: str
    pid: int
    pgid: int
    exit_code: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool
    terminated: bool
    duration_seconds: float

    @property
    def completed_successfully(self) -> bool:
        """Return whether the workload exited normally with status zero."""
        return (
            self.exit_code == 0
            and not self.timed_out
            and not self.terminated
        )


class _BoundedOutputBuffer:
    """Thread-safe bounded byte collector for one process output stream."""

    __slots__ = ("_data", "_limit", "_lock")

    def __init__(self, limit: int) -> None:
        self._data = bytearray()
        self._limit = limit
        self._lock = threading.Lock()

    def append(self, chunk: bytes) -> None:
        """Retain only bytes that fit within the configured bound."""
        if not chunk:
            return

        with self._lock:
            remaining = self._limit - len(self._data)
            if remaining > 0:
                self._data.extend(chunk[:remaining])

    @property
    def value(self) -> bytes:
        """Return the bounded output snapshot."""
        with self._lock:
            return bytes(self._data)


class ProcessBoundary:
    """Create and supervise one controlled real workload process."""

    def __init__(self, *, termination_grace_seconds: float = 2.0) -> None:
        if termination_grace_seconds <= 0:
            raise ValueError("termination_grace_seconds must be greater than zero")

        self._termination_grace_seconds = termination_grace_seconds

    def run(self, spec: ProcessLaunchSpec) -> ProcessResult:
        """Launch and supervise one workload process.

        This method does not authorize execution and does not apply Linux
        security policy. Those responsibilities belong to the caller and
        trusted enforcement layer.
        """
        if not spec.cwd.is_dir():
            raise ProcessLaunchRejected(
                f"working directory does not exist: {spec.cwd}"
            )

        started = time.monotonic()

        try:
            process = subprocess.Popen(
                list(spec.argv),
                cwd=spec.cwd,
                env=dict(spec.environment),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                close_fds=True,
                start_new_session=True,
                text=False,
            )
        except (OSError, ValueError) as exc:
            raise ProcessBoundaryError(
                f"controlled process launch failed: {type(exc).__name__}"
            ) from exc

        pid = process.pid

        try:
            pgid = os.getpgid(pid)
        except OSError as exc:
            self._terminate_process_group(pid)
            raise ProcessBoundaryError(
                "unable to establish workload process-group identity"
            ) from exc

        stdout_buffer = _BoundedOutputBuffer(spec.max_output_bytes)
        stderr_buffer = _BoundedOutputBuffer(spec.max_output_bytes)

        stdout_thread = threading.Thread(
            target=self._drain_output,
            args=(process.stdout, stdout_buffer),
            name=f"lyrion-stdout-{pid}",
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=self._drain_output,
            args=(process.stderr, stderr_buffer),
            name=f"lyrion-stderr-{pid}",
            daemon=True,
        )

        stdout_thread.start()
        stderr_thread.start()

        timed_out = False
        terminated = False

        try:
            process.wait(timeout=spec.timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            self._terminate_process_group(pid)

            try:
                process.wait(timeout=self._termination_grace_seconds)
            except subprocess.TimeoutExpired:
                self._kill_process_group(pid)
                process.wait()
        except BaseException:
            terminated = True
            self._terminate_process_group(pid)

            try:
                process.wait(timeout=self._termination_grace_seconds)
            except subprocess.TimeoutExpired:
                self._kill_process_group(pid)
                process.wait()
            raise
        finally:
            stdout_thread.join(timeout=self._termination_grace_seconds)
            stderr_thread.join(timeout=self._termination_grace_seconds)

            if stdout_thread.is_alive() or stderr_thread.is_alive():
                self._kill_process_group(pid)
                stdout_thread.join()
                stderr_thread.join()

        duration = time.monotonic() - started

        return ProcessResult(
            execution_id=spec.execution_id,
            pid=pid,
            pgid=pgid,
            exit_code=process.returncode,
            stdout=stdout_buffer.value,
            stderr=stderr_buffer.value,
            timed_out=timed_out,
            terminated=terminated,
            duration_seconds=duration,
        )

    @staticmethod
    def _drain_output(
        stream: BinaryIO | None,
        buffer: _BoundedOutputBuffer,
    ) -> None:
        """Drain one process stream while retaining only bounded output."""
        if stream is None:
            return

        while True:
            chunk = stream.read(8192)
            if not chunk:
                return
            buffer.append(chunk)

    def _terminate_process_group(self, pid: int) -> None:
        """Request graceful termination of the complete workload group."""
        self._signal_process_group(pid, signal.SIGTERM)

    def _kill_process_group(self, pid: int) -> None:
        """Force termination of the complete workload group."""
        self._signal_process_group(pid, signal.SIGKILL)

    @staticmethod
    def _signal_process_group(pid: int, sig: signal.Signals) -> None:
        """Signal the workload's process group when it still exists."""
        try:
            pgid = os.getpgid(pid)
        except OSError:
            return

        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            return
        except PermissionError as exc:
            raise ProcessBoundaryError(
                "process-group termination was denied"
            ) from exc
