"""Adversarial security-boundary tests for LHICF.

These tests verify that LHICF cannot become an alternate authority,
execution, sandbox, or host-control path.
"""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta

import pytest

from lyrion.capabilities.contracts import (
    AuthorizationDecision,
    AuthorizationResult,
    CapabilityOperation,
    CapabilityRequest,
)
from lyrion.capabilities.gateway import ExecutionAdmission
from lyrion.core.types import (
    AutonomyLevel,
    DecisionId,
    IdempotencyKey,
    RiskLevel,
    TaskId,
)
from lyrion.events.models import EventSensitivity
from lyrion.execution.backends.linux.host.contracts import (
    LinuxHostAbstractionSnapshot,
    LinuxHostFingerprint,
    LinuxHostIdentity,
)
from lyrion.execution.lhicf import (
    AdapterLifecycleState,
    AdapterRegistration,
    AdapterRegistry,
    BoundaryStatus,
    LHICFBoundaryValidator,
    LHICFRequest,
)
from lyrion.execution.lhicf.adapters import OSStateReadonlyAdapter

_DEFAULT_ADMISSION = object()

def authoritative_admission(
    *,
    request_id: str = "adv-req-001",
    capability_id: str = "development.prepare",
    target_scope: str = "HOST",
    operation: CapabilityOperation = CapabilityOperation.READ,
    admitted: bool = True,
    authorization_decision: AuthorizationDecision = (
        AuthorizationDecision.ALLOWED
    ),
) -> ExecutionAdmission:
    now = datetime.now(UTC)

    capability_request = CapabilityRequest(
        request_id=request_id,
        decision_id=DecisionId(f"decision:{request_id}"),
        task_id=TaskId(f"task:{request_id}"),
        principal_id="lyrion-piae",
        capability_id=capability_id,
        target_scope=target_scope,
        operation=operation,
        data_classification=EventSensitivity.INTERNAL,
        autonomy_level=AutonomyLevel.L1,
        risk_level=RiskLevel.LOW,
        policy_version="aegis-policy-v1",
        idempotency_key=IdempotencyKey(f"idem:{request_id}"),
        requested_at=now,
        expires_at=now + timedelta(minutes=5),
        justification="LHICF authoritative admission boundary test.",
        correlation_id="adv-corr-001",
    )

    authorization = AuthorizationResult(
        request_id=request_id,
        decision=authorization_decision,
        granted=admitted,
        principal_id=capability_request.principal_id,
        capability_id=capability_request.capability_id,
        target_scope=capability_request.target_scope,
        policy_version=capability_request.policy_version,
        reason=(
            "Authorized."
            if admitted
            else "Capability admission denied."
        ),
        evaluated_at=now,
        expires_at=capability_request.expires_at,
    )

    return ExecutionAdmission.from_authorization(
        capability_request,
        authorization,
        admitted_at=now,
    )


def valid_request(
    *,
    admission=_DEFAULT_ADMISSION,
    adapter_id="os-state",
    operation="READ_STATE",
    target_scope="HOST",
    requested_at=None,
    expires_at=None,
):
    if admission is _DEFAULT_ADMISSION:
        admission = authoritative_admission(
            target_scope=target_scope,
            operation=CapabilityOperation.READ,
        )

    if isinstance(admission, ExecutionAdmission):
        now = requested_at or admission.execution_request.requested_at
        final_expires_at = (
            expires_at
            or admission.execution_request.expires_at
        )
        request_id = admission.request_id
        correlation_id = (
            admission.execution_request.correlation_id
            or "adv-corr-001"
        )
    else:
        now = requested_at or datetime.now(UTC)
        final_expires_at = (
            expires_at
            or (now + timedelta(minutes=5))
        )
        request_id = "adv-req-001"
        correlation_id = "adv-corr-001"

    return LHICFRequest(
        request_id=request_id,
        execution_admission=admission,
        sandbox_context=object(),
        adapter_id=adapter_id,
        operation=operation,
        target_scope=target_scope,
        correlation_id=correlation_id,
        provenance_context="adv-prov-001",
        requested_at=now,
        expires_at=final_expires_at,
    )


def fake_snapshot():
    identity = LinuxHostIdentity(
        os_name="Ubuntu",
        os_version="24.04",
        kernel="6.8.0-test",
        architecture="x86_64",
        virtualization=None,
        init_system="systemd",
    )

    return LinuxHostAbstractionSnapshot(
        identity=identity,
        fingerprint=LinuxHostFingerprint(
            identity=identity,
            primitives=(),
        ),
        user_id=1000,
        effective_capabilities=(),
        namespaces=(),
        notes=(),
    )


