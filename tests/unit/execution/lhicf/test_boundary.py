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
        request_id="req-1",
        decision_id=DecisionId("decision:req-1"),
        task_id=TaskId("task:req-1"),
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope="HOST",
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        autonomy_level=AutonomyLevel.L1,
        risk_level=RiskLevel.LOW,
        policy_version="aegis-policy-v1",
        idempotency_key=IdempotencyKey("idem:req-1"),
        requested_at=now,
        expires_at=now + timedelta(minutes=5),
        justification="LHICF boundary unit test.",
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
        reason="Authorized.",
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
    expires_delta=timedelta(minutes=5),
    adapter_id="os-state",
    operation="READ_STATE",
    scope="HOST",
    requested_offset=timedelta(0),
):
    if admission is _DEFAULT_ADMISSION:
        admission = authoritative_admission()

    if isinstance(admission, ExecutionAdmission):
        base_requested_at = admission.execution_request.requested_at
        base_expires_at = admission.execution_request.expires_at
        request_id = admission.request_id
        correlation_id = (
            admission.execution_request.correlation_id
            or "corr-1"
        )
    else:
        base_requested_at = datetime.now(UTC)
        base_expires_at = base_requested_at + timedelta(minutes=5)
        request_id = "req-1"
        correlation_id = "corr-1"

    requested_at = base_requested_at + requested_offset

    if isinstance(admission, ExecutionAdmission):
        expires_at = requested_at + expires_delta
    else:
        expires_at = (
            requested_at + expires_delta
            if expires_delta is not None
            else base_expires_at
        )

    return LHICFRequest(
        request_id=request_id,
        execution_admission=admission,
        sandbox_context=object(),
        adapter_id=adapter_id,
        operation=operation,
        target_scope=scope,
        correlation_id=correlation_id,
        provenance_context="prov-1",
        requested_at=requested_at,
        expires_at=expires_at,
    )


def validator():
    registry = AdapterRegistry.from_adapters((registration(),))
    return LHICFBoundaryValidator(registry)


def test_valid_request_is_accepted_without_authorization_reconstruction():
    result = validator().validate(request())

    assert result.boundary_status is BoundaryStatus.ACCEPTED
    assert result.adapter_id == "os-state"
    assert result.provenance_reference == "prov-1"


def test_missing_admission_is_blocked():
    result = validator().validate(request(admission=None))

    assert result.boundary_status is BoundaryStatus.BLOCKED


def test_expired_request_is_stale():
    result = validator().validate(
        request(
            requested_offset=timedelta(minutes=-5),
            expires_delta=timedelta(minutes=1),
        )
    )

    assert result.boundary_status is BoundaryStatus.STALE


def test_unknown_adapter_is_blocked():
    result = validator().validate(request(adapter_id="unknown"))

    assert result.boundary_status is BoundaryStatus.BLOCKED


def test_unsupported_operation_is_blocked():
    result = validator().validate(request(operation="DELETE"))

    assert result.boundary_status is BoundaryStatus.BLOCKED


def test_unsupported_scope_is_blocked():
    result = validator().validate(request(scope="FILESYSTEM"))

    assert result.boundary_status is BoundaryStatus.BLOCKED


def test_revoked_adapter_is_not_selectable():
    registry = AdapterRegistry.from_adapters(
        (registration(lifecycle=AdapterLifecycleState.REVOKED),)
    )

    result = LHICFBoundaryValidator(registry).validate(request())

    assert result.boundary_status is BoundaryStatus.BLOCKED


def test_operation_must_be_normalized():
    with pytest.raises(ValueError, match="normalized uppercase"):
        request(operation="read_state")


def test_registry_requires_deterministic_order():
    with pytest.raises(ValueError, match="deterministically sorted"):
        AdapterRegistry.from_adapters(
            (
                registration(adapter_id="z-adapter"),
                registration(adapter_id="a-adapter"),
            )
        )


def test_duplicate_adapter_ids_are_rejected():
    with pytest.raises(ValueError, match="duplicate adapter_id"):
        AdapterRegistry.from_adapters(
            (
                registration(),
                registration(),
            )
        )


def test_accepted_result_requires_provenance_and_audit():
    from lyrion.execution.lhicf.contracts import LHICFResult

    with pytest.raises(ValueError):
        LHICFResult(
            boundary_status=BoundaryStatus.ACCEPTED,
            adapter_id="os-state",
            operation="READ_STATE",
            host_identity_reference=None,
            capability_observation_reference=None,
            normalized_result=None,
            provenance_reference=None,
            audit_reference=None,
        )
