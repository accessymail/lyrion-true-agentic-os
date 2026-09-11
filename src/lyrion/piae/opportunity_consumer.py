"""Queue-driven PIAE opportunity consumer."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from lyrion.core.types import AutonomyLevel, DecisionId, TaskId
from lyrion.execution.contracts import ExecutionPlan
from lyrion.execution.sandbox import SandboxConfig
from lyrion.integration.proactive_execution import CapabilityIntent
from lyrion.piae.action_loop import (
    PIAEActionCycleResult,
    PIAEActionLoop,
)
from lyrion.piae.contracts import (
    DecisionCandidate,
    DecisionConstraints,
    DecisionContext,
    Opportunity,
)
from lyrion.piae.opportunity_binding import OpportunityContextFactory
from lyrion.piae.opportunity_queue import OpportunityQueue
from lyrion.state.models import StateRecord

CandidateFactory = Callable[
    [Opportunity],
    tuple[DecisionCandidate, ...],
]


class OpportunityConsumer:
    """Consume queued opportunities through the PIAE action loop."""

    def __init__(
        self,
        queue: OpportunityQueue,
        action_loop: PIAEActionLoop,
    ) -> None:
        """Initialize the queue consumer."""
        self._queue = queue
        self._action_loop = action_loop

    @property
    def queue(self) -> OpportunityQueue:
        """Return the opportunity queue."""
        return self._queue

    @property
    def action_loop(self) -> PIAEActionLoop:
        """Return the PIAE action loop."""
        return self._action_loop

    def consume_once(
        self,
        *,
        candidates: tuple[DecisionCandidate, ...],
        intent: CapabilityIntent | None,
        plan: ExecutionPlan | None,
        sandbox: SandboxConfig | None,
        state_records: tuple[StateRecord, ...] = (),
        active_task_ids: tuple[TaskId, ...] = (),
        autonomy_level: AutonomyLevel,
        constraints: DecisionConstraints,
        now: datetime | None = None,
    ) -> PIAEActionCycleResult | None:
        """Consume the highest-priority eligible opportunity."""
        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        opportunity = self._queue.dequeue(
            now=current_time,
        )

        if opportunity is None:
            return None

        if opportunity.is_expired(current_time):
            return None

        context = DecisionContext(
            opportunity=opportunity,
            state_records=state_records,
            active_task_ids=active_task_ids,
            autonomy_level=autonomy_level,
            constraints=constraints,
            now=current_time,
        )

        return self._action_loop.run_once(
            context,
            candidates,
            intent,
            plan,
            sandbox,
            decision_id=DecisionId(
                f"opportunity:{opportunity.opportunity_id}",
            ),
            now=current_time,
        )

    async def consume_bound_once_persistent(
        self,
        *,
        context_factory: OpportunityContextFactory,
        candidates_factory: CandidateFactory,
        worker_id: str,
        lease_id: str,
        now: datetime | None = None,
    ) -> PIAEActionCycleResult | None:
        """Consume one opportunity through durable execution."""
        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        opportunity = self._queue.dequeue(
            now=current_time,
        )

        if opportunity is None:
            return None

        context = context_factory.build(
            opportunity,
            now=current_time,
        )

        candidates = candidates_factory(
            opportunity,
        )

        decision_context = DecisionContext(
            opportunity=context.opportunity,
            state_records=context.state_records,
            active_task_ids=context.active_task_ids,
            autonomy_level=context.autonomy_level,
            constraints=context.constraints,
            now=current_time,
        )

        return await self._action_loop.run_once_persistent(
            decision_context,
            candidates,
            context.intent,
            context.plan,
            context.sandbox,
            worker_id=worker_id,
            lease_id=lease_id,
            decision_id=context.decision_id,
            now=current_time,
        )

    def consume_bound_once(
        self,
        *,
        context_factory: OpportunityContextFactory,
        candidates_factory: CandidateFactory,
        now: datetime | None = None,
    ) -> PIAEActionCycleResult | None:
        """Consume one opportunity using isolated bound context."""
        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        opportunity = self._queue.dequeue(
            now=current_time,
        )

        if opportunity is None:
            return None

        context = context_factory.build(
            opportunity,
            now=current_time,
        )

        candidates = candidates_factory(
            opportunity,
        )

        decision_context = DecisionContext(
            opportunity=context.opportunity,
            state_records=context.state_records,
            active_task_ids=context.active_task_ids,
            autonomy_level=context.autonomy_level,
            constraints=context.constraints,
            now=current_time,
        )

        return self._action_loop.run_once(
            decision_context,
            candidates,
            context.intent,
            context.plan,
            context.sandbox,
            decision_id=context.decision_id,
            now=current_time,
        )
