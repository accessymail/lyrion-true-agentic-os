"""Bounded continuous runner for proactive intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from lyrion.core.types import (
    AutonomyLevel,
    DecisionId,
    TaskId,
)
from lyrion.events.models import Event
from lyrion.execution.contracts import ExecutionPlan
from lyrion.execution.sandbox import SandboxConfig
from lyrion.integration.proactive_execution import CapabilityIntent
from lyrion.piae.contracts import (
    DecisionCandidate,
    DecisionConstraints,
)
from lyrion.piae.proactive_cycle import (
    PIAEProactiveCycle,
    ProactiveCycleResult,
)
from lyrion.state.models import StateRecord


class ExecutionPlanFactory(Protocol):
    """Create a plan appropriate for one event."""

    def __call__(
        self,
        event: Event,
    ) -> ExecutionPlan:
        """Return an execution plan for the event."""


@dataclass(frozen=True)
class ContinuousRunnerConfig:
    """Explicit bounds for one continuous-runner invocation."""

    max_events_per_batch: int = 32

    def __post_init__(self) -> None:
        """Validate runner bounds."""
        if self.max_events_per_batch <= 0:
            raise ValueError(
                "max_events_per_batch must be greater than zero"
            )


@dataclass(frozen=True)
class ProactiveBatchResult:
    """Immutable result of bounded batch processing."""

    results: tuple[ProactiveCycleResult, ...]
    failed_indices: tuple[int, ...]

    @property
    def processed_count(self) -> int:
        """Return the number of successfully processed events."""
        return len(self.results)

    @property
    def failure_count(self) -> int:
        """Return the number of events that raised an exception."""
        return len(self.failed_indices)


class PIAEContinuousRunner:
    """Run bounded proactive cycles without an infinite loop."""

    def __init__(
        self,
        cycle: PIAEProactiveCycle,
        config: ContinuousRunnerConfig | None = None,
    ) -> None:
        """Initialize the continuous runner."""
        self._cycle = cycle
        self._config = config or ContinuousRunnerConfig()

    @property
    def cycle(self) -> PIAEProactiveCycle:
        """Return the underlying proactive cycle."""
        return self._cycle

    @property
    def config(self) -> ContinuousRunnerConfig:
        """Return the configured execution bounds."""
        return self._config

    def run_once(
        self,
        event: Event,
        *,
        candidates: tuple[DecisionCandidate, ...],
        intent: CapabilityIntent | None,
        plan: ExecutionPlan | None,
        sandbox: SandboxConfig | None,
        state_records: tuple[StateRecord, ...] = (),
        active_task_ids: tuple[TaskId, ...] = (),
        autonomy_level: AutonomyLevel | None = None,
        constraints: DecisionConstraints | None = None,
        decision_id: DecisionId | None = None,
        now: datetime | None = None,
    ) -> ProactiveCycleResult:
        """Process exactly one event."""
        effective_decision_id = decision_id or DecisionId(
            f"batch:{event.event_id}",
        )

        return self._cycle.process_event(
            event,
            candidates=candidates,
            intent=intent,
            plan=plan,
            sandbox=sandbox,
            state_records=state_records,
            active_task_ids=active_task_ids,
            autonomy_level=autonomy_level,
            constraints=constraints,
            decision_id=effective_decision_id,
            now=now,
        )

    def run_batch(
        self,
        events: tuple[Event, ...],
        *,
        candidates: tuple[DecisionCandidate, ...],
        intent: CapabilityIntent | None,
        plan_factory: ExecutionPlanFactory,
        sandbox: SandboxConfig | None,
        state_records: tuple[StateRecord, ...] = (),
        active_task_ids: tuple[TaskId, ...] = (),
        autonomy_level: AutonomyLevel | None = None,
        constraints: DecisionConstraints | None = None,
        now: datetime | None = None,
    ) -> ProactiveBatchResult:
        """Process a bounded ordered batch with failure isolation."""
        if len(events) > self._config.max_events_per_batch:
            raise ValueError(
                "event batch exceeds max_events_per_batch"
            )

        results: list[ProactiveCycleResult] = []
        failed_indices: list[int] = []

        for index, event in enumerate(events):
            try:
                plan = plan_factory(event)

                result = self.run_once(
                    event,
                    candidates=candidates,
                    intent=intent,
                    plan=plan,
                    sandbox=sandbox,
                    state_records=state_records,
                    active_task_ids=active_task_ids,
                    autonomy_level=autonomy_level,
                    constraints=constraints,
                    decision_id=DecisionId(
                        f"batch:{event.event_id}",
                    ),
                    now=now,
                )

                results.append(result)

            except Exception:
                failed_indices.append(index)

        return ProactiveBatchResult(
            results=tuple(results),
            failed_indices=tuple(failed_indices),
        )
