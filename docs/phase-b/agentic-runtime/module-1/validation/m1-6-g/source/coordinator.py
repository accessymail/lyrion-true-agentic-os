"""Module 1.6-G — Agent Runtime coordination coordinator.

This component is strictly a coordination-plane service. It does not
authorize actions, grant capabilities, create Execution Admission, restore
authority, execute host operations, or replace the Agent Harness.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from uuid import UUID

from lyrion.agent_runtime.contracts.lifecycle import AgentLifecycleState
from lyrion.agent_runtime.lifecycle.coordinator import AgentRuntimeLifecycleCoordinator
from lyrion.agent_runtime.supervision.coordinator import RuntimeSupervisionCoordinator

from .contracts import (
    CoordinationDecision,
    CoordinationError,
    CoordinationEvent,
    CoordinationMessage,
    CoordinationResourceState,
    ResourceAllocation,
    ResourceRequest,
    RouteDecision,
    RouteRequest,
    ScheduleRequest,
    ScheduleResult,
)


class AgentRuntimeCoordinationCoordinator:
    """Coordinate scheduling, routing, resources, messaging and provenance.

    Security invariants:
      * scheduling != authorization
      * routing != authorization
      * resource allocation != capability grant
      * communication != authorization
      * runtime state != authorization
      * recovery != authority restoration
      * retry != authorization
    """

    _SCHEDULABLE_STATES = frozenset(
        {
            AgentLifecycleState.READY,
            AgentLifecycleState.ASSIGNED,
            AgentLifecycleState.ADMITTED,
        }
    )

    def __init__(
        self,
        lifecycle: AgentRuntimeLifecycleCoordinator,
        supervision: RuntimeSupervisionCoordinator,
        *,
        resource_capacities: Mapping[str, int],
        peer_eligibility_checker: Callable[[UUID], bool],
    ) -> None:
        if supervision.lifecycle is not lifecycle:
            raise CoordinationError(
                "lifecycle and supervision coordinators must reference the same runtime"
            )
        self._lifecycle = lifecycle
        self._supervision = supervision
        self._events: tuple[CoordinationEvent, ...] = ()
        self._schedules: dict[UUID, ScheduleResult] = {}
        self._routes: dict[UUID, RouteDecision] = {}
        self._allocations: dict[UUID, ResourceAllocation] = {}
        self._messages: tuple[CoordinationMessage, ...] = ()
        self._message_ids: set[UUID] = set()
        self._idempotency: dict[UUID, object] = {}
        if not resource_capacities:
            raise CoordinationError("resource capacities must be configured")
        if any(not name.strip() or units <= 0 for name, units in resource_capacities.items()):
            raise CoordinationError("resource capacities must contain positive values")
        if peer_eligibility_checker is None:
            raise CoordinationError("peer eligibility checker is required")
        self._resource_capacities = dict(resource_capacities)
        self._peer_eligibility_checker = peer_eligibility_checker
        self._resource_usage: dict[str, int] = {}
        self._validate_integrity()

    @property
    def lifecycle(self) -> AgentRuntimeLifecycleCoordinator:
        return self._lifecycle

    @property
    def supervision(self) -> RuntimeSupervisionCoordinator:
        return self._supervision

    @property
    def events(self) -> tuple[CoordinationEvent, ...]:
        return self._events

    @property
    def schedules(self) -> tuple[ScheduleResult, ...]:
        return tuple(self._schedules.values())

    @property
    def routes(self) -> tuple[RouteDecision, ...]:
        return tuple(self._routes.values())

    @property
    def allocations(self) -> tuple[ResourceAllocation, ...]:
        return tuple(self._allocations.values())

    @property
    def messages(self) -> tuple[CoordinationMessage, ...]:
        return self._messages

    def _validate_integrity(self) -> None:
        self._lifecycle.verify_execution_context_correlation()

    def _event(self, event_type: str, reason: str) -> CoordinationEvent:
        self._validate_integrity()
        context = self._lifecycle.context
        event = CoordinationEvent(
            sequence=len(self._events) + 1,
            event_type=event_type,
            task_id=self._lifecycle.binding.task_id,
            agent_id=self._lifecycle.binding.agent_id,
            correlation_id=context.correlation_id,
            reason=reason,
        )
        self._events = (*self._events, event)
        return event

    def _ensure_not_terminal(self) -> None:
        if self._lifecycle.is_terminal:
            raise CoordinationError("terminal runtime cannot accept coordination")

    def schedule(self, request: ScheduleRequest) -> ScheduleResult:
        """Evaluate scheduling constraints only; never authorize execution."""
        self._ensure_not_terminal()
        self._validate_integrity()

        if request.task_id != self._lifecycle.binding.task_id:
            raise CoordinationError("schedule task does not match runtime task")
        if request.agent_id != self._lifecycle.binding.agent_id:
            raise CoordinationError("schedule agent does not match runtime agent")

        existing = self._schedules.get(request.request_id)
        if existing is not None:
            return existing

        now = datetime.now(UTC)
        if request.deadline is not None and request.deadline <= now:
            result = ScheduleResult(
                request_id=request.request_id,
                task_id=request.task_id,
                agent_id=request.agent_id,
                decision=CoordinationDecision.REJECTED,
                reason="scheduling deadline has expired",
            )
        elif not request.dependencies_satisfied:
            result = ScheduleResult(
                request_id=request.request_id,
                task_id=request.task_id,
                agent_id=request.agent_id,
                decision=CoordinationDecision.DEFERRED,
                reason="dependencies are not satisfied",
            )
        elif self._lifecycle.state not in self._SCHEDULABLE_STATES:
            result = ScheduleResult(
                request_id=request.request_id,
                task_id=request.task_id,
                agent_id=request.agent_id,
                decision=CoordinationDecision.DEFERRED,
                reason="runtime lifecycle is not schedulable",
            )
        else:
            result = ScheduleResult(
                request_id=request.request_id,
                task_id=request.task_id,
                agent_id=request.agent_id,
                decision=CoordinationDecision.ACCEPTED,
                reason="coordination schedule accepted; security admission remains external",
                scheduled_at=now,
            )

        self._schedules[request.request_id] = result
        self._event("schedule_evaluated", result.reason)
        return result

    def route(self, request: RouteRequest) -> RouteDecision:
        """Select a coordination route without dispatching or executing."""
        self._ensure_not_terminal()
        self._validate_integrity()

        if request.task_id != self._lifecycle.binding.task_id:
            raise CoordinationError("route task does not match runtime task")
        if request.source_agent_id != self._lifecycle.binding.agent_id:
            raise CoordinationError("route source agent does not match runtime agent")

        existing = self._routes.get(request.request_id)
        if existing is not None:
            return existing

        if not self._peer_eligibility_checker(request.target_id):
            decision = RouteDecision(
                request_id=request.request_id,
                task_id=request.task_id,
                target_id=request.target_id,
                decision=CoordinationDecision.DEFERRED,
                reason="target eligibility is unresolved by the external registry",
            )
        else:
            decision = RouteDecision(
                request_id=request.request_id,
                task_id=request.task_id,
                target_id=request.target_id,
                decision=CoordinationDecision.ACCEPTED,
                reason="coordination route selected; execution remains external",
            )
        self._routes[request.request_id] = decision
        self._event("route_selected", decision.reason)
        return decision

    def reserve_resource(self, request: ResourceRequest) -> ResourceAllocation:
        """Reserve coordination capacity only; no capability is granted."""
        self._ensure_not_terminal()
        self._validate_integrity()

        if request.task_id != self._lifecycle.binding.task_id:
            raise CoordinationError("resource task does not match runtime task")
        if request.agent_id != self._lifecycle.binding.agent_id:
            raise CoordinationError("resource agent does not match runtime agent")

        existing = self._idempotency.get(request.request_id)
        if isinstance(existing, ResourceAllocation):
            return existing

        capacity = self._resource_capacities.get(request.resource)
        if capacity is None:
            raise CoordinationError("resource capacity is not configured")

        current_usage = self._resource_usage.get(request.resource, 0)
        if current_usage + request.units > capacity:
            raise CoordinationError("resource capacity exceeded")

        allocation = ResourceAllocation(
            request_id=request.request_id,
            task_id=request.task_id,
            agent_id=request.agent_id,
            resource=request.resource,
            units=request.units,
            state=CoordinationResourceState.RESERVED,
        )
        self._allocations[allocation.allocation_id] = allocation
        self._resource_usage[request.resource] = (
            self._resource_usage.get(request.resource, 0) + request.units
        )
        self._idempotency[request.request_id] = allocation
        self._event("resource_reserved", "coordination capacity reserved")
        return allocation

    def release_resource(self, allocation_id: UUID) -> ResourceAllocation:
        """Release coordination capacity without changing security authority."""
        allocation = self._allocations.get(allocation_id)
        if allocation is None:
            raise CoordinationError("unknown resource allocation")
        if allocation.state is CoordinationResourceState.RELEASED:
            return allocation

        self._allocations[allocation_id] = allocation.model_copy(
            update={"state": CoordinationResourceState.RELEASED}
        )
        self._resource_usage[allocation.resource] = max(
            0, self._resource_usage.get(allocation.resource, 0) - allocation.units
        )
        self._event("resource_released", "coordination capacity released")
        return self._allocations[allocation_id]

    def send_message(self, message: CoordinationMessage) -> CoordinationMessage:
        """Record a correlation-preserving message; does not deliver/execute."""
        self._ensure_not_terminal()
        self._validate_integrity()

        if message.task_id != self._lifecycle.binding.task_id:
            raise CoordinationError("message task does not match runtime task")
        if message.sender_agent_id != self._lifecycle.binding.agent_id:
            raise CoordinationError("message sender does not match runtime agent")
        if not self._peer_eligibility_checker(message.recipient_agent_id):
            raise CoordinationError("message recipient eligibility is unresolved")
        if message.message_id in self._message_ids:
            raise CoordinationError("duplicate message_id rejected")

        if message.sequence != len(
            [m for m in self._messages if m.correlation_id == message.correlation_id]
        ) + 1:
            raise CoordinationError("message sequence is not contiguous for correlation")

        self._messages = (*self._messages, message)
        self._message_ids.add(message.message_id)
        self._event("message_recorded", "inter-agent coordination message recorded")
        return message

    def cancel_coordination(self, *, reason: str) -> CoordinationEvent:
        """Coordinate cancellation through existing supervision/lifecycle."""
        if not reason.strip():
            raise CoordinationError("cancellation reason is required")
        self._supervision.request_cancellation()
        return self._event("coordination_cancelled", reason.strip())

    def check_deadline(self, deadline: datetime) -> bool:
        """Observe a deadline without authorizing or executing anything."""
        self._ensure_not_terminal()
        self._validate_integrity()
        if deadline.tzinfo is None:
            raise CoordinationError("deadline must be timezone-aware")
        expired = deadline <= datetime.now(UTC)
        self._event(
            "deadline_checked",
            "coordination deadline expired" if expired else "coordination deadline active",
        )
        return expired

    def retry_coordination_allowed(self) -> bool:
        """Return runtime retry eligibility; security validation remains external."""
        self._validate_integrity()
        return self._supervision.retry_allowed()
