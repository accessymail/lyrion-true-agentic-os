from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import ValidationError

from lyrion.agent_runtime.contracts import (
    AgentIdentity,
    AgentLifecycle,
    AgentLifecycleState,
    AgentRegistration,
    AgentTaskBinding,
    RuntimeExecutionContext,
)


def make_identity(
    *,
    agent_type: str = "test-agent",
    instance_name: str = "test-instance",
    version: str = "0.1.0",
) -> AgentIdentity:
    return AgentIdentity(
        agent_type=agent_type,
        instance_name=instance_name,
        version=version,
    )


class TestAgentIdentity:
    def test_identity_generates_uuid(self) -> None:
        identity = make_identity()

        assert isinstance(identity.agent_id, UUID)
        assert identity.agent_type == "test-agent"
        assert identity.instance_name == "test-instance"
        assert identity.version == "0.1.0"

    def test_identity_is_immutable(self) -> None:
        identity = make_identity()

        with pytest.raises(ValidationError):
            identity.instance_name = "changed"  # type: ignore[misc]

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("agent_type", ""),
            ("instance_name", ""),
            ("version", ""),
        ],
    )
    def test_identity_rejects_blank_required_fields(
        self,
        field: str,
        value: str,
    ) -> None:
        values = {
            "agent_type": "test-agent",
            "instance_name": "test-instance",
            "version": "0.1.0",
        }
        values[field] = value

        with pytest.raises(ValidationError):
            AgentIdentity(**values)


class TestAgentRegistration:
    def test_registration_preserves_identity(self) -> None:
        identity = make_identity()

        registration = AgentRegistration(
            identity=identity,
            declared_capabilities=("read", "analyze"),
        )

        assert registration.identity == identity
        assert registration.identity.agent_id == identity.agent_id
        assert registration.declared_capabilities == ("read", "analyze")

    def test_registration_is_immutable(self) -> None:
        registration = AgentRegistration(
            identity=make_identity(),
            declared_capabilities=("read",),
        )

        with pytest.raises(ValidationError):
            registration.trust_state = "trusted"  # type: ignore[misc]

    def test_capability_declarations_are_descriptive_not_authority(self) -> None:
        registration = AgentRegistration(
            identity=make_identity(),
            declared_capabilities=("filesystem.read",),
        )

        assert registration.declared_capabilities == ("filesystem.read",)
        assert not hasattr(registration, "authorize")
        assert not hasattr(registration, "admission_id")


class TestAgentLifecycle:
    def test_valid_lifecycle_progression(self) -> None:
        lifecycle = AgentLifecycle(state=AgentLifecycleState.REGISTERED)

        lifecycle = lifecycle.transition(AgentLifecycleState.READY)
        lifecycle = lifecycle.transition(AgentLifecycleState.ASSIGNED)
        lifecycle = lifecycle.transition(AgentLifecycleState.ADMITTED)
        lifecycle = lifecycle.transition(AgentLifecycleState.RUNNING)

        assert lifecycle.state is AgentLifecycleState.RUNNING

    def test_invalid_lifecycle_transition_is_rejected(self) -> None:
        lifecycle = AgentLifecycle(state=AgentLifecycleState.REGISTERED)

        with pytest.raises(ValueError):
            lifecycle.transition(AgentLifecycleState.RUNNING)

    @pytest.mark.parametrize(
        "terminal_state",
        [
            AgentLifecycleState.CANCELLED,
            AgentLifecycleState.COMPLETED,
            AgentLifecycleState.FAILED,
            AgentLifecycleState.QUARANTINED,
        ],
    )
    def test_terminal_states_have_no_outgoing_transitions(
        self,
        terminal_state: AgentLifecycleState,
    ) -> None:
        lifecycle = AgentLifecycle(state=terminal_state)

        with pytest.raises(ValueError):
            lifecycle.transition(AgentLifecycleState.READY)

    def test_lifecycle_is_immutable(self) -> None:
        lifecycle = AgentLifecycle(state=AgentLifecycleState.REGISTERED)

        with pytest.raises(ValidationError):
            lifecycle.state = AgentLifecycleState.READY  # type: ignore[misc]


class TestAgentTaskBinding:
    def test_binding_preserves_task_and_agent_identity(self) -> None:
        identity = make_identity()

        binding = AgentTaskBinding(
            task_id=identity.agent_id,
            agent_id=identity.agent_id,
        )

        assert binding.task_id == identity.agent_id
        assert binding.agent_id == identity.agent_id
        assert binding.parent_task_id is None

    def test_binding_is_immutable(self) -> None:
        identity = make_identity()

        binding = AgentTaskBinding(
            task_id=identity.agent_id,
            agent_id=identity.agent_id,
        )

        with pytest.raises(ValidationError):
            binding.agent_id = UUID(int=0)  # type: ignore[misc]

    def test_binding_does_not_create_authority(self) -> None:
        identity = make_identity()

        binding = AgentTaskBinding(
            task_id=identity.agent_id,
            agent_id=identity.agent_id,
        )

        assert not hasattr(binding, "authorize")
        assert not hasattr(binding, "capabilities")
        assert not hasattr(binding, "admission_id")


class TestRuntimeExecutionContext:
    def test_context_contains_correlation_identity(self) -> None:
        identity = make_identity()

        context = RuntimeExecutionContext(
            task_id=identity.agent_id,
            agent_id=identity.agent_id,
        )

        assert context.task_id == identity.agent_id
        assert context.agent_id == identity.agent_id
        assert context.parent_context_id is None
        assert context.admission_id is None
        assert context.delegated_authority_id is None
        assert context.has_admission_reference is False

    def test_context_can_reference_admission_without_granting_it(self) -> None:
        identity = make_identity()
        admission_id = UUID(int=1)
        delegated_authority_id = UUID(int=2)

        context = RuntimeExecutionContext(
            task_id=identity.agent_id,
            agent_id=identity.agent_id,
            admission_id=admission_id,
            delegated_authority_id=delegated_authority_id,
        )

        assert context.admission_id == admission_id
        assert context.delegated_authority_id == delegated_authority_id
        assert context.has_admission_reference is True

    def test_context_is_immutable(self) -> None:
        identity = make_identity()

        context = RuntimeExecutionContext(
            task_id=identity.agent_id,
            agent_id=identity.agent_id,
        )

        with pytest.raises(ValidationError):
            context.agent_id = UUID(int=0)  # type: ignore[misc]


class TestModule1SecurityBoundaries:
    def test_registration_does_not_equal_authorization(self) -> None:
        registration = AgentRegistration(
            identity=make_identity(),
            declared_capabilities=("filesystem.read",),
        )

        assert registration.trust_state.value == "unknown"
        assert not hasattr(registration, "authorize")

    def test_binding_does_not_equal_execution_admission(self) -> None:
        identity = make_identity()

        binding = AgentTaskBinding(
            task_id=identity.agent_id,
            agent_id=identity.agent_id,
        )

        context = RuntimeExecutionContext(
            task_id=binding.task_id,
            agent_id=binding.agent_id,
        )

        assert context.has_admission_reference is False
        assert not hasattr(binding, "admission_id")

    def test_runtime_context_only_references_security_decisions(self) -> None:
        identity = make_identity()

        context = RuntimeExecutionContext(
            task_id=identity.agent_id,
            agent_id=identity.agent_id,
            admission_id=UUID(int=1),
            delegated_authority_id=UUID(int=2),
        )

        assert context.has_admission_reference is True
        assert context.admission_id == UUID(int=1)
        assert context.delegated_authority_id == UUID(int=2)
