"""Module 1.6-E lifecycle/task-binding integration tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from lyrion.agent_runtime.contracts.lifecycle import AgentLifecycleState
from lyrion.agent_runtime.contracts.runtime_context import RuntimeExecutionContext
from lyrion.agent_runtime.contracts.task_binding import AgentTaskBinding
from lyrion.agent_runtime.lifecycle.coordinator import (
    AgentRuntimeLifecycleCoordinator,
    RuntimeLifecycleError,
)


def make_binding() -> AgentTaskBinding:
    return AgentTaskBinding(
        task_id=uuid4(),
        agent_id=uuid4(),
        parent_task_id=uuid4(),
        binding_revision=1,
    )


def test_required_lifecycle_progression() -> None:
    binding = make_binding()
    coordinator = AgentRuntimeLifecycleCoordinator(binding=binding)

    assert coordinator.state is AgentLifecycleState.REGISTERED

    coordinator.transition(
        AgentLifecycleState.READY,
        reason="registration complete",
    )
    coordinator.transition(
        AgentLifecycleState.ASSIGNED,
        reason="agent assigned",
    )
    coordinator.attach_admission_reference(uuid4())
    coordinator.transition(
        AgentLifecycleState.ADMITTED,
        reason="admission reference correlated",
    )
    coordinator.transition(
        AgentLifecycleState.RUNNING,
        reason="execution lifecycle started",
    )

    assert coordinator.state is AgentLifecycleState.RUNNING


def test_invalid_transition_fails_closed() -> None:
    coordinator = AgentRuntimeLifecycleCoordinator(
        binding=make_binding()
    )

    with pytest.raises(RuntimeLifecycleError):
        coordinator.transition(
            AgentLifecycleState.RUNNING,
            reason="invalid direct transition",
        )

    assert coordinator.state is AgentLifecycleState.REGISTERED
    assert coordinator.provenance == ()


@pytest.mark.parametrize(
    "terminal_state",
    [
        AgentLifecycleState.COMPLETED,
        AgentLifecycleState.CANCELLED,
        AgentLifecycleState.FAILED,
        AgentLifecycleState.QUARANTINED,
    ],
)
def test_terminal_states_cannot_resume(
    terminal_state: AgentLifecycleState,
) -> None:
    coordinator = AgentRuntimeLifecycleCoordinator(
        binding=make_binding()
    )

    coordinator.transition(
        AgentLifecycleState.READY,
        reason="registration complete",
    )
    coordinator.transition(
        AgentLifecycleState.ASSIGNED,
        reason="agent assigned",
    )

    if terminal_state is AgentLifecycleState.CANCELLED:
        coordinator.request_cancellation()
        coordinator.complete_cancellation()
    elif terminal_state is AgentLifecycleState.QUARANTINED:
        coordinator.quarantine(reason="security quarantine")
    else:
        coordinator.transition(
            AgentLifecycleState.ADMITTED,
            reason="admission reference correlated",
        )
        coordinator.transition(
            AgentLifecycleState.RUNNING,
            reason="execution lifecycle started",
        )
        coordinator.transition(
            terminal_state,
            reason="terminal transition",
        )

    with pytest.raises(RuntimeLifecycleError):
        coordinator.transition(
            AgentLifecycleState.READY,
            reason="attempted terminal-state resume",
        )

    assert coordinator.state is terminal_state


def test_task_binding_and_runtime_context_must_correlate() -> None:
    binding = make_binding()
    context = RuntimeExecutionContext(
        task_id=uuid4(),
        agent_id=binding.agent_id,
    )

    with pytest.raises(RuntimeLifecycleError):
        AgentRuntimeLifecycleCoordinator(
            binding=binding,
            context=context,
        )


def test_admission_reference_is_not_authorization() -> None:
    coordinator = AgentRuntimeLifecycleCoordinator(
        binding=make_binding()
    )

    admission_id = uuid4()
    context = coordinator.attach_admission_reference(admission_id)

    assert context.admission_id == admission_id
    assert context.has_admission_reference is True
    assert coordinator.state is AgentLifecycleState.REGISTERED


def test_recovery_clears_security_references_and_requires_fresh_path() -> None:
    coordinator = AgentRuntimeLifecycleCoordinator(
        binding=make_binding()
    )

    coordinator.transition(
        AgentLifecycleState.READY,
        reason="registration complete",
    )
    coordinator.transition(
        AgentLifecycleState.ASSIGNED,
        reason="agent assigned",
    )
    coordinator.attach_admission_reference(
        uuid4(),
        delegated_authority_id=uuid4(),
    )
    coordinator.transition(
        AgentLifecycleState.ADMITTED,
        reason="admission reference correlated",
    )
    coordinator.transition(
        AgentLifecycleState.RUNNING,
        reason="execution lifecycle started",
    )
    coordinator.mark_recoverable()

    coordinator.begin_recovery()

    assert coordinator.state is AgentLifecycleState.RECOVERING
    assert coordinator.context.admission_id is None
    assert coordinator.context.delegated_authority_id is None

    coordinator.finish_recovery()

    assert coordinator.state is AgentLifecycleState.ASSIGNED
    assert coordinator.context.admission_id is None
    assert coordinator.context.delegated_authority_id is None


def test_cancellation_does_not_create_authority() -> None:
    coordinator = AgentRuntimeLifecycleCoordinator(
        binding=make_binding()
    )

    coordinator.transition(
        AgentLifecycleState.READY,
        reason="registration complete",
    )
    coordinator.transition(
        AgentLifecycleState.ASSIGNED,
        reason="agent assigned",
    )

    coordinator.request_cancellation()

    assert coordinator.state is AgentLifecycleState.CANCELLING
    assert coordinator.context.admission_id is None
    assert coordinator.context.delegated_authority_id is None

    coordinator.complete_cancellation()

    assert coordinator.state is AgentLifecycleState.CANCELLED


def test_provenance_is_immutable_and_preserves_correlation() -> None:
    binding = make_binding()
    coordinator = AgentRuntimeLifecycleCoordinator(binding=binding)

    coordinator.transition(
        AgentLifecycleState.READY,
        reason="registration complete",
    )
    coordinator.transition(
        AgentLifecycleState.ASSIGNED,
        reason="agent assigned",
    )

    records = coordinator.provenance

    assert len(records) == 2
    assert records[0].sequence == 1
    assert records[1].sequence == 2
    assert records[0].task_id == binding.task_id
    assert records[0].agent_id == binding.agent_id
    assert records[0].binding_id == binding.binding_id
    assert records[0].binding_revision == binding.binding_revision
    assert records[0].context_id == coordinator.context.context_id
    assert records[0].correlation_id == coordinator.context.correlation_id


def test_runtime_context_reference_does_not_validate_admission() -> None:
    coordinator = AgentRuntimeLifecycleCoordinator(
        binding=make_binding()
    )

    coordinator.attach_admission_reference(uuid4())

    # Correlation validation is deliberately separate from security
    # validation and cannot prove authorization.
    coordinator.verify_execution_context_correlation()

    assert coordinator.context.has_admission_reference is True


def test_quarantine_is_terminal() -> None:
    coordinator = AgentRuntimeLifecycleCoordinator(
        binding=make_binding()
    )

    coordinator.quarantine(reason="integrity condition violated")

    assert coordinator.state is AgentLifecycleState.QUARANTINED
    assert coordinator.is_terminal is True

    with pytest.raises(RuntimeLifecycleError):
        coordinator.transition(
            AgentLifecycleState.READY,
            reason="attempted quarantine escape",
        )
