"""Read-only Linux host-state adapter for LHICF.

Security boundary:
    LHICF Core -> OS_STATE_READONLY -> LinuxHostDiscovery

This adapter observes host state only. It does not authorize execution,
grant capabilities, execute processes, invoke a shell, or mutate the host.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any

from lyrion.execution.backends.linux.host.discovery import LinuxHostDiscovery

from ..contracts import (
    AdapterLifecycleState,
    AdapterRegistration,
    BoundaryStatus,
    LHICFRequest,
    LHICFResult,
)


class OSStateReadonlyAdapter:
    """Controlled, observation-only Linux host-state adapter."""

    ADAPTER_ID = "os-state"
    ADAPTER_VERSION = "1.0.0"
    CONTRACT_VERSION = "1.0.0"
    OPERATION = "READ_STATE"
    TARGET_SCOPE = "HOST"
    SECURITY_CLASSIFICATION = "READ_ONLY_HOST_STATE"

    def __init__(
        self,
        *,
        discovery: LinuxHostDiscovery | None = None,
    ) -> None:
        self._discovery = discovery or LinuxHostDiscovery()

    @classmethod
    def registration(cls) -> AdapterRegistration:
        """Return immutable registry metadata for this adapter."""
        return AdapterRegistration(
            adapter_id=cls.ADAPTER_ID,
            adapter_version=cls.ADAPTER_VERSION,
            contract_version=cls.CONTRACT_VERSION,
            supported_operations=frozenset({cls.OPERATION}),
            supported_target_scopes=frozenset({cls.TARGET_SCOPE}),
            required_host_capabilities=frozenset(),
            required_host_qualification=frozenset(),
            security_classification=cls.SECURITY_CLASSIFICATION,
            integrity_reference="sha256:os-state-readonly-v1",
            lifecycle_state=AdapterLifecycleState.AVAILABLE,
        )

    def observe(self, request: LHICFRequest) -> LHICFResult:
        """Observe host state after the LHICF boundary has admitted the request.

        This method does not perform authorization. The caller must first
        validate the request through LHICFBoundaryValidator.
        """
        if request.adapter_id != self.ADAPTER_ID:
            return self._blocked(
                request,
                "adapter identity does not match OS_STATE_READONLY",
            )

        if request.operation != self.OPERATION:
            return self._blocked(
                request,
                "operation is not supported by OS_STATE_READONLY",
            )

        if request.target_scope != self.TARGET_SCOPE:
            return self._blocked(
                request,
                "target scope is not supported by OS_STATE_READONLY",
            )

        if request.execution_admission is None:
            return self._blocked(
                request,
                "execution admission is required",
            )

        if request.expired:
            return LHICFResult(
                boundary_status=BoundaryStatus.STALE,
                adapter_id=self.ADAPTER_ID,
                operation=self.OPERATION,
                host_identity_reference=None,
                capability_observation_reference=None,
                normalized_result=None,
                provenance_reference=None,
                audit_reference=None,
                failure_reason="execution admission has expired",
            )

        try:
            snapshot = self._discovery.discover()
        except Exception as exc:
            return LHICFResult(
                boundary_status=BoundaryStatus.ADAPTER_ERROR,
                adapter_id=self.ADAPTER_ID,
                operation=self.OPERATION,
                host_identity_reference=None,
                capability_observation_reference=None,
                normalized_result=None,
                provenance_reference=None,
                audit_reference=None,
                failure_reason=f"host discovery failed: {type(exc).__name__}",
            )

        identity = asdict(snapshot.identity)
        fingerprint = asdict(snapshot.fingerprint)

        identity_reference = self._reference(identity)
        capability_reference = self._reference(fingerprint)

        normalized_result: dict[str, Any] = {
            "identity": identity,
            "fingerprint": fingerprint,
            "user_id": snapshot.user_id,
            "effective_capabilities": list(snapshot.effective_capabilities),
            "namespaces": list(snapshot.namespaces),
            "notes": list(snapshot.notes),
        }

        return LHICFResult(
            boundary_status=BoundaryStatus.ACCEPTED,
            adapter_id=self.ADAPTER_ID,
            operation=self.OPERATION,
            host_identity_reference=identity_reference,
            capability_observation_reference=capability_reference,
            normalized_result=normalized_result,
            provenance_reference=request.provenance_context,
            audit_reference=f"lhicf-os-state:{request.correlation_id}",
        )

    @staticmethod
    def _reference(value: Any) -> str:
        payload = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")

        return f"sha256:{hashlib.sha256(payload).hexdigest()}"

    @staticmethod
    def _blocked(
        request: LHICFRequest,
        reason: str,
    ) -> LHICFResult:
        return LHICFResult(
            boundary_status=BoundaryStatus.BLOCKED,
            adapter_id=request.adapter_id,
            operation=request.operation,
            host_identity_reference=None,
            capability_observation_reference=None,
            normalized_result=None,
            provenance_reference=None,
            audit_reference=None,
            failure_reason=reason,
        )