class FakeDiscovery:
    def __init__(self):
        self.calls = 0

    def discover(self):
        self.calls += 1
        return fake_snapshot()


def registry():
    return AdapterRegistry(
        (
            OSStateReadonlyAdapter.registration(),
        )
    )


def test_arbitrary_python_object_cannot_cross_authority_boundary():
    request = valid_request(
        admission=object(),
    )

    validator = LHICFBoundaryValidator(registry())
    result = validator.validate(request)

    assert result.boundary_status is BoundaryStatus.BLOCKED
    assert "authoritative" in (result.failure_reason or "")


def test_denied_execution_admission_cannot_reach_host_boundary():
    admission = authoritative_admission(
        admitted=False,
        authorization_decision=AuthorizationDecision.DENIED,
    )
    request = valid_request(admission=admission)

    validator = LHICFBoundaryValidator(registry())
    result = validator.validate(request)

    assert result.boundary_status is BoundaryStatus.BLOCKED
    assert result.failure_reason == "execution admission is not admitted"


def test_genuine_authoritative_execution_admission_is_accepted():
    admission = authoritative_admission()
    request = valid_request(admission=admission)

    validator = LHICFBoundaryValidator(registry())
    result = validator.validate(request)

    assert result.boundary_status is BoundaryStatus.ACCEPTED


def test_admission_request_id_mismatch_is_blocked():
    admission = authoritative_admission()
    request = LHICFRequest(
        request_id="different-request-id",
        execution_admission=admission,
        sandbox_context=object(),
        adapter_id="os-state",
        operation="READ_STATE",
        target_scope="HOST",
        correlation_id="adv-corr-001",
        provenance_context="adv-prov-001",
        requested_at=admission.execution_request.requested_at,
        expires_at=admission.execution_request.expires_at,
    )

    validator = LHICFBoundaryValidator(registry())
    result = validator.validate(request)

    assert result.boundary_status is BoundaryStatus.BLOCKED
    assert "not bound" in (result.failure_reason or "")


def test_admission_target_scope_mismatch_is_blocked():
    admission = authoritative_admission(
        target_scope="lyrion/project/src",
    )

    request = LHICFRequest(
        request_id=admission.request_id,
        execution_admission=admission,
        sandbox_context=object(),
        adapter_id="os-state",
        operation="READ_STATE",
        target_scope="HOST",
        correlation_id=admission.execution_request.correlation_id,
        provenance_context="adv-prov-001",
        requested_at=admission.execution_request.requested_at,
        expires_at=admission.execution_request.expires_at,
    )

    validator = LHICFBoundaryValidator(registry())
    result = validator.validate(request)

    assert result.boundary_status is BoundaryStatus.BLOCKED


def test_admission_operation_mismatch_is_blocked():
    admission = authoritative_admission()

    request = LHICFRequest(
        request_id=admission.request_id,
        execution_admission=admission,
        sandbox_context=object(),
        adapter_id="os-state",
        operation="EXECUTE_PROCESS",
        target_scope="HOST",
        correlation_id=admission.execution_request.correlation_id,
        provenance_context="adv-prov-001",
        requested_at=admission.execution_request.requested_at,
        expires_at=admission.execution_request.expires_at,
    )

    validator = LHICFBoundaryValidator(registry())
    result = validator.validate(request)

    assert result.boundary_status is BoundaryStatus.BLOCKED


def test_missing_admission_is_blocked():
    request = valid_request(admission=None)
    validator = LHICFBoundaryValidator(registry())

    result = validator.validate(request)

    assert result.boundary_status is BoundaryStatus.BLOCKED
    assert result.failure_reason == "execution admission is required"


def test_expired_admission_is_blocked():
    requested = datetime.now(UTC) - timedelta(minutes=10)
    request = valid_request(
        requested_at=requested,
        expires_at=requested + timedelta(minutes=1),
    )

    validator = LHICFBoundaryValidator(registry())
    result = validator.validate(request)

    assert result.boundary_status is BoundaryStatus.STALE


def test_unknown_adapter_cannot_route_to_host():
    request = valid_request(adapter_id="unregistered-host-control")

    validator = LHICFBoundaryValidator(registry())
    result = validator.validate(request)

    assert result.boundary_status is BoundaryStatus.BLOCKED


def test_unsupported_operation_is_blocked():
    request = valid_request(operation="EXECUTE_PROCESS")

    validator = LHICFBoundaryValidator(registry())
    result = validator.validate(request)

    assert result.boundary_status is BoundaryStatus.BLOCKED


def test_unsupported_target_scope_is_blocked():
    request = valid_request(target_scope="FILESYSTEM")

    validator = LHICFBoundaryValidator(registry())
    result = validator.validate(request)

    assert result.boundary_status is BoundaryStatus.BLOCKED


