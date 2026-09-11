"""Deterministic end-to-end PIAE action loop."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict

from lyrion.capabilities.contracts import CapabilityRequest
from lyrion.capabilities.gateway import ExecutionAdmission
from lyrion.core.types import DecisionId
from lyrion.execution.contracts import ExecutionPlan, ExecutionResult
from lyrion.execution.sandbox import SandboxConfig
from lyrion.integration.proactive_execution import (
    CapabilityIntent,
    ProactiveExecutionCoordinator,
)
from lyrion.persistence.execution_runner import (
    PersistentExecutionRunner,
)
from lyrion.piae.contracts import (
    DecisionCandidate,
    DecisionContext,
    DecisionResult,
)


class PIAEActionCycleResult(BaseModel):
    """Immutable result of one deterministic PIAE action cycle."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    decision: DecisionResult
    capability_request: CapabilityRequest | None = None
    admission: ExecutionAdmission | None = None
    execution_result: ExecutionResult | None = None

    @property
    def executed(self) -> bool:
        """Return whether the cycle reached secure execution."""
        return self.execution_result is not None


class PIAEActionLoop:
    """Coordinate one bounded PIAE decision-to-action cycle."""

    def __init__(
        self,
        coordinator: ProactiveExecutionCoordinator,
        *,
        persistent_runner: PersistentExecutionRunner | None = None,
    ) -> None:
        """Initialize the action loop."""
        self._coordinator = coordinator
        self._persistent_runner = persistent_runner

    @property
    def coordinator(self) -> ProactiveExecutionCoordinator:
        """Return the underlying secure-execution coordinator."""
        return self._coordinator

    def run_once(
        self,
        context: DecisionContext,
        candidates: tuple[DecisionCandidate, ...],
        intent: CapabilityIntent | None,
        plan: ExecutionPlan | None,
        sandbox: SandboxConfig | None,
        *,
        decision_id: DecisionId | None = None,
        input_context_ref: str = "action-loop",
        now: datetime | None = None,
    ) -> PIAEActionCycleResult:
        """Run exactly one bounded PIAE action cycle."""
        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        decision = self._coordinator.decide(
            context,
            candidates,
            decision_id=decision_id,
            input_context_ref=input_context_ref,
        )

        if decision.selected_action.value != "EXECUTE":
            return PIAEActionCycleResult(
                decision=decision,
            )

        if intent is None:
            raise ValueError(
                "CapabilityIntent is required for EXECUTE decisions"
            )

        if plan is None:
            raise ValueError(
                "ExecutionPlan is required for EXECUTE decisions"
            )

        if sandbox is None:
            raise ValueError(
                "SandboxConfig is required for EXECUTE decisions"
            )

        request = self._coordinator.create_capability_request(
            decision,
            intent,
            now=current_time,
        )

        admission = self._coordinator.admit(
            request,
            now=current_time,
        )

        execution_result = self._coordinator.execute(
            admission,
            plan,
            sandbox,
            now=current_time,
        )

        return PIAEActionCycleResult(
            decision=decision,
            capability_request=request,
            admission=admission,
            execution_result=execution_result,
        )

    async def run_once_persistent(
        self,
        context: DecisionContext,
        candidates: tuple[DecisionCandidate, ...],
        intent: CapabilityIntent | None,
        plan: ExecutionPlan | None,
        sandbox: SandboxConfig | None,
        *,
        worker_id: str,
        lease_id: str,
        decision_id: DecisionId | None = None,
        input_context_ref: str = "action-loop",
        now: datetime | None = None,
    ) -> PIAEActionCycleResult:
        """Run one action cycle through durable execution persistence."""
        runner = self._persistent_runner
        if runner is None:
            raise RuntimeError(
                "persistent execution runner is not configured"
            )

        current_time = now or datetime.now(UTC)

        if (
            current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise ValueError("now must be timezone-aware")

        decision = self._coordinator.decide(
            context,
            candidates,
            decision_id=decision_id,
            input_context_ref=input_context_ref,
        )

        if decision.selected_action.value != "EXECUTE":
            return PIAEActionCycleResult(
                decision=decision,
            )

        if intent is None:
            raise ValueError(
                "CapabilityIntent is required for EXECUTE decisions"
            )

        if plan is None:
            raise ValueError(
                "ExecutionPlan is required for EXECUTE decisions"
            )

        if sandbox is None:
            raise ValueError(
                "SandboxConfig is required for EXECUTE decisions"
            )

        request = self._coordinator.create_capability_request(
            decision,
            intent,
            now=current_time,
        )

        admission = self._coordinator.admit(
            request,
            now=current_time,
        )

        if not admission.admitted:
            execution_result = self._coordinator.execute(
                admission,
                plan,
                sandbox,
                now=current_time,
            )

            return PIAEActionCycleResult(
                decision=decision,
                capability_request=request,
                admission=admission,
                execution_result=execution_result,
            )

        execution_result = await runner.run(
            opportunity_id=context.opportunity.opportunity_id,
            admission=admission,
            plan=plan,
            sandbox=sandbox,
            worker_id=worker_id,
            lease_id=lease_id,
            now=current_time,
        )

        return PIAEActionCycleResult(
            decision=decision,
            capability_request=request,
            admission=admission,
            execution_result=execution_result,
        )
