"""Secure per-opportunity context binding for PIAE."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from lyrion.core.types import AutonomyLevel, DecisionId, TaskId
from lyrion.execution.contracts import ExecutionPlan
from lyrion.execution.sandbox import SandboxConfig
from lyrion.integration.proactive_execution import CapabilityIntent
from lyrion.piae.contracts import (
    DecisionConstraints,
    Opportunity,
)
from lyrion.state.models import StateRecord

CapabilityIntentFactory = Callable[
    [Opportunity],
    CapabilityIntent | None,
]

ExecutionPlanFactory = Callable[
    [Opportunity],
    ExecutionPlan | None,
]

SandboxFactory = Callable[
    [Opportunity],
    SandboxConfig | None,
]


@dataclass(frozen=True)
class OpportunityContext:
    """Immutable context bound to exactly one opportunity."""

    opportunity: Opportunity
    decision_id: DecisionId
    state_records: tuple[StateRecord, ...]
    active_task_ids: tuple[TaskId, ...]
    autonomy_level: AutonomyLevel
    constraints: DecisionConstraints
    intent: CapabilityIntent | None
    plan: ExecutionPlan | None
    sandbox: SandboxConfig | None


class OpportunityContextFactory(Protocol):
    """Build execution context specifically for one opportunity."""

    def build(
        self,
        opportunity: Opportunity,
        *,
        now: datetime,
    ) -> OpportunityContext:
        """Build a validated opportunity-specific context."""


class DeterministicOpportunityContextFactory:
    """Create explicit, identity-bound context for one opportunity."""

    def __init__(
        self,
        *,
        state_records: tuple[StateRecord, ...] = (),
        active_task_ids: tuple[TaskId, ...] = (),
        autonomy_level: AutonomyLevel,
        constraints: DecisionConstraints,
        intent_factory: CapabilityIntentFactory | None = None,
        plan_factory: ExecutionPlanFactory | None = None,
        sandbox_factory: SandboxFactory | None = None,
    ) -> None:
        """Initialize the deterministic context factory."""
        self._state_records = state_records
        self._active_task_ids = active_task_ids
        self._autonomy_level = autonomy_level
        self._constraints = constraints
        self._intent_factory = intent_factory
        self._plan_factory = plan_factory
        self._sandbox_factory = sandbox_factory

    def build(
        self,
        opportunity: Opportunity,
        *,
        now: datetime,
    ) -> OpportunityContext:
        """Build a validated context for exactly one opportunity."""
        if (
            now.tzinfo is None
            or now.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        current_time = now.astimezone(UTC)

        if opportunity.is_expired(current_time):
            raise ValueError(
                "cannot bind an expired opportunity"
            )

        decision_id = DecisionId(
            f"opportunity:{opportunity.opportunity_id}",
        )

        intent = (
            self._intent_factory(opportunity)
            if self._intent_factory is not None
            else None
        )

        plan = (
            self._plan_factory(opportunity)
            if self._plan_factory is not None
            else None
        )

        sandbox = (
            self._sandbox_factory(opportunity)
            if self._sandbox_factory is not None
            else None
        )

        if plan is not None:
            expected_execution_id = (
                f"execution:capreq:{decision_id}"
            )

            if plan.execution_id != expected_execution_id:
                raise ValueError(
                    "execution plan is not bound to opportunity"
                )

        return OpportunityContext(
            opportunity=opportunity,
            decision_id=decision_id,
            state_records=self._state_records,
            active_task_ids=self._active_task_ids,
            autonomy_level=self._autonomy_level,
            constraints=self._constraints,
            intent=intent,
            plan=plan,
            sandbox=sandbox,
        )
