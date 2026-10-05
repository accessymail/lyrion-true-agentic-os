"""Immutable LHICF boundary contracts.

Security invariant:
LHICF consumes execution admission; it never creates or reconstructs
authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class BoundaryStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    UNAVAILABLE = "unavailable"
    STALE = "stale"
    ADAPTER_ERROR = "adapter_error"
    HOST_BOUNDARY_ERROR = "host_boundary_error"
    INVALID_REQUEST = "invalid_request"


class AdapterLifecycleState(StrEnum):
    DECLARED = "declared"
    VALIDATED = "validated"
    REGISTERED = "registered"
    AVAILABLE = "available"
    REVOKED = "revoked"


@dataclass(frozen=True, slots=True)
class LHICFRequest:
    """Request entering the controlled host boundary.

    The request must carry an already-authoritative execution admission.
    No authorization decision or capability grant can be represented here.
    """

    request_id: str
    execution_admission: Any
    sandbox_context: Any
    adapter_id: str
    operation: str
    target_scope: str
    correlation_id: str
    provenance_context: str
    requested_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        for name in (
            "request_id",
            "adapter_id",
            "operation",
            "target_scope",
            "correlation_id",
            "provenance_context",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be blank")


        if self.requested_at.tzinfo is None:
            raise ValueError("requested_at must be timezone-aware")

        if self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")

        if self.expires_at <= self.requested_at:
            raise ValueError("expires_at must be later than requested_at")

        normalized_operation = self.operation.strip().upper()
        if normalized_operation != self.operation:
            raise ValueError("operation must already be normalized uppercase")

    @property
    def expired(self) -> bool:
        return datetime.now(UTC) >= self.expires_at


@dataclass(frozen=True, slots=True)
class LHICFResult:
    """Normalized result leaving the LHICF boundary."""

    boundary_status: BoundaryStatus
    adapter_id: str
    operation: str
    host_identity_reference: str | None
    capability_observation_reference: str | None
    normalized_result: Any | None
    provenance_reference: str | None
    audit_reference: str | None
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.adapter_id.strip():
            raise ValueError("adapter_id must not be blank")

        if not self.operation.strip():
            raise ValueError("operation must not be blank")

        if self.boundary_status is BoundaryStatus.ACCEPTED:
            if not self.provenance_reference:
                raise ValueError(
                    "accepted result requires provenance_reference"
                )
            if not self.audit_reference:
                raise ValueError(
                    "accepted result requires audit_reference"
                )

        if self.boundary_status is not BoundaryStatus.ACCEPTED:
            if self.failure_reason is None or not self.failure_reason.strip():
                raise ValueError(
                    "non-accepted result requires failure_reason"
                )


@dataclass(frozen=True, slots=True)
class AdapterRegistration:
    """Immutable security metadata for one LHICF adapter."""

    adapter_id: str
    adapter_version: str
    contract_version: str
    supported_operations: frozenset[str]
    supported_target_scopes: frozenset[str]
    required_host_capabilities: frozenset[str]
    required_host_qualification: frozenset[str]
    security_classification: str
    integrity_reference: str
    lifecycle_state: AdapterLifecycleState

    def __post_init__(self) -> None:
        for name in (
            "adapter_id",
            "adapter_version",
            "contract_version",
            "security_classification",
            "integrity_reference",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must not be blank")

        if not self.supported_operations:
            raise ValueError("supported_operations must not be empty")

        if not self.supported_target_scopes:
            raise ValueError("supported_target_scopes must not be empty")

        normalized_operations = frozenset(
            operation.strip().upper()
            for operation in self.supported_operations
        )

        if normalized_operations != self.supported_operations:
            raise ValueError(
                "supported_operations must contain normalized uppercase values"
            )
