"""Adversarial validation for the bounded LHICF Core.

These tests verify that hostile or malformed boundary inputs fail closed.
They intentionally do not exercise real host operations.
"""

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
from lyrion.execution.lhicf import (
    AdapterLifecycleState,
    AdapterRegistration,
    AdapterRegistry,
    BoundaryStatus,
    LHICFBoundaryValidator,
    LHICFRequest,
)

_DEFAULT_ADMISSION = object()


def registration(
    *,
    adapter_id: str = "os-state",
    operations: frozenset[str] = frozenset({"READ_STATE"}),
    scopes: frozenset[str] = frozenset({"HOST"}),
    lifecycle: AdapterLifecycleState = AdapterLifecycleState.AVAILABLE,
    integrity: str = "sha256:test",
) -> AdapterRegistration:
    return AdapterRegistration(
        adapter_id=adapter_id,
        adapter_version="1.0.0",
        contract_version="1.0.0",
        supported_operations=operations,
        supported_target_scopes=scopes,
        required_host_capabilities=frozenset(),
        required_host_qualification=frozenset(),
        security_classification="READ_ONLY_HOST_STATE",
        integrity_reference=integrity,
        lifecycle_state=lifecycle,
    )


def authoritative_admission():
    now = datetime.now(UTC)

    capability_request = CapabilityRequest(
        request_id="req-adversarial-1",
        decision_id=DecisionId("decision:req-adversarial-1"),
        task_id=TaskId("task:req-adversarial-1"),
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope="HOST",
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        autonomy_level=AutonomyLevel.L1,
        risk_level=RiskLevel.LOW,
        policy_version="aegis-policy-v1",
        idempotency_key=IdempotencyKey("idem:req-adversarial-1"),
        requested_at=now,
        expires_at=now + timedelta(minutes=5),
        justification="LHICF adversarial boundary unit test.",
        correlation_id="corr-1",
    )

    authorization = AuthorizationResult(
        request_id=capability_request.request_id,
        decision=AuthorizationDecision.ALLOWED,
        granted=True,
        principal_id=capability_request.principal_id,
        capability_id=capability_request.capability_id,
        target_scope=capability_request.target_scope,
        policy_version=capability_request.policy_version,
        reason="Authorized for controlled LHICF testing.",
        evaluated_at=now,
        expires_at=capability_request.expires_at,
    )

    return ExecutionAdmission.from_authorization(
        capability_request,
        authorization,
        admitted_at=now,
    )


def request(
    *,
    admission=_DEFAULT_ADMISSION,
    adapter_id: str = "os-state",
    operation: str = "READ_STATE",
    scope: str = "HOST",
    correlation_id: str = "corr-1",
    provenance_context: str = "prov-1",
    expires_delta: timedelta = timedelta(minutes=5),
) -> LHICFRequest:
    if admission is _DEFAULT_ADMISSION:
        admission = authoritative_admission()

    if isinstance(admission, ExecutionAdmission):
        requested_at = admission.execution_request.requested_at
        request_id = admission.request_id
        effective_correlation_id = correlation_id
    else:
        requested_at = datetime.now(UTC)
        request_id = "req-adversarial-1"
        effective_correlation_id = correlation_id

    return LHICFRequest(
        request_id=request_id,
        execution_admission=admission,
        sandbox_context=object(),
        adapter_id=adapter_id,
        operation=operation,
        target_scope=scope,
        correlation_id=effective_correlation_id,
        provenance_context=provenance_context,
        requested_at=requested_at,
        expires_at=requested_at + expires_delta,
    )


def validator(
    *adapters: AdapterRegistration,
) -> LHICFBoundaryValidator:
    if not adapters:
        adapters = (registration(),)

    ordered = tuple(sorted(adapters, key=lambda adapter: adapter.adapter_id))
    return LHICFBoundaryValidator(
        AdapterRegistry.from_adapters(ordered)
    )


def test_missing_execution_admission_fails_closed():
    result = validator().validate(request(admission=None))

    assert result.boundary_status is BoundaryStatus.BLOCKED
    assert result.normalized_result is None
    assert result.failure_reason


def test_expired_execution_context_is_stale():
    now = datetime.now(UTC)

    expired_request = LHICFRequest(
        request_id="req-expired",
        execution_admission=object(),
        sandbox_context=object(),
        adapter_id="os-state",
        operation="READ_STATE",
        target_scope="HOST",
        correlation_id="corr-expired",
        provenance_context="prov-expired",
        requested_at=now - timedelta(minutes=10),
        expires_at=now - timedelta(minutes=1),
    )

    result = validator().validate(expired_request)

    assert result.boundary_status is BoundaryStatus.STALE
    assert result.normalized_result is None


