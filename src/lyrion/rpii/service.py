"""Bounded orchestration service for Lyrion Real Proactive Interactive Intelligence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from lyrion.core.types import DecisionId
from lyrion.execution.contracts import ExecutionPlan
from lyrion.execution.sandbox import SandboxConfig
from lyrion.integration.proactive_execution import CapabilityIntent
from lyrion.piae.action_loop import PIAEActionCycleResult, PIAEActionLoop
from lyrion.piae.contracts import DecisionCandidate
from lyrion.rpii.contracts import (
    RPIIContext,
    RPIICycleResult,
    RPIIStage,
    RPIIStatus,
)


class RPIIActionRunner(Protocol):
    """Minimal action-loop interface required by the RPII orchestrator."""

    def run_once(
        self,
        context: object,
        candidates: tuple[DecisionCandidate, ...],
        intent: CapabilityIntent | None,
        plan: ExecutionPlan | None,
        sandbox: SandboxConfig | None,
        *,
        decision_id: DecisionId | None = None,
        input_context_ref: str = "action-loop",
        now: datetime | None = None,
    ) -> PIAEActionCycleResult:
        """Run one bounded PIAE action cycle."""


class RPIIService:
    """Orchestrate one bounded RPII cycle without owning authorization or execution."""

    def __init__(
        self,
        action_loop: PIAEActionLoop | RPIIActionRunner,
    ) -> None:
        """Initialize the service with the existing PIAE action-loop boundary."""
        self._action_loop = action_loop

    @property
    def action_loop(self) -> PIAEActionLoop | RPIIActionRunner:
        """Return the configured action-loop boundary."""
        return self._action_loop

    def run_once(
        self,
        context: RPIIContext,
        candidates: tuple[DecisionCandidate, ...],
        intent: CapabilityIntent | None,
        plan: ExecutionPlan | None,
        sandbox: SandboxConfig | None,
        *,
        decision_id: DecisionId | None = None,
        now: datetime | None = None,
    ) -> RPIICycleResult:
        """Run exactly one bounded RPII orchestration cycle."""
        current_time = now or datetime.now(UTC)

        self._require_timezone_aware(current_time, "now")

        if current_time < context.created_at:
            raise ValueError("now cannot be earlier than context.created_at")

        started_at = context.created_at

        input_context_ref = self._build_input_context_ref(context)

        cycle = self._action_loop.run_once(
            context.decision_context,
            candidates,
            intent,
            plan,
            sandbox,
            decision_id=decision_id,
            input_context_ref=input_context_ref,
            now=current_time,
        )

        self._verify_cycle_bindings(
            context=context,
            cycle=cycle,
            plan=plan,
        )

        status, stage = self._derive_lifecycle(cycle)

        completed_at: datetime | None
        if status in {
            RPIIStatus.COMPLETED,
            RPIIStatus.DENIED,
            RPIIStatus.FAILED,
            RPIIStatus.DEGRADED,
        }:
            completed_at = current_time
        else:
            completed_at = None

        return RPIICycleResult(
            interaction_id=context.interaction_id,
            session_id=context.session_id,
            status=status,
            stage=stage,
            decision=cycle.decision,
            capability_request=cycle.capability_request,
            admission=cycle.admission,
            execution_plan=plan,
            sandbox=sandbox,
            execution_result=cycle.execution_result,
            started_at=started_at,
            completed_at=completed_at,
        )

    @staticmethod
    def _build_input_context_ref(context: RPIIContext) -> str:
        """Build a deterministic context reference owned by this RPII cycle."""
        return f"rpii:{context.session_id}:{context.interaction_id}"

    @staticmethod
    def _require_timezone_aware(value: datetime, name: str) -> None:
        """Require a timezone-aware timestamp."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{name} must be timezone-aware")

    @classmethod
    def _verify_cycle_bindings(
        cls,
        *,
        context: RPIIContext,
        cycle: PIAEActionCycleResult,
        plan: ExecutionPlan | None,
    ) -> None:
        """Verify identity continuity without granting authority."""
        decision = cycle.decision
        expected_opportunity = context.decision_context.opportunity.opportunity_id

        if decision.input_context_ref != cls._build_input_context_ref(context):
            raise ValueError("decision input context is not bound to this RPII cycle")

        if decision.opportunity_ref != expected_opportunity:
            raise ValueError("decision opportunity does not match RPII context")

        request = cycle.capability_request
        admission = cycle.admission
        execution_result = cycle.execution_result

        if request is None:
            if admission is not None or execution_result is not None:
                raise ValueError(
                    "execution artifacts cannot exist without a capability request"
                )
            return

        if request.decision_id != decision.decision_id:
            raise ValueError("capability request is bound to a different decision")

        if admission is None:
            if execution_result is not None:
                raise ValueError(
                    "execution result cannot exist without an execution admission"
                )
            return

        if admission.request_id != request.request_id:
            raise ValueError("execution admission is bound to a different request")

        admitted_request = admission.execution_request

        if admitted_request.request_id != admission.request_id:
            raise ValueError(
                "execution request is not bound to the execution admission"
            )

        if admitted_request.capability_id != request.capability_id:
            raise ValueError(
                "execution request capability does not match capability request"
            )

        if admitted_request.target_scope != request.target_scope:
            raise ValueError(
                "execution request target does not match capability request"
            )

        if admitted_request.task_id != request.task_id:
            raise ValueError(
                "execution request task does not match capability request"
            )

        if admitted_request.principal_id != request.principal_id:
            raise ValueError(
                "execution request principal does not match capability request"
            )

        if admitted_request.idempotency_key != request.idempotency_key:
            raise ValueError(
                "execution request idempotency key does not match capability request"
            )

        if plan is not None and plan.execution_id != admitted_request.execution_id:
            raise ValueError(
                "execution plan execution_id does not match admitted execution"
            )

        if execution_result is None:
            return

        if execution_result.execution_id != admitted_request.execution_id:
            raise ValueError(
                "execution result belongs to a different execution"
            )

        if execution_result.request_id != admission.request_id:
            raise ValueError(
                "execution result belongs to a different capability request"
            )

    @staticmethod
    def _derive_lifecycle(
        cycle: PIAEActionCycleResult,
    ) -> tuple[RPIIStatus, RPIIStage]:
        """Derive bounded RPII lifecycle state from the existing action result."""
        request = cycle.capability_request
        admission = cycle.admission
        execution_result = cycle.execution_result

        if request is None:
            return RPIIStatus.COMPLETED, RPIIStage.DECISION

        if admission is None:
            return RPIIStatus.FAILED, RPIIStage.AUTHORIZATION

        if not admission.admitted:
            return RPIIStatus.DENIED, RPIIStage.AUTHORIZATION

        if execution_result is None:
            return RPIIStatus.WAITING, RPIIStage.EXECUTION

        status = execution_result.status.value

        if status == "COMPLETED":
            return RPIIStatus.COMPLETED, RPIIStage.EVALUATION

        if status == "DENIED":
            return RPIIStatus.DENIED, RPIIStage.EXECUTION

        if status == "FAILED":
            return RPIIStatus.FAILED, RPIIStage.EVALUATION

        return RPIIStatus.DEGRADED, RPIIStage.EVALUATION
