from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from lyrion.agent_runtime.contracts.lifecycle import AgentLifecycle, AgentLifecycleState
from lyrion.agent_runtime.contracts.runtime_context import RuntimeExecutionContext
from lyrion.agent_runtime.contracts.task_binding import AgentTaskBinding
from lyrion.agent_runtime.coordination import (
    AgentRuntimeCoordinationCoordinator,
    CoordinationDecision,
    CoordinationError,
    CoordinationMessage,
    ResourceRequest,
    RouteRequest,
    ScheduleRequest,
)
from lyrion.agent_runtime.lifecycle.coordinator import AgentRuntimeLifecycleCoordinator
from lyrion.agent_runtime.supervision.coordinator import RuntimeSupervisionCoordinator


def _security_context():
    from lyrion.agent_runtime.coordination import CoordinationSecurityContext

    return CoordinationSecurityContext(
        principal_id=uuid4(),
        delegated_authority_ref=uuid4(),
        capability_ref=uuid4(),
        policy_context_ref=uuid4(),
    )


def _runtime() -> AgentRuntimeCoordinationCoordinator:
    task_id = uuid4()
    agent_id = uuid4()
    binding = AgentTaskBinding(task_id=task_id, agent_id=agent_id)
    context = RuntimeExecutionContext(task_id=task_id, agent_id=agent_id)
    lifecycle = AgentRuntimeLifecycleCoordinator(
        binding=binding,
        lifecycle=AgentLifecycle(state=AgentLifecycleState.REGISTERED),
        context=context,
    )
    lifecycle.transition(AgentLifecycleState.READY, reason="test ready")
    supervision = RuntimeSupervisionCoordinator(lifecycle)
    return AgentRuntimeCoordinationCoordinator(
        lifecycle,
        supervision,
        resource_capacities={"cpu": 4, "memory": 16},
        peer_eligibility_checker=lambda _peer_id: True,
    )


def test_schedule_accepts_satisfied_dependencies_without_authorizing() -> None:
    runtime = _runtime()
    request = ScheduleRequest(
        task_id=runtime.lifecycle.binding.task_id,
        agent_id=runtime.lifecycle.binding.agent_id,
    )
    result = runtime.schedule(request)
    assert result.decision is CoordinationDecision.ACCEPTED
    assert runtime.lifecycle.context.admission_id is None


def test_schedule_defers_unsatisfied_dependencies() -> None:
    runtime = _runtime()
    dependency = uuid4()
    result = runtime.schedule(
        ScheduleRequest(
            task_id=runtime.lifecycle.binding.task_id,
            agent_id=runtime.lifecycle.binding.agent_id,
            dependencies=(dependency,),
        )
    )
    assert result.decision is CoordinationDecision.DEFERRED


def test_schedule_rejects_expired_deadline() -> None:
    runtime = _runtime()
    result = runtime.schedule(
        ScheduleRequest(
            task_id=runtime.lifecycle.binding.task_id,
            agent_id=runtime.lifecycle.binding.agent_id,
            deadline=datetime.now(UTC) - timedelta(seconds=1),
        )
    )
    assert result.decision is CoordinationDecision.REJECTED


def test_schedule_is_idempotent() -> None:
    runtime = _runtime()
    request = ScheduleRequest(
        task_id=runtime.lifecycle.binding.task_id,
        agent_id=runtime.lifecycle.binding.agent_id,
    )
    assert runtime.schedule(request) == runtime.schedule(request)


def test_schedule_rejects_mismatched_task() -> None:
    runtime = _runtime()
    with pytest.raises(CoordinationError):
        runtime.schedule(
            ScheduleRequest(task_id=uuid4(), agent_id=runtime.lifecycle.binding.agent_id)
        )


def test_route_records_without_execution() -> None:
    runtime = _runtime()
    request = RouteRequest(
        task_id=runtime.lifecycle.binding.task_id,
        source_agent_id=runtime.lifecycle.binding.agent_id,
        target_id=uuid4(),
        correlation_id=runtime.lifecycle.context.correlation_id,
    security_context=_security_context(),
    )
    result = runtime.route(request)
    assert result.decision is CoordinationDecision.ACCEPTED


def test_route_is_idempotent() -> None:
    runtime = _runtime()
    request = RouteRequest(
        task_id=runtime.lifecycle.binding.task_id,
        source_agent_id=runtime.lifecycle.binding.agent_id,
        target_id=uuid4(),
        correlation_id=runtime.lifecycle.context.correlation_id,
    security_context=_security_context(),
    )
    assert runtime.route(request) == runtime.route(request)


def test_resource_capacity_is_enforced() -> None:
    runtime = _runtime()
    runtime.reserve_resource(
        ResourceRequest(
            task_id=runtime.lifecycle.binding.task_id,
            agent_id=runtime.lifecycle.binding.agent_id,
            resource="cpu",
            units=4,
        )
    )
    with pytest.raises(CoordinationError):
        runtime.reserve_resource(
            ResourceRequest(
                task_id=runtime.lifecycle.binding.task_id,
                agent_id=runtime.lifecycle.binding.agent_id,
                resource="cpu",
                units=1,
            )
        )


