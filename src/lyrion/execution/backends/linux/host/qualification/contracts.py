from __future__ import annotations

from dataclasses import dataclass

from lyrion.execution.backends.linux.host.negotiation.contracts import (
    CapabilityNegotiationResult,
    CapabilityNegotiationStatus,
)


@dataclass(frozen=True, slots=True)
class AdaptiveQualificationResult:
    """
    LYRION project-level qualification result.

    This is an integration/result model only. It does not grant
    authorization, apply enforcement, or execute anything.
    """

    status: CapabilityNegotiationStatus
    profile_id: str
    evidence_digest: str
    negotiation: CapabilityNegotiationResult

    @property
    def execution_authorized(self) -> bool:
        return self.negotiation.execution_authorized

    @property
    def enforcement_verified(self) -> bool:
        return self.negotiation.enforcement_verified

    @property
    def qualified(self) -> bool:
        return self.status is CapabilityNegotiationStatus.QUALIFIED

    @property
    def degraded(self) -> bool:
        return self.status is CapabilityNegotiationStatus.DEGRADED

    @property
    def blocked(self) -> bool:
        return self.status is CapabilityNegotiationStatus.BLOCKED
