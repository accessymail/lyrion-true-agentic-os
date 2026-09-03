"""Provider-neutral Cognitive Runtime implementation boundary."""

from __future__ import annotations

from typing import Protocol

from lyrion.cognition.contracts import (
    CognitiveRequestStatus,
    CognitiveResult,
    ReasonRequest,
)


class CognitiveRuntime(Protocol):
    """Abstract boundary for substantive cognitive processing."""

    async def reason(
        self,
        request: ReasonRequest,
    ) -> CognitiveResult:
        """Process one bounded reasoning request."""


class UnavailableCognitiveRuntime:
    """Fail-closed runtime used until a model-backed implementation exists."""

    async def reason(
        self,
        request: ReasonRequest,
    ) -> CognitiveResult:
        """Reject execution because no cognitive provider is configured."""
        return CognitiveResult(
            request_id=request.request_id,
            status=CognitiveRequestStatus.REJECTED,
            answer=None,
            proposed_plan=(),
            uncertainty=1.0,
            confidence=0.0,
            evidence_refs=(),
            provider=None,
            model=None,
            verification_required=True,
            created_at=request.created_at,
        )
