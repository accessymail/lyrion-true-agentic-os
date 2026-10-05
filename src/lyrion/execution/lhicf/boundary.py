"""LHICF boundary validation.

This validator deliberately does not perform host operations.
It verifies that an already-admitted execution context is suitable for
entering the controlled host boundary.
"""

from __future__ import annotations

from dataclasses import dataclass

from lyrion.capabilities.gateway import ExecutionAdmission

from .contracts import BoundaryStatus, LHICFRequest, LHICFResult
from .registry import AdapterRegistry, AdapterSelectionError


@dataclass(frozen=True, slots=True)
class LHICFBoundaryValidator:
    registry: AdapterRegistry

    def validate(self, request: LHICFRequest) -> LHICFResult:
        """Validate boundary admission without executing anything."""

        if request.expired:
            return LHICFResult(
                boundary_status=BoundaryStatus.STALE,
                adapter_id=request.adapter_id,
                operation=request.operation,
                host_identity_reference=None,
                capability_observation_reference=None,
                normalized_result=None,
                provenance_reference=None,
                audit_reference=None,
                failure_reason="execution admission has expired",
            )

        if request.execution_admission is None:
            return LHICFResult(
                boundary_status=BoundaryStatus.BLOCKED,
                adapter_id=request.adapter_id,
                operation=request.operation,
                host_identity_reference=None,
                capability_observation_reference=None,
                normalized_result=None,
                provenance_reference=None,
                audit_reference=None,
                failure_reason="execution admission is required",
            )

        admission = request.execution_admission

        if not isinstance(admission, ExecutionAdmission):
            return LHICFResult(
                boundary_status=BoundaryStatus.BLOCKED,
                adapter_id=request.adapter_id,
                operation=request.operation,
                host_identity_reference=None,
                capability_observation_reference=None,
                normalized_result=None,
                provenance_reference=None,
                audit_reference=None,
                failure_reason=(
                    "execution admission must be the authoritative "
                    "ExecutionAdmission type"
                ),
            )

        if not admission.admitted:
            return LHICFResult(
                boundary_status=BoundaryStatus.BLOCKED,
                adapter_id=request.adapter_id,
                operation=request.operation,
                host_identity_reference=None,
                capability_observation_reference=None,
                normalized_result=None,
                provenance_reference=None,
                audit_reference=None,
                failure_reason="execution admission is not admitted",
            )

        execution = admission.execution_request

        binding_mismatch = (
            admission.request_id != request.request_id
            or execution.request_id != request.request_id
            or admission.capability_id != execution.capability_id
            or admission.capability_id != request.execution_admission.capability_id
            or execution.capability_id != request.execution_admission.capability_id
            or execution.target_scope != admission.target_scope
            or execution.target_scope != request.target_scope
            or execution.correlation_id != request.correlation_id
            or execution.requested_at != request.requested_at
            or execution.expires_at != request.expires_at
        )

        if binding_mismatch:
            return LHICFResult(
                boundary_status=BoundaryStatus.BLOCKED,
                adapter_id=request.adapter_id,
                operation=request.operation,
                host_identity_reference=None,
                capability_observation_reference=None,
                normalized_result=None,
                provenance_reference=None,
                audit_reference=None,
                failure_reason=(
                    "execution admission is not bound to the LHICF request"
                ),
            )

        try:
            adapter = self.registry.select(
                adapter_id=request.adapter_id,
                operation=request.operation,
                target_scope=request.target_scope,
            )
        except AdapterSelectionError as exc:
            return LHICFResult(
                boundary_status=BoundaryStatus.BLOCKED,
                adapter_id=request.adapter_id,
                operation=request.operation,
                host_identity_reference=None,
                capability_observation_reference=None,
                normalized_result=None,
                provenance_reference=None,
                audit_reference=None,
                failure_reason=str(exc),
            )

        if not adapter.integrity_reference.strip():
            return LHICFResult(
                boundary_status=BoundaryStatus.REJECTED,
                adapter_id=request.adapter_id,
                operation=request.operation,
                host_identity_reference=None,
                capability_observation_reference=None,
                normalized_result=None,
                provenance_reference=None,
                audit_reference=None,
                failure_reason="adapter integrity reference is missing",
            )

        return LHICFResult(
            boundary_status=BoundaryStatus.ACCEPTED,
            adapter_id=adapter.adapter_id,
            operation=request.operation,
            host_identity_reference=None,
            capability_observation_reference=None,
            normalized_result=None,
            provenance_reference=request.provenance_context,
            audit_reference=f"lhicf-boundary:{request.correlation_id}",
        )
