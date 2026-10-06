"""Module 1.6-D — Agent Runtime → Agent Harness integration tests.

These tests validate the controlled integration boundary between the
Agent Runtime coordination plane and the existing Agent Harness.

Security invariants:
    Runtime registration != authorization
    Runtime identity != authority
    Runtime trust state != authorization
    Runtime declared capabilities != granted capabilities
    AgentTaskBinding != AgentBinding
    AgentTaskBinding != ExecutionAdmission
    Runtime context != authorization context
    Identity resolution does not create authority
    Harness remains the owner of authorized execution context
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from lyrion.agent_harness import AgentHarness
from lyrion.agent_harness.contracts import AgentIdentity as HarnessAgentIdentity
from lyrion.agent_runtime.contracts.agent import (
    AgentIdentity,
    AgentRegistration,
    AgentTrustState,
)
from lyrion.agent_runtime.contracts.task_binding import AgentTaskBinding
from lyrion.agent_runtime.registry.adapter import AgentIdentityAdapter
from lyrion.agent_runtime.registry.identity_resolver import (
    AgentHarnessIdentityResolver,
    AgentIdentityResolutionError,
)
from lyrion.agent_runtime.registry.registry import AgentRegistry
from lyrion.capabilities.contracts import (
    AuthorizationDecision,
    CapabilityOperation,
    CapabilityRequest,
)
from lyrion.capabilities.gateway import CapabilityGateway, ExecutionAdmission
from lyrion.core.types import (
    AutonomyLevel,
    DecisionId,
    IdempotencyKey,
    RiskLevel,
    TaskId,
)
from lyrion.events.models import EventSensitivity
from lyrion.execution.executor import SecureExecutor
from lyrion.security.authorization import AegisAuthorizationService
from lyrion.security.guards import AuthorizationGuard
from lyrion.security.policy import AegisPolicyEvaluator
from lyrion.security.replay import ReplayGuard
from lyrion.security.rules import default_aegis_policy
from lyrion.tasks.models import TaskStatus

AGENT_ID = UUID("11111111-1111-4111-8111-111111111111")
TASK_ID = UUID("22222222-2222-4222-8222-222222222222")
PARENT_TASK_ID = UUID("33333333-3333-4333-8333-333333333333")

PROVENANCE_REF = "runtime-test:module-1.6-d"
DECLARED_CAPABILITY = "descriptive:filesystem.read"


def make_runtime_identity() -> AgentIdentity:
    """Create a deterministic Runtime identity."""
    return AgentIdentity(
        agent_id=AGENT_ID,
        agent_type="integration-test-agent",
        instance_name="module-1.6-d",
        version="1.0.0",
    )


def make_registration(
    *,
    trust_state: AgentTrustState = AgentTrustState.TRUSTED,
    declared_capabilities: tuple[str, ...] = (DECLARED_CAPABILITY,),
) -> AgentRegistration:
    """Create a Runtime registration record."""
    return AgentRegistration(
        identity=make_runtime_identity(),
        registered_at=__import__("datetime").datetime.now(
            __import__("datetime").UTC
        ),
        trust_state=trust_state,
        declared_capabilities=declared_capabilities,
        registration_revision=1,
    )


def make_registry() -> AgentRegistry:
    """Create a fresh isolated Runtime registry."""
    registry = AgentRegistry()
    registry.register(make_registration())
    return registry


def make_resolver(
    registry: AgentRegistry,
) -> AgentHarnessIdentityResolver:
    """Create the production Runtime identity-resolution boundary."""
    return AgentHarnessIdentityResolver(
        registry=registry,
        adapter=AgentIdentityAdapter(),
    )


def test_registered_runtime_identity_resolves_to_harness_identity() -> None:
    """Registered Runtime identity maps deterministically into Harness identity."""
    registry = make_registry()
    resolver = make_resolver(registry)

    resolved = resolver.resolve(
        AGENT_ID,
        identity_provenance_ref=PROVENANCE_REF,
    )

    assert isinstance(resolved, HarnessAgentIdentity)
    assert resolved.agent_id == str(AGENT_ID)
    assert resolved.identity_provenance_ref == PROVENANCE_REF


def test_resolution_preserves_runtime_identity_without_promoting_metadata() -> None:
    """Runtime metadata must not become Harness authority."""
    registry = make_registry()
    resolver = make_resolver(registry)

    resolved = resolver.resolve(
        AGENT_ID,
        identity_provenance_ref=PROVENANCE_REF,
    )

    assert resolved.agent_id == str(AGENT_ID)

    # Harness identity intentionally contains only identity/provenance data.
    assert not hasattr(resolved, "declared_capabilities")
    assert not hasattr(resolved, "trust_state")
    assert not hasattr(resolved, "registration_revision")
    assert not hasattr(resolved, "authority_context")
    assert not hasattr(resolved, "capability_context")
    assert not hasattr(resolved, "execution_admission")


def test_runtime_declared_capability_is_not_promoted_during_resolution() -> None:
    """Declared Runtime capabilities cannot become Harness authority."""
    registry = make_registry()
    resolver = make_resolver(registry)

    registration = registry.get(AGENT_ID)

    assert DECLARED_CAPABILITY in registration.declared_capabilities

    resolved = resolver.resolve(
        AGENT_ID,
        identity_provenance_ref=PROVENANCE_REF,
    )

    assert not hasattr(resolved, "declared_capabilities")
    assert not hasattr(resolved, "capabilities")
    assert not hasattr(resolved, "capability_context")


@pytest.mark.parametrize(
    "trust_state",
    [
        AgentTrustState.UNKNOWN,
        AgentTrustState.UNTRUSTED,
        AgentTrustState.EVALUATING,
        AgentTrustState.TRUSTED,
        AgentTrustState.QUARANTINED,
    ],
)
def test_trust_state_does_not_change_identity_resolution_contract(
    trust_state: AgentTrustState,
) -> None:
    """Runtime trust metadata does not become authorization."""
    registry = AgentRegistry()
    registry.register(make_registration(trust_state=trust_state))

    resolver = make_resolver(registry)

    resolved = resolver.resolve(
        AGENT_ID,
        identity_provenance_ref=PROVENANCE_REF,
    )

    assert resolved.agent_id == str(AGENT_ID)
    assert resolved.identity_provenance_ref == PROVENANCE_REF


def test_unregistered_runtime_identity_fails_closed() -> None:
    """An unregistered Runtime identity cannot cross the boundary."""
    registry = AgentRegistry()
    resolver = make_resolver(registry)

    with pytest.raises(AgentIdentityResolutionError):
        resolver.resolve(
            AGENT_ID,
            identity_provenance_ref=PROVENANCE_REF,
        )


def test_blank_provenance_fails_closed() -> None:
    """Harness identity cannot be created without explicit provenance."""
    registry = make_registry()
    resolver = make_resolver(registry)

    with pytest.raises(AgentIdentityResolutionError):
        resolver.resolve(
            AGENT_ID,
            identity_provenance_ref="   ",
        )


def test_runtime_identity_is_deterministic() -> None:
    """Repeated resolution produces equivalent Harness identity."""
    registry = make_registry()
    resolver = make_resolver(registry)

    first = resolver.resolve(
        AGENT_ID,
        identity_provenance_ref=PROVENANCE_REF,
    )
    second = resolver.resolve(
        AGENT_ID,
        identity_provenance_ref=PROVENANCE_REF,
    )

    assert first == second


def test_agent_task_binding_remains_distinct_from_harness_identity() -> None:
    """Runtime task binding is coordination data, not Harness authority."""
    binding = AgentTaskBinding(
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        parent_task_id=PARENT_TASK_ID,
    )

    assert binding.agent_id == AGENT_ID
    assert binding.task_id == TASK_ID
    assert binding.parent_task_id == PARENT_TASK_ID

    # The Runtime binding carries coordination identity only.
    assert not hasattr(binding, "authority_context")
    assert not hasattr(binding, "capability_context")
    assert not hasattr(binding, "execution_admission")


def test_agent_task_binding_does_not_change_resolved_harness_identity() -> None:
    """Runtime task binding cannot alter Harness identity resolution."""
    registry = make_registry()
    resolver = make_resolver(registry)

    binding = AgentTaskBinding(
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        parent_task_id=PARENT_TASK_ID,
    )

    resolved = resolver.resolve(
        binding.agent_id,
        identity_provenance_ref=PROVENANCE_REF,
    )

    assert resolved.agent_id == str(binding.agent_id)
    assert resolved.identity_provenance_ref == PROVENANCE_REF


def test_runtime_registry_cannot_resolve_another_agent() -> None:
    """Resolution is bound to the requested registered agent ID."""
    registry = make_registry()
    resolver = make_resolver(registry)

    other_agent_id = uuid4()

    with pytest.raises(AgentIdentityResolutionError):
        resolver.resolve(
            other_agent_id,
            identity_provenance_ref=PROVENANCE_REF,
        )


def test_identity_resolution_does_not_expose_execution_surface() -> None:
    """Resolver output must not expose an execution or admission API."""
    registry = make_registry()
    resolver = make_resolver(registry)

    resolved = resolver.resolve(
        AGENT_ID,
        identity_provenance_ref=PROVENANCE_REF,
    )

    forbidden = {
        "authorize",
        "grant_capability",
        "create_admission",
        "execution_admission",
        "execute",
        "secure_execute",
        "run",
        "spawn",
        "host_access",
    }

    exposed = {
        name
        for name in forbidden
        if hasattr(resolved, name)
    }

    assert exposed == set()


def test_runtime_resolution_does_not_construct_harness_binding() -> None:
    """Identity resolution must stop before AgentBinding creation."""
    registry = make_registry()
    resolver = make_resolver(registry)

    resolved = resolver.resolve(
        AGENT_ID,
        identity_provenance_ref=PROVENANCE_REF,
    )

    # Harness identity is intentionally not an AgentBinding.
    assert isinstance(resolved, HarnessAgentIdentity)
    assert not hasattr(resolved, "task_id")
    assert not hasattr(resolved, "authority_context")
    assert not hasattr(resolved, "execution_admission")


def test_registry_membership_is_not_authorization() -> None:
    """Registration alone must never be interpreted as permission."""
    registry = make_registry()

    registration = registry.get(AGENT_ID)

    assert registration.identity.agent_id == AGENT_ID
    assert registration.trust_state is AgentTrustState.TRUSTED

    # These attributes are deliberately absent from Runtime registration.
    assert not hasattr(registration, "authorization")
    assert not hasattr(registration, "authorization_result")
    assert not hasattr(registration, "execution_admission")
    assert not hasattr(registration, "delegated_authority")


def test_resolution_requires_explicit_provenance_per_call() -> None:
    """Provenance must be supplied at the integration boundary."""
    registry = make_registry()
    resolver = make_resolver(registry)

    with pytest.raises(AgentIdentityResolutionError):
        resolver.resolve(AGENT_ID, identity_provenance_ref="")

    with pytest.raises(AgentIdentityResolutionError):
        resolver.resolve(AGENT_ID, identity_provenance_ref="   ")

    valid = resolver.resolve(
        AGENT_ID,
        identity_provenance_ref=PROVENANCE_REF,
    )

    assert valid.identity_provenance_ref == PROVENANCE_REF

def test_runtime_identity_crosses_into_existing_harness_binding_boundary() -> None:
    """Validate Runtime identity integration with the existing Agent Harness.

    Security invariant:
        Runtime resolves identity only; the Harness receives an already
        authorized execution context and remains responsible for binding
        validation. Runtime registration, trust state, and declared
        capabilities do not create authority or execution admission.
    """
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)
    task_id = TaskId("task:module-1.6-d:harness-binding")

    request = CapabilityRequest(
        request_id="request:module-1.6-d:harness-binding",
        decision_id=DecisionId("decision:module-1.6-d:harness-binding"),
        task_id=task_id,
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope="lyrion/project/src",
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        autonomy_level=AutonomyLevel.L1,
        risk_level=RiskLevel.LOW,
        policy_version="aegis-policy-v1",
        idempotency_key=IdempotencyKey("idem:module-1.6-d:harness-binding"),
        requested_at=now,
        expires_at=now + timedelta(minutes=5),
        justification="Controlled Module 1.6-D Runtime/Harness integration.",
    )

    policy = default_aegis_policy()
    gateway = CapabilityGateway(
        AegisAuthorizationService(
            AegisPolicyEvaluator(policy),
            AuthorizationGuard(policy.policy_version),
            ReplayGuard(),
        )
    )

    # Authorization is intentionally established outside Agent Runtime.
    authority = gateway.authorization_service.authorize(
        request,
        now=now,
    )

    assert authority.decision is AuthorizationDecision.ALLOWED
    assert authority.granted is True

    # Execution Admission is intentionally established outside Agent Runtime.
    admission = ExecutionAdmission.from_authorization(
        request,
        authority,
        admitted_at=now,
    )

    assert admission.admitted is True

    task = __import__("lyrion.tasks.models", fromlist=["Task"]).Task(
        task_id=task_id,
        objective="Controlled Module 1.6-D Runtime/Harness integration.",
        status=TaskStatus.RUNNING,
        autonomy_level=AutonomyLevel.L2,
        risk_level=RiskLevel.LOW,
        created_at=now,
        updated_at=now,
    )

    registry = make_registry()
    resolver = make_resolver(registry)

    # Runtime contributes identity/provenance only.
    runtime_resolved_identity = resolver.resolve(
        AGENT_ID,
        identity_provenance_ref=PROVENANCE_REF,
    )

    assert runtime_resolved_identity.agent_id == str(AGENT_ID)
    assert (
        runtime_resolved_identity.identity_provenance_ref
        == PROVENANCE_REF
    )

    # The existing Harness receives the already-authorized context.
    harness = AgentHarness(secure_executor=SecureExecutor())

    binding = harness.bind(
        identity=runtime_resolved_identity,
        task=task,
        authority_context=authority,
        capability_context=request,
        execution_admission=admission,
        provenance_context="test:module-1.6-d:harness-binding",
    )

    assert binding.lifecycle_state.value == "VALIDATED"
    assert binding.identity == runtime_resolved_identity
    assert binding.task_id == task.task_id
    assert binding.authority_context is authority
    assert binding.capability_context is request
    assert binding.execution_admission is admission

    provenance = harness.provenance(
        binding,
        task=task,
        now=now,
    )

    assert provenance.agent_id == runtime_resolved_identity.agent_id
    assert provenance.identity_provenance_ref == PROVENANCE_REF
    assert provenance.task_id == task.task_id
    assert provenance.request_id == request.request_id
    assert provenance.execution_id == admission.execution_request.execution_id

    # Runtime metadata remains descriptive and never becomes Harness authority.
    registration = registry.get(AGENT_ID)

    assert registration.trust_state is AgentTrustState.TRUSTED
    assert DECLARED_CAPABILITY in registration.declared_capabilities
    assert not hasattr(runtime_resolved_identity, "declared_capabilities")
    assert not hasattr(runtime_resolved_identity, "authority_context")
    assert not hasattr(runtime_resolved_identity, "capability_context")
    assert not hasattr(runtime_resolved_identity, "execution_admission")


def test_runtime_cannot_construct_harness_binding_without_external_authorization() -> None:
    """Verify Runtime identity resolution alone cannot create AgentBinding."""
    registry = make_registry()
    resolver = make_resolver(registry)

    resolved_identity = resolver.resolve(
        AGENT_ID,
        identity_provenance_ref=PROVENANCE_REF,
    )

    # Identity resolution produces only Harness identity.
    assert isinstance(resolved_identity, HarnessAgentIdentity)

    # The resulting object cannot supply any Harness execution context.
    assert not hasattr(resolved_identity, "task_id")
    assert not hasattr(resolved_identity, "authority_context")
    assert not hasattr(resolved_identity, "capability_context")
    assert not hasattr(resolved_identity, "execution_admission")
