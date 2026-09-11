"""Single-cycle proactive intelligence pipeline."""

from __future__ import annotations

from datetime import UTC, datetime

from lyrion.capabilities.gateway import ExecutionAdmission
from lyrion.core.types import AutonomyLevel, DecisionId, TaskId
from lyrion.events.models import Event
from lyrion.execution.contracts import ExecutionPlan, ExecutionResult
from lyrion.execution.sandbox import SandboxConfig
from lyrion.integration.proactive_execution import CapabilityIntent
from lyrion.piae.action_loop import PIAEActionCycleResult, PIAEActionLoop
from lyrion.piae.contracts import (
    DecisionCandidate,
    DecisionConstraints,
    DecisionContext,
)
from lyrion.piae.opportunity_detector import OpportunityDetector
from lyrion.state.models import StateRecord


class ProactiveCycleResult:
    """Result of one event-to-action proactive cycle."""

    def __init__(
        self,
        *,
        event: Event,
        detected_opportunity: object,
        action_cycle: PIAEActionCycleResult | None,
    ) -> None:
        self.event = event
        self.detected_opportunity = detected_opportunity
        self.action_cycle = action_cycle

    @property
    def opportunity_detected(self) -> bool:
        """Return whether an opportunity was detected."""
        return self.detected_opportunity is not None

    @property
    def execution_result(self) -> ExecutionResult | None:
        """Return the execution result when execution occurred."""
        if self.action_cycle is None:
            return None

        return self.action_cycle.execution_result

    @property
    def execution_admission(self) -> ExecutionAdmission | None:
        """Return the execution admission when one was created."""
        if self.action_cycle is None:
            return None

        return self.action_cycle.admission


class PIAEProactiveCycle:
    """Connect event observation to one bounded PIAE action cycle."""

    def __init__(
        self,
        detector: OpportunityDetector,
        action_loop: PIAEActionLoop,
    ) -> None:
        """Initialize the proactive cycle."""
        self._detector = detector
        self._action_loop = action_loop

    @property
    def detector(self) -> OpportunityDetector:
        """Return the opportunity detector."""
        return self._detector

    @property
    def action_loop(self) -> PIAEActionLoop:
        """Return the PIAE action loop."""
        return self._action_loop

    def process_event(
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
        """Process one event through detection and PIAE action."""
        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        opportunity = self._detector.detect(
            event,
            now=current_time,
        )

        if opportunity is None:
            return ProactiveCycleResult(
                event=event,
                detected_opportunity=None,
                action_cycle=None,
            )

        if autonomy_level is None:
            raise ValueError(
                "autonomy_level is required when an opportunity is detected"
            )

        if constraints is None:
            raise ValueError(
                "constraints are required when an opportunity is detected"
            )

        context = DecisionContext(
            opportunity=opportunity,
            state_records=state_records,
            active_task_ids=active_task_ids,
            autonomy_level=autonomy_level,
            constraints=constraints,
            now=current_time,
        )

        action_cycle = self._action_loop.run_once(
            context,
            candidates,
            intent,
            plan,
            sandbox,
            decision_id=decision_id,
            now=current_time,
        )

        return ProactiveCycleResult(
            event=event,
            detected_opportunity=opportunity,
            action_cycle=action_cycle,
        )