def test_unknown_resource_capacity_is_rejected() -> None:
    runtime = _runtime()
    with pytest.raises(CoordinationError):
        runtime.reserve_resource(
            ResourceRequest(
                task_id=runtime.lifecycle.binding.task_id,
                agent_id=runtime.lifecycle.binding.agent_id,
                resource="gpu",
                units=1,
            )
        )


def test_route_defers_unknown_peer() -> None:
    task_id = uuid4()
    agent_id = uuid4()
    binding = AgentTaskBinding(task_id=task_id, agent_id=agent_id)
    context = RuntimeExecutionContext(task_id=task_id, agent_id=agent_id)
    lifecycle = AgentRuntimeLifecycleCoordinator(
        binding=binding,
        lifecycle=AgentLifecycle(state=AgentLifecycleState.REGISTERED),
        context=context,
    )
    lifecycle.transition(AgentLifecycleState.READY, reason="test ready")
    supervision = RuntimeSupervisionCoordinator(lifecycle)
    runtime = AgentRuntimeCoordinationCoordinator(
        lifecycle,
        supervision,
        resource_capacities={"cpu": 4},
        peer_eligibility_checker=lambda _peer_id: False,
    )

    result = runtime.route(
        RouteRequest(
            task_id=task_id,
            source_agent_id=agent_id,
            target_id=uuid4(),
            correlation_id=context.correlation_id,
            security_context=_security_context(),
        )
    )
    assert result.decision is CoordinationDecision.DEFERRED


def test_resource_reservation_is_not_capability() -> None:
    runtime = _runtime()
    allocation = runtime.reserve_resource(
        ResourceRequest(
            task_id=runtime.lifecycle.binding.task_id,
            agent_id=runtime.lifecycle.binding.agent_id,
            resource="cpu",
            units=2,
        )
    )
    assert allocation.units == 2
    assert runtime.lifecycle.context.admission_id is None


def test_resource_reservation_is_idempotent() -> None:
    runtime = _runtime()
    request = ResourceRequest(
        task_id=runtime.lifecycle.binding.task_id,
        agent_id=runtime.lifecycle.binding.agent_id,
        resource="memory",
        units=4,
    )
    assert runtime.reserve_resource(request) == runtime.reserve_resource(request)


def test_resource_release_is_terminal_for_allocation_state() -> None:
    runtime = _runtime()
    allocation = runtime.reserve_resource(
        ResourceRequest(
            task_id=runtime.lifecycle.binding.task_id,
            agent_id=runtime.lifecycle.binding.agent_id,
            resource="cpu",
            units=1,
        )
    )
    released = runtime.release_resource(allocation.allocation_id)
    assert released.state.value == "released"
    assert runtime.release_resource(allocation.allocation_id) == released


def test_message_preserves_correlation_and_rejects_duplicate() -> None:
    runtime = _runtime()
    correlation = uuid4()
    message = CoordinationMessage(
        task_id=runtime.lifecycle.binding.task_id,
        sender_agent_id=runtime.lifecycle.binding.agent_id,
        recipient_agent_id=uuid4(),
        correlation_id=correlation,
        sequence=1,
        payload_digest="sha256:example",
    security_context=_security_context(),
    )
    runtime.send_message(message)
    with pytest.raises(CoordinationError):
        runtime.send_message(message)


def test_message_requires_contiguous_sequence() -> None:
    runtime = _runtime()
    correlation = uuid4()
    with pytest.raises(CoordinationError):
        runtime.send_message(
            CoordinationMessage(
                task_id=runtime.lifecycle.binding.task_id,
                sender_agent_id=runtime.lifecycle.binding.agent_id,
                recipient_agent_id=uuid4(),
                correlation_id=correlation,
                sequence=2,
                payload_digest="sha256:example",
            security_context=_security_context(),
            )
        )


def test_deadline_requires_timezone() -> None:
    runtime = _runtime()
    with pytest.raises(CoordinationError):
        runtime.check_deadline(datetime.now())


def test_deadline_observation_does_not_authorize() -> None:
    runtime = _runtime()
    assert runtime.check_deadline(datetime.now(UTC) + timedelta(seconds=30)) is False
    assert runtime.lifecycle.context.admission_id is None


def test_cancellation_uses_existing_supervision_boundary() -> None:
    runtime = _runtime()
    runtime.lifecycle.transition(
        AgentLifecycleState.ASSIGNED,
        reason="test assigned",
    )
    runtime.lifecycle.transition(
        AgentLifecycleState.ADMITTED,
        reason="test admitted",
    )
    runtime.lifecycle.transition(
        AgentLifecycleState.RUNNING,
        reason="test running",
    )
    event = runtime.cancel_coordination(reason="test cancellation")
    assert event.event_type == "coordination_cancelled"
    assert runtime.lifecycle.state is AgentLifecycleState.CANCELLING
    assert runtime.lifecycle.context.admission_id is None


def test_terminal_runtime_rejects_coordination() -> None:
    runtime = _runtime()
    runtime.lifecycle.quarantine(reason="test quarantine")
    with pytest.raises(CoordinationError):
        runtime.check_deadline(datetime.now(UTC) + timedelta(seconds=1))


def test_retry_eligibility_remains_runtime_only() -> None:
    runtime = _runtime()
    assert runtime.retry_coordination_allowed() is False
