"""Module 1.6-F supervision coordinator security and behavior tests."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from lyrion.agent_runtime.contracts.lifecycle import (
    AgentLifecycle,
    AgentLifecycleState,
)
from lyrion.agent_runtime.contracts.runtime_context import RuntimeExecutionContext
from lyrion.agent_runtime.contracts.task_binding import AgentTaskBinding
from lyrion.agent_runtime.lifecycle.coordinator import (
    AgentRuntimeLifecycleCoordinator,
)
from lyrion.agent_runtime.supervision.coordinator import (
    FailureCategory,
    RuntimeSupervisionCoordinator,
    RuntimeSupervisionError,
)


def _coordinator() -> RuntimeSupervisionCoordinator:
    binding = AgentTaskBinding(
        binding_id=uuid4(),
        task_id=uuid4(),
        agent_id=uuid4(),
        binding_revision=1,
    )
    context = RuntimeExecutionContext(
        task_id=binding.task_id,
        agent_id=binding.agent_id,
    )
    lifecycle = AgentLifecycle(state=AgentLifecycleState.REGISTERED)

    lifecycle_coordinator = AgentRuntimeLifecycleCoordinator(
        binding=binding,
        lifecycle=lifecycle,
        context=context,
    )

    return RuntimeSupervisionCoordinator(lifecycle_coordinator)


def _reach_running(
    coordinator: RuntimeSupervisionCoordinator,
) -> None:
    lifecycle = coordinator.lifecycle
    lifecycle.transition(
        AgentLifecycleState.READY,
        reason="test setup",
    )
    lifecycle.transition(
        AgentLifecycleState.ASSIGNED,
        reason="test setup",
    )
    lifecycle.transition(
        AgentLifecycleState.ADMITTED,
        reason="test setup",
    )
    lifecycle.transition(
        AgentLifecycleState.RUNNING,
        reason="test setup",
    )


def test_health_observation_is_provenance_only() -> None:
    coordinator = _coordinator()

    event = coordinator.observe_health()

    assert event.event_type == "health_observed"
    assert coordinator.lifecycle.context.admission_id is None


def test_failure_is_classified_and_correlated() -> None:
    coordinator = _coordinator()

    failure = coordinator.report_failure(
        category=FailureCategory.RUNTIME,
        message="runtime dependency stopped",
        recoverable=True,
    )

    assert failure.category is FailureCategory.RUNTIME
    assert failure.task_id == coordinator.lifecycle.binding.task_id
    assert failure.agent_id == coordinator.lifecycle.binding.agent_id
    assert coordinator.failures == (failure,)


def test_invalid_integrity_fails_closed() -> None:
    coordinator = _coordinator()

    coordinator.lifecycle._context = RuntimeExecutionContext(
        task_id=uuid4(),
        agent_id=coordinator.lifecycle.binding.agent_id,
    )

    with pytest.raises(RuntimeSupervisionError):
        coordinator.observe_health()


def test_cancellation_does_not_create_authority() -> None:
    coordinator = _coordinator()
    _reach_running(coordinator)

    coordinator.request_cancellation()
    assert coordinator.state is AgentLifecycleState.CANCELLING

    coordinator.complete_cancellation()

    assert coordinator.state is AgentLifecycleState.CANCELLED
    assert coordinator.lifecycle.context.admission_id is None
    assert coordinator.lifecycle.context.delegated_authority_id is None


def test_quarantine_is_terminal_and_clears_security_references() -> None:
    coordinator = _coordinator()
    _reach_running(coordinator)

    coordinator.lifecycle.attach_admission_reference(
        uuid4(),
        delegated_authority_id=uuid4(),
    )

    coordinator.quarantine(reason="security boundary inconsistency")

    assert coordinator.state is AgentLifecycleState.QUARANTINED
    assert coordinator.lifecycle.context.admission_id is None
    assert coordinator.lifecycle.context.delegated_authority_id is None

    with pytest.raises(RuntimeSupervisionError):
        coordinator.observe_health()


def test_recovery_cannot_restore_authority() -> None:
    coordinator = _coordinator()
    _reach_running(coordinator)

    coordinator.lifecycle.attach_admission_reference(
        uuid4(),
        delegated_authority_id=uuid4(),
    )

    coordinator.mark_failure_recoverable()
    assert coordinator.state is AgentLifecycleState.RECOVERABLE

    coordinator.begin_recovery()

    assert coordinator.state is AgentLifecycleState.RECOVERING
    assert coordinator.lifecycle.context.admission_id is None
    assert coordinator.lifecycle.context.delegated_authority_id is None

    coordinator.finish_recovery()

    assert coordinator.state is AgentLifecycleState.ASSIGNED
    assert coordinator.lifecycle.context.admission_id is None
    assert coordinator.lifecycle.context.delegated_authority_id is None


def test_recovery_cannot_jump_directly_to_running() -> None:
    coordinator = _coordinator()
    _reach_running(coordinator)

    coordinator.mark_failure_recoverable()
    coordinator.begin_recovery()
    coordinator.finish_recovery()

    assert coordinator.state is AgentLifecycleState.ASSIGNED


def test_terminal_runtime_cannot_resume() -> None:
    coordinator = _coordinator()

    coordinator.quarantine(reason="terminal containment")

    with pytest.raises(RuntimeSupervisionError):
        coordinator.begin_recovery()

    with pytest.raises(RuntimeSupervisionError):
        coordinator.mark_failure_recoverable()


def test_retry_requires_runtime_admission_reference_but_does_not_validate_it() -> None:
    coordinator = _coordinator()
    _reach_running(coordinator)

    with pytest.raises(RuntimeSupervisionError):
        coordinator.validate_retry_context()

    coordinator.lifecycle.attach_admission_reference(uuid4())

    coordinator.validate_retry_context()

    assert coordinator.retry_allowed() is True


def test_retry_is_not_authorization() -> None:
    coordinator = _coordinator()
    _reach_running(coordinator)

    coordinator.lifecycle.attach_admission_reference(uuid4())

    assert coordinator.retry_allowed() is True

    coordinator.lifecycle.clear_security_references()

    assert coordinator.retry_allowed() is True

    with pytest.raises(RuntimeSupervisionError):
        coordinator.validate_retry_context()


def test_provenance_is_immutable() -> None:
    coordinator = _coordinator()

    event = coordinator.observe_health()

    with pytest.raises(ValidationError):
        event.reason = "mutated"

    assert coordinator.events[0].event_id == event.event_id


def test_failure_provenance_preserves_correlation() -> None:
    coordinator = _coordinator()

    failure = coordinator.report_failure(
        category=FailureCategory.SECURITY_BOUNDARY,
        message="stale runtime security reference",
        recoverable=False,
    )

    assert failure.context_id == coordinator.lifecycle.context.context_id
    assert failure.correlation_id == coordinator.lifecycle.context.correlation_id


def test_security_boundary_failure_can_be_contained_without_authority() -> None:
    coordinator = _coordinator()

    failure = coordinator.report_failure(
        category=FailureCategory.SECURITY_BOUNDARY,
        message="security precondition inconsistency",
        recoverable=False,
    )

    event = coordinator.contain_failure(
        reason="contain security boundary failure",
    )

    assert event.failure_id == failure.failure_id
    assert coordinator.lifecycle.context.admission_id is None
