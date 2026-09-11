"""Runtime failure state for provider-neutral model routing."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class ModelTarget:
    """Stable identity for one routable model target."""

    provider: str
    model: str
    execution_target_name: str

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("provider must not be empty")
        if not self.model.strip():
            raise ValueError("model must not be empty")
        if not self.execution_target_name.strip():
            raise ValueError("execution_target_name must not be empty")


@dataclass(frozen=True)
class ModelFailurePolicy:
    """Bounded temporary exclusion policy for failed model targets."""

    failure_threshold: int = 1
    initial_cooldown_seconds: float = 5.0
    max_cooldown_seconds: float = 60.0
    multiplier: float = 2.0

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if self.initial_cooldown_seconds < 0.0:
            raise ValueError("initial_cooldown_seconds must not be negative")
        if self.max_cooldown_seconds < self.initial_cooldown_seconds:
            raise ValueError(
                "max_cooldown_seconds must be at least initial_cooldown_seconds",
            )
        if self.multiplier < 1.0:
            raise ValueError("multiplier must be at least 1")

    def cooldown_for_failure(self, failure_count: int) -> float:
        """Return the bounded cooldown after a failure."""
        if failure_count < 1:
            raise ValueError("failure_count must be at least 1")
        return min(
            self.max_cooldown_seconds,
            self.initial_cooldown_seconds * self.multiplier ** (failure_count - 1),
        )


@dataclass(frozen=True)
class ModelFailureRecord:
    """Immutable runtime failure record for one target."""

    failure_count: int
    excluded_until: float


class ModelFailureTracker:
    """Track temporary runtime exclusions without mutating model metadata."""

    def __init__(
        self,
        *,
        policy: ModelFailurePolicy | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._policy = policy or ModelFailurePolicy()
        self._clock = clock
        self._records: dict[ModelTarget, ModelFailureRecord] = {}

    @property
    def policy(self) -> ModelFailurePolicy:
        """Return the configured failure policy."""
        return self._policy

    def record_failure(self, target: ModelTarget) -> ModelFailureRecord:
        """Record a failure and apply exclusion after the threshold."""
        previous = self._records.get(target)
        failure_count = 1 if previous is None else previous.failure_count + 1

        if failure_count < self._policy.failure_threshold:
            excluded_until = self._clock()
        else:
            cooldown = self._policy.cooldown_for_failure(failure_count)
            excluded_until = self._clock() + cooldown

        record = ModelFailureRecord(
            failure_count=failure_count,
            excluded_until=excluded_until,
        )
        self._records[target] = record
        return record

    def record_success(self, target: ModelTarget) -> None:
        """Clear runtime failure state after a successful invocation."""
        self._records.pop(target, None)

    def is_excluded(self, target: ModelTarget) -> bool:
        """Return whether a target is currently temporarily excluded."""
        record = self._records.get(target)
        if record is None:
            return False
        if record.failure_count < self._policy.failure_threshold:
            return False
        if self._clock() >= record.excluded_until:
            self._records.pop(target, None)
            return False
        return True

    def excluded_targets(self) -> frozenset[ModelTarget]:
        """Return currently excluded targets, cleaning expired state."""
        return frozenset(
            target for target in tuple(self._records)
            if self.is_excluded(target)
        )

    def failure_record(self, target: ModelTarget) -> ModelFailureRecord | None:
        """Return the active failure record for a target, if any."""
        if not self.is_excluded(target):
            return None
        return self._records[target]