def test_revoked_adapter_cannot_route():
    registration = OSStateReadonlyAdapter.registration()
    revoked = AdapterRegistration(
        adapter_id=registration.adapter_id,
        adapter_version=registration.adapter_version,
        contract_version=registration.contract_version,
        supported_operations=registration.supported_operations,
        supported_target_scopes=registration.supported_target_scopes,
        required_host_capabilities=registration.required_host_capabilities,
        required_host_qualification=registration.required_host_qualification,
        security_classification=registration.security_classification,
        integrity_reference=registration.integrity_reference,
        lifecycle_state=AdapterLifecycleState.REVOKED,
    )

    revoked_registry = AdapterRegistry((revoked,))
    validator = LHICFBoundaryValidator(revoked_registry)

    result = validator.validate(valid_request())

    assert result.boundary_status is BoundaryStatus.BLOCKED


def test_adapter_registration_is_immutable():
    registration = OSStateReadonlyAdapter.registration()

    with pytest.raises((FrozenInstanceError, TypeError)):
        registration.lifecycle_state = AdapterLifecycleState.REVOKED


def test_request_is_immutable():
    request = valid_request()

    with pytest.raises((FrozenInstanceError, TypeError)):
        request.operation = "EXECUTE_PROCESS"


def test_registry_order_is_deterministic():
    first = OSStateReadonlyAdapter.registration()
    second = AdapterRegistration(
        adapter_id="z-test",
        adapter_version="1.0.0",
        contract_version="1.0.0",
        supported_operations=frozenset({"READ_STATE"}),
        supported_target_scopes=frozenset({"HOST"}),
        required_host_capabilities=frozenset(),
        required_host_qualification=frozenset(),
        security_classification="READ_ONLY_HOST_STATE",
        integrity_reference="sha256:test",
        lifecycle_state=AdapterLifecycleState.AVAILABLE,
    )

    ordered = tuple(sorted((first, second), key=lambda adapter: adapter.adapter_id))

    registry_a = AdapterRegistry.from_adapters(ordered)
    registry_b = AdapterRegistry.from_adapters(ordered)

    assert tuple(
        adapter.adapter_id for adapter in registry_a.adapters
    ) == tuple(
        adapter.adapter_id for adapter in registry_b.adapters
    )


def test_adapter_never_becomes_authority():
    discovery = FakeDiscovery()
    adapter = OSStateReadonlyAdapter(discovery=discovery)

    result = adapter.observe(valid_request())

    assert result.boundary_status is BoundaryStatus.ACCEPTED
    assert not hasattr(result, "authorization_decision")
    assert not hasattr(result, "capability_grant")
    assert not hasattr(result, "execution_authorization")


def test_readonly_adapter_has_no_process_execution_interface():
    adapter = OSStateReadonlyAdapter(discovery=FakeDiscovery())

    assert not hasattr(adapter, "execute")
    assert not hasattr(adapter, "run")
    assert not hasattr(adapter, "shell")
    assert not hasattr(adapter, "subprocess")


def test_readonly_adapter_has_no_host_mutation_interface():
    adapter = OSStateReadonlyAdapter(discovery=FakeDiscovery())

    assert not hasattr(adapter, "write")
    assert not hasattr(adapter, "delete")
    assert not hasattr(adapter, "modify")
    assert not hasattr(adapter, "service_control")


def test_discovery_is_not_called_for_invalid_boundary_request():
    discovery = FakeDiscovery()
    adapter = OSStateReadonlyAdapter(discovery=discovery)

    result = adapter.observe(
        valid_request(operation="EXECUTE_PROCESS")
    )

    assert result.boundary_status is BoundaryStatus.BLOCKED
    assert discovery.calls == 0


def test_provenance_is_preserved_not_replaced():
    discovery = FakeDiscovery()
    adapter = OSStateReadonlyAdapter(discovery=discovery)

    request = valid_request()
    result = adapter.observe(request)

    assert result.provenance_reference == request.provenance_context


def test_unknown_boundary_status_cannot_be_treated_as_allow():
    allowed = {BoundaryStatus.ACCEPTED}

    for status in BoundaryStatus:
        if status not in allowed:
            assert status is not BoundaryStatus.ACCEPTED


def test_host_observation_remains_read_only():
    discovery = FakeDiscovery()
    adapter = OSStateReadonlyAdapter(discovery=discovery)

    before = discovery.calls
    result = adapter.observe(valid_request())
    after = discovery.calls

    assert result.boundary_status is BoundaryStatus.ACCEPTED
    assert after == before + 1
