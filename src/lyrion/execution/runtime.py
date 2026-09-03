"""Deterministic runtime-control primitives for secure execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from lyrion.execution.contracts import ResourceLimits


class RuntimeState(StrEnum):
    """Lifecycle state of runtime control."""

    READY = "READY"
    RUNNING = "RUNNING"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    TIMED_OUT = "TIMED_OUT"
    TERMINATED = "TERMINATED"
    COMPLETED = "COMPLETED"


class RuntimeViolation(StrEnum):
    """Normalized runtime-control violations."""

    TIMEOUT = "TIMEOUT"
    CPU_LIMIT_EXCEEDED = "CPU_LIMIT_EXCEEDED"
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    OUTPUT_LIMIT_EXCEEDED = "OUTPUT_LIMIT_EXCEEDED"
    CANCELLED = "CANCELLED"
    TERMINATED = "TERMINATED"


@dataclass(frozen=True, slots=True)
class RuntimeBudget:
    """Immutable runtime budget derived from execution limits."""

    started_at: datetime
    deadline: datetime
    max_cpu_seconds: float
    max_memory_mb: int
    max_output_bytes: int

    @classmethod
    def from_limits(
        cls,
        limits: ResourceLimits,
        *,
        started_at: datetime,
    ) -> RuntimeBudget:
        """Create a runtime budget from explicit resource limits."""
        if started_at.tzinfo is None or started_at.utcoffset() is None:
            raise ValueError("started_at must be timezone-aware")

        return cls(
            started_at=started_at.astimezone(UTC),
            deadline=(
                started_at.astimezone(UTC)
                + timedelta(seconds=limits.max_runtime_seconds)
            ),
            max_cpu_seconds=limits.max_cpu_seconds,
            max_memory_mb=limits.max_memory_mb,
            max_output_bytes=limits.max_output_bytes,
        )


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    """Immutable observation of runtime-control state."""

    state: RuntimeState
    now: datetime
    elapsed_seconds: float
    cpu_seconds: float
    memory_mb: int
    output_bytes: int
    violation: RuntimeViolation | None = None


class RuntimeController:
    """Evaluate runtime usage against a fixed execution budget."""

    def __init__(self, budget: RuntimeBudget) -> None:
        """Initialize runtime control with an immutable budget."""
        if budget.deadline < budget.started_at:
            raise ValueError("runtime deadline cannot precede start")

        self._budget = budget
        self._state = RuntimeState.READY
        self._violation: RuntimeViolation | None = None

    @property
    def budget(self) -> RuntimeBudget:
        """Return the configured runtime budget."""
        return self._budget

    @property
    def state(self) -> RuntimeState:
        """Return the current runtime state."""
        return self._state

    @property
    def violation(self) -> RuntimeViolation | None:
        """Return the current runtime violation, if any."""
        return self._violation

    def start(self) -> None:
        """Transition from READY to RUNNING."""
        if self._state is not RuntimeState.READY:
            raise RuntimeError(
                f"cannot start runtime from state {self._state}"
            )

        self._state = RuntimeState.RUNNING
        self._violation = None

    def request_cancel(self) -> None:
        """Request cancellation of a running execution."""
        if self._state is RuntimeState.READY:
            self._state = RuntimeState.CANCEL_REQUESTED
            self._violation = RuntimeViolation.CANCELLED
            return

        if self._state is RuntimeState.RUNNING:
            self._state = RuntimeState.CANCEL_REQUESTED
            self._violation = RuntimeViolation.CANCELLED
            return

        raise RuntimeError(
            f"cannot cancel runtime from state {self._state}"
        )

    def terminate(self) -> None:
        """Mark the runtime as terminated."""
        if self._state in {
            RuntimeState.COMPLETED,
            RuntimeState.TERMINATED,
            RuntimeState.TIMED_OUT,
        }:
            raise RuntimeError(
                f"cannot terminate runtime from state {self._state}"
            )

        self._state = RuntimeState.TERMINATED
        self._violation = RuntimeViolation.TERMINATED

    def complete(self) -> None:
        """Mark a running runtime as completed."""
        if self._state is not RuntimeState.RUNNING:
            raise RuntimeError(
                f"cannot complete runtime from state {self._state}"
            )

        self._state = RuntimeState.COMPLETED
        self._violation = None

    def snapshot(
        self,
        *,
        now: datetime,
        cpu_seconds: float = 0.0,
        memory_mb: int = 0,
        output_bytes: int = 0,
    ) -> RuntimeSnapshot:
        """Evaluate the current runtime observation."""
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")

        if cpu_seconds < 0:
            raise ValueError("cpu_seconds must not be negative")

        if memory_mb < 0:
            raise ValueError("memory_mb must not be negative")

        if output_bytes < 0:
            raise ValueError("output_bytes must not be negative")

        current_time = now.astimezone(UTC)
        elapsed_seconds = (
            current_time - self._budget.started_at
        ).total_seconds()

        if elapsed_seconds < 0:
            raise ValueError("now cannot precede runtime start")

        if self._state in {
            RuntimeState.COMPLETED,
            RuntimeState.TERMINATED,
            RuntimeState.TIMED_OUT,
        }:
            return RuntimeSnapshot(
                state=self._state,
                now=current_time,
                elapsed_seconds=elapsed_seconds,
                cpu_seconds=cpu_seconds,
                memory_mb=memory_mb,
                output_bytes=output_bytes,
                violation=self._violation,
            )

        violation = self._check_limits(
            current_time=current_time,
            cpu_seconds=cpu_seconds,
            memory_mb=memory_mb,
            output_bytes=output_bytes,
        )

        if violation is not None:
            self._violation = violation

            if violation is RuntimeViolation.TIMEOUT:
                self._state = RuntimeState.TIMED_OUT
            elif violation is RuntimeViolation.CANCELLED:
                self._state = RuntimeState.CANCEL_REQUESTED
            else:
                self._state = RuntimeState.TERMINATED

        return RuntimeSnapshot(
            state=self._state,
            now=current_time,
            elapsed_seconds=elapsed_seconds,
            cpu_seconds=cpu_seconds,
            memory_mb=memory_mb,
            output_bytes=output_bytes,
            violation=self._violation,
        )

    def _check_limits(
        self,
        *,
        current_time: datetime,
        cpu_seconds: float,
        memory_mb: int,
        output_bytes: int,
    ) -> RuntimeViolation | None:
        """Return the first applicable runtime violation."""
        if self._state is RuntimeState.CANCEL_REQUESTED:
            return RuntimeViolation.CANCELLED

        if current_time >= self._budget.deadline:
            return RuntimeViolation.TIMEOUT

        if cpu_seconds > self._budget.max_cpu_seconds:
            return RuntimeViolation.CPU_LIMIT_EXCEEDED

        if memory_mb > self._budget.max_memory_mb:
            return RuntimeViolation.MEMORY_LIMIT_EXCEEDED

        if output_bytes > self._budget.max_output_bytes:
            return RuntimeViolation.OUTPUT_LIMIT_EXCEEDED

        return None

    def require_within_limits(
        self,
        *,
        now: datetime,
        cpu_seconds: float = 0.0,
        memory_mb: int = 0,
        output_bytes: int = 0,
    ) -> RuntimeSnapshot:
        """Return a valid snapshot or fail closed."""
        snapshot = self.snapshot(
            now=now,
            cpu_seconds=cpu_seconds,
            memory_mb=memory_mb,
            output_bytes=output_bytes,
        )

        if snapshot.violation is not None:
            raise RuntimeError(
                "runtime limit violation: "
                + snapshot.violation.value
            )

        return snapshot
