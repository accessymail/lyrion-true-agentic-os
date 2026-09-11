from __future__ import annotations

from lyrion.execution.backends.linux.host.contracts import (
    LinuxHostAbstractionSnapshot,
)
from lyrion.execution.backends.linux.host.negotiation.contracts import (
    CapabilityNegotiationResult,
    CapabilityRequirementSet,
)
from lyrion.execution.backends.linux.host.negotiation.engine import (
    CapabilityNegotiationEngine,
)

from .contracts import AdaptiveQualificationResult


class AdaptiveQualificationEngine:
    """
    Integrates host capability discovery with capability negotiation.

    The engine is observational only.

    It:
      - evaluates the supplied host snapshot;
      - delegates capability semantics to the validated negotiation engine;
      - preserves deterministic negotiation evidence.

    It does NOT:
      - authorize execution;
      - apply Linux security controls;
      - execute processes;
      - modify the host;
      - silently downgrade required controls.
    """

    def __init__(
        self,
        *,
        negotiation_engine: CapabilityNegotiationEngine | None = None,
    ) -> None:
        self._negotiation_engine = (
            negotiation_engine or CapabilityNegotiationEngine()
        )

    def qualify(
        self,
        *,
        host_snapshot: LinuxHostAbstractionSnapshot,
        requirements: CapabilityRequirementSet,
    ) -> AdaptiveQualificationResult:
        negotiation = self._negotiation_engine.negotiate(
            host_snapshot=host_snapshot,
            requirements=requirements,
        )

        self._assert_boundary(negotiation)

        return AdaptiveQualificationResult(
            status=negotiation.status,
            profile_id=negotiation.profile_id,
            evidence_digest=negotiation.evidence_digest,
            negotiation=negotiation,
        )

    @staticmethod
    def _assert_boundary(
        result: CapabilityNegotiationResult,
    ) -> None:
        if result.execution_authorized:
            raise RuntimeError(
                "Capability qualification cannot authorize execution."
            )

        if result.enforcement_verified:
            raise RuntimeError(
                "Capability qualification cannot claim enforcement verification."
            )
