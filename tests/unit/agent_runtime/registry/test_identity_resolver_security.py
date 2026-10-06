"""Negative and security-boundary tests for Module 1.6-B.

These tests verify that Agent Runtime identity resolution remains a
coordination-plane boundary and cannot become an authorization, execution,
sandbox, LHICF, or host-control path.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from lyrion.agent_harness.contracts import AgentIdentity as HarnessAgentIdentity
from lyrion.agent_runtime.contracts.agent import (
    AgentIdentity,
    AgentRegistration,
    AgentTrustState,
)
from lyrion.agent_runtime.registry import AgentRegistry
from lyrion.agent_runtime.registry.adapter import AgentIdentityAdapter
from lyrion.agent_runtime.registry.identity_resolver import (
    AgentHarnessIdentityResolver,
    AgentIdentityResolutionError,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
RESOLVER_SOURCE = (
    PROJECT_ROOT
    / "src"
    / "lyrion"
    / "agent_runtime"
    / "registry"
    / "identity_resolver.py"
)


def make_registration(
    *,
    agent_id: UUID | None = None,
    trust_state: AgentTrustState = AgentTrustState.UNKNOWN,
    capabilities: tuple[str, ...] = ("research.read",),
) -> AgentRegistration:
    """Create deterministic Runtime registration metadata for tests."""
    return AgentRegistration(
        identity=AgentIdentity(
            agent_id=agent_id or uuid4(),
            agent_type="research-agent",
            instance_name="research-001",
            version="1.0.0",
        ),
        trust_state=trust_state,
        declared_capabilities=capabilities,
    )


def test_resolver_source_has_no_security_authority_imports() -> None:
    """The resolver must not import security or execution authorities."""
    tree = ast.parse(RESOLVER_SOURCE.read_text(encoding="utf-8"))

    forbidden_modules = {
        "lyrion.capabilities",
        "lyrion.execution",
        "lyrion.security",
        "lyrion.host",
        "lyrion.lhicf",
    }

    imported_modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert not any(
        module == forbidden or module.startswith(f"{forbidden}.")
        for module in imported_modules
        for forbidden in forbidden_modules
    )


def test_resolver_source_does_not_construct_security_or_execution_objects() -> None:
    """The resolver must never manufacture authority or execution objects."""
    tree = ast.parse(RESOLVER_SOURCE.read_text(encoding="utf-8"))

    forbidden_names = {
        "AuthorizationResult",
        "CapabilityRequest",
        "DelegatedAuthority",
        "ExecutionAdmission",
        "SecureExecutor",
        "AgentSandbox",
        "LHICF",
    }

    constructed: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            constructed.add(node.func.id)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            constructed.add(node.func.attr)

    assert constructed.isdisjoint(forbidden_names)


def test_resolver_source_has_no_host_execution_calls() -> None:
    """The resolver must not expose or invoke host/execution primitives."""
    tree = ast.parse(RESOLVER_SOURCE.read_text(encoding="utf-8"))

    forbidden_calls = {
        "execute",
        "exec",
        "subprocess",
        "Popen",
        "run",
        "system",
        "popen",
    }

    calls: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)

    assert calls.isdisjoint(forbidden_calls)


def test_resolver_public_api_contains_no_authority_or_execution_inputs() -> None:
    """Resolution accepts identity/provenance only, never authority objects."""
    signature = inspect.signature(AgentHarnessIdentityResolver.resolve)

    parameter_names = set(signature.parameters)

    forbidden_parameters = {
        "authorization",
        "authorization_result",
        "capability",
        "capability_request",
        "delegated_authority",
        "execution_admission",
        "secure_executor",
        "sandbox",
        "lhicf",
        "host",
    }

    assert parameter_names.isdisjoint(forbidden_parameters)


def test_unregistered_identity_never_reaches_adapter() -> None:
    """Unregistered identities must fail before translation occurs."""

    class RecordingAdapter(AgentIdentityAdapter):
        def __init__(self) -> None:
            self.called = False

        def to_harness_identity(
            self,
            identity: AgentIdentity,
            *,
            identity_provenance_ref: str,
        ) -> HarnessAgentIdentity:
            self.called = True
            return super().to_harness_identity(
                identity,
                identity_provenance_ref=identity_provenance_ref,
            )

    adapter = RecordingAdapter()
    resolver = AgentHarnessIdentityResolver(
        registry=AgentRegistry(),
        adapter=adapter,
    )

    with pytest.raises(AgentIdentityResolutionError):
        resolver.resolve(
            uuid4(),
            identity_provenance_ref="registry://unknown/1",
        )

    assert adapter.called is False


def test_runtime_capabilities_are_never_passed_to_harness_identity_adapter() -> None:
    """Declared Runtime capabilities cannot cross the identity boundary."""

    class RecordingAdapter(AgentIdentityAdapter):
        def __init__(self) -> None:
            self.received_identity: AgentIdentity | None = None
            self.received_provenance: str | None = None

        def to_harness_identity(
            self,
            identity: AgentIdentity,
            *,
            identity_provenance_ref: str,
        ) -> HarnessAgentIdentity:
            self.received_identity = identity
            self.received_provenance = identity_provenance_ref
            return super().to_harness_identity(
                identity,
                identity_provenance_ref=identity_provenance_ref,
            )

    registration = make_registration(
        capabilities=(
            "research.read",
            "filesystem.write",
            "process.execute",
        )
    )
    registry = AgentRegistry()
    registry.register(registration)

    adapter = RecordingAdapter()
    resolver = AgentHarnessIdentityResolver(
        registry=registry,
        adapter=adapter,
    )

    resolver.resolve(
        registration.identity.agent_id,
        identity_provenance_ref="registry://research-agent/1",
    )

    assert adapter.received_identity == registration.identity
    assert adapter.received_provenance == "registry://research-agent/1"

    # The adapter receives the identity object, not a promoted capability
    # collection or security decision.
    assert not hasattr(adapter.received_identity, "authorization")
    assert not hasattr(adapter.received_identity, "capability_grant")
    assert not hasattr(adapter.received_identity, "execution_admission")


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
def test_trust_state_does_not_change_identity_resolution_authority(
    trust_state: AgentTrustState,
) -> None:
    """Trust metadata must never become execution authority."""
    registration = make_registration(trust_state=trust_state)

    registry = AgentRegistry()
    registry.register(registration)

    result = AgentHarnessIdentityResolver(
        registry=registry,
    ).resolve(
        registration.identity.agent_id,
        identity_provenance_ref="registry://research-agent/1",
    )

    assert isinstance(result, HarnessAgentIdentity)
    assert set(type(result).model_fields) == {
        "agent_id",
        "identity_provenance_ref",
    }


def test_adapter_translation_failure_fails_closed() -> None:
    """Adapter translation errors must not produce a partial identity."""

    class FailingAdapter(AgentIdentityAdapter):
        def to_harness_identity(
            self,
            identity: AgentIdentity,
            *,
            identity_provenance_ref: str,
        ) -> HarnessAgentIdentity:
            raise ValueError("translation rejected")

    registration = make_registration()

    registry = AgentRegistry()
    registry.register(registration)

    resolver = AgentHarnessIdentityResolver(
        registry=registry,
        adapter=FailingAdapter(),
    )

    with pytest.raises(AgentIdentityResolutionError):
        resolver.resolve(
            registration.identity.agent_id,
            identity_provenance_ref="registry://research-agent/1",
        )


def test_registry_identity_mismatch_fails_closed() -> None:
    """A corrupt/mismatched registry response must never be translated."""

    class MismatchedRegistry:
        def __init__(self, registration: AgentRegistration) -> None:
            self.registration = registration

        def get(self, agent_id: UUID) -> AgentRegistration:
            return self.registration

    registered = make_registration()
    requested_agent_id = uuid4()

    resolver = AgentHarnessIdentityResolver(
        registry=MismatchedRegistry(registered),  # type: ignore[arg-type]
    )

    with pytest.raises(AgentIdentityResolutionError):
        resolver.resolve(
            requested_agent_id,
            identity_provenance_ref="registry://mismatch/1",
        )


def test_resolver_cannot_create_execution_surface_via_dynamic_attributes() -> None:
    """The resolver object exposes only its coordination-boundary interface."""
    resolver = AgentHarnessIdentityResolver(registry=AgentRegistry())

    forbidden_names = {
        "authorize",
        "grant_capability",
        "create_admission",
        "execute",
        "secure_executor",
        "sandbox",
        "lhicf",
        "host",
        "delegate",
    }

    public_names = {
        name
        for name in dir(resolver)
        if not name.startswith("_")
    }

    assert public_names.isdisjoint(forbidden_names)
    assert "resolve" in public_names


def test_identity_adapter_is_translation_only() -> None:
    """The identity adapter has no security or execution authority surface."""
    adapter = AgentIdentityAdapter()

    public_names = {
        name
        for name in dir(adapter)
        if not name.startswith("_")
    }

    forbidden_names = {
        "authorize",
        "grant_capability",
        "create_admission",
        "execute",
        "secure_executor",
        "sandbox",
        "lhicf",
        "host",
    }

    assert public_names.isdisjoint(forbidden_names)
    assert public_names == {"to_harness_identity"}