def test_unknown_adapter_fails_closed():
    result = validator().validate(
        request(adapter_id="unknown-host-control")
    )

    assert result.boundary_status is BoundaryStatus.BLOCKED


def test_revoked_adapter_cannot_enter_boundary():
    registry = AdapterRegistry.from_adapters(
        (
            registration(
                adapter_id="os-state",
                lifecycle=AdapterLifecycleState.REVOKED,
            ),
        )
    )

    result = LHICFBoundaryValidator(registry).validate(request())

    assert result.boundary_status is BoundaryStatus.BLOCKED


def test_unsupported_operation_fails_closed():
    result = validator().validate(
        request(operation="DELETE")
    )

    assert result.boundary_status is BoundaryStatus.BLOCKED


def test_unsupported_target_scope_fails_closed():
    result = validator().validate(
        request(scope="FILESYSTEM")
    )

    assert result.boundary_status is BoundaryStatus.BLOCKED


def test_operation_case_downgrade_cannot_bypass_request_contract():
    with pytest.raises(
        ValueError,
        match="normalized uppercase",
    ):
        request(operation="read_state")


def test_blank_correlation_id_is_rejected_at_contract_boundary():
    with pytest.raises(
        ValueError,
        match="correlation_id must not be blank",
    ):
        request(correlation_id=" ")


def test_blank_provenance_context_is_rejected_at_contract_boundary():
    with pytest.raises(
        ValueError,
        match="provenance_context must not be blank",
    ):
        request(provenance_context=" ")


def test_duplicate_adapter_identity_is_rejected():
    with pytest.raises(
        ValueError,
        match="duplicate adapter_id",
    ):
        AdapterRegistry.from_adapters(
            (
                registration(),
                registration(),
            )
        )


def test_non_deterministic_adapter_order_is_rejected():
    with pytest.raises(
        ValueError,
        match="deterministically sorted",
    ):
        AdapterRegistry.from_adapters(
            (
                registration(adapter_id="z-adapter"),
                registration(adapter_id="a-adapter"),
            )
        )


def test_declared_adapter_is_not_available_for_execution():
    registry = AdapterRegistry.from_adapters(
        (
            registration(
                lifecycle=AdapterLifecycleState.VALIDATED,
            ),
        )
    )

    result = LHICFBoundaryValidator(registry).validate(request())

    assert result.boundary_status is BoundaryStatus.BLOCKED


def test_registered_adapter_is_not_available_for_execution():
    registry = AdapterRegistry.from_adapters(
        (
            registration(
                lifecycle=AdapterLifecycleState.REGISTERED,
            ),
        )
    )

    result = LHICFBoundaryValidator(registry).validate(request())

    assert result.boundary_status is BoundaryStatus.BLOCKED


def test_empty_integrity_reference_is_rejected_by_registration_contract():
    with pytest.raises(
        ValueError,
        match="integrity_reference must not be blank",
    ):
        registration(integrity=" ")


def test_lhicf_request_is_immutable():
    value = request()

    with pytest.raises(AttributeError):
        value.operation = "DELETE"


def test_adapter_registration_is_immutable():
    value = registration()

    with pytest.raises(AttributeError):
        value.adapter_id = "malicious-adapter"


def test_registry_snapshot_is_immutable():
    registry = AdapterRegistry.from_adapters(
        (registration(),)
    )

    with pytest.raises(AttributeError):
        registry._adapters = ()


def test_accepted_result_carries_provenance_and_audit():
    result = validator().validate(request())

    assert result.boundary_status is BoundaryStatus.ACCEPTED
    assert result.provenance_reference == "prov-1"
    assert result.audit_reference == "lhicf-boundary:corr-1"


def test_boundary_never_produces_execution_authority():
    result = validator().validate(request())

    assert result.boundary_status is BoundaryStatus.ACCEPTED

    # LHICF returns normalized boundary information only.
    # It does not expose authorization/capability-grant fields.
    assert not hasattr(result, "authorization_decision")
    assert not hasattr(result, "granted_capabilities")
    assert not hasattr(result, "capability_grant")


def test_boundary_does_not_execute_host_operations():
    result = validator().validate(
        request(operation="READ_STATE")
    )

    assert result.boundary_status is BoundaryStatus.ACCEPTED
    assert result.normalized_result is None
    assert result.host_identity_reference is None
    assert result.capability_observation_reference is None
