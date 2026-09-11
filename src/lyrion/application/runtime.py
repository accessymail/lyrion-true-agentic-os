"""Application Runtime orchestration boundary.

The Application Runtime owns application-level composition and lineage
validation. It does not authenticate providers, authorize capabilities,
admit execution, or execute privileged operations.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from lyrion.application.contracts import (
    ApplicationCorrelationContext,
    ApplicationCorrelationError,
    ApplicationPrincipalContext,
    ApplicationRuntimeError,
    ApplicationSessionContext,
    ApplicationSessionError,
    ApplicationTurnContext,
    ApplicationTurnError,
)
from lyrion.cognition.contracts import CognitiveResult, ReasonRequest
from lyrion.cognition.runtime import CognitiveRuntime
from lyrion.core.types import DecisionId
from lyrion.execution.contracts import ExecutionPlan
from lyrion.execution.sandbox import SandboxConfig
from lyrion.integration.proactive_execution import CapabilityIntent
from lyrion.piae.contracts import DecisionCandidate
from lyrion.rpii.contracts import RPIIContext, RPIICycleResult
from lyrion.rpii.service import RPIIService
from lyrion.voice.providers import VoiceSynthesisRequest
from lyrion.voice.streaming.contracts import (
    VoiceInterruptionRequest,
    VoiceInterruptionResult,
    VoiceOutputChunk,
    VoiceStreamSession,
)
from lyrion.voice.streaming.service import VoiceStreamingService

Clock = Callable[[], datetime]
SynthesisFactory = Callable[[CognitiveResult], VoiceSynthesisRequest]


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class ApplicationRuntime:
    """Application-level security and lineage boundary.

    Security invariant:

        Observation != Opportunity != Decision != Authorization != Execution

    This class deliberately exposes none of the authority-granting or
    privileged execution operations.
    """

    cognitive_runtime: CognitiveRuntime | None = None
    rpii_service: RPIIService | None = None
    voice_streaming_service: VoiceStreamingService | None = None
    clock: Clock = utc_now

    def bind_session(
        self,
        *,
        principal: ApplicationPrincipalContext,
        session: ApplicationSessionContext,
    ) -> ApplicationSessionContext:
        """Bind a previously authenticated principal to an application session."""

        if session.principal_id != principal.principal_id:
            raise ApplicationSessionError(
                "session principal does not match authenticated principal"
            )

        self._validate_session_timestamp(session.created_at)

        return session

    def validate_correlation(
        self,
        context: ApplicationCorrelationContext,
        *,
        expected_session_id: str | None = None,
    ) -> ApplicationCorrelationContext:
        """Validate correlation lineage and optional session ownership."""

        if (
            expected_session_id is not None
            and context.application_session_id != expected_session_id.strip()
        ):
            raise ApplicationCorrelationError(
                "correlation session does not match application session"
            )

        return context

    def bind_turn(
        self,
        *,
        session: ApplicationSessionContext,
        correlation: ApplicationCorrelationContext,
        turn: ApplicationTurnContext,
    ) -> ApplicationTurnContext:
        """Validate application turn lineage against its parent contexts."""

        if turn.application_session_id != session.application_session_id:
            raise ApplicationTurnError(
                "turn session does not match application session"
            )

        if correlation.application_session_id != session.application_session_id:
            raise ApplicationCorrelationError(
                "correlation session does not match application session"
            )

        if turn.correlation_id != correlation.correlation_id:
            raise ApplicationTurnError(
                "turn correlation does not match correlation context"
            )

        return turn

    async def start_voice_session(
        self,
        *,
        session: ApplicationSessionContext,
        correlation: ApplicationCorrelationContext,
    ) -> VoiceStreamSession:
        """Start a voice stream bound to the validated application session."""

        self.validate_correlation(
            correlation,
            expected_session_id=session.application_session_id,
        )

        service = self.voice_streaming_service
        if service is None:
            raise ApplicationRuntimeError(
                "voice streaming service is not configured",
            )

        if correlation.voice_session_id is not None:
            raise ApplicationCorrelationError(
                "voice session must not already exist when starting a voice session",
            )

        result = await service.start(
            correlation_id=correlation.correlation_id,
        )

        if result.correlation_id != correlation.correlation_id:
            raise ApplicationCorrelationError(
                "voice session result does not match correlation lineage",
            )

        return result

    def bind_voice_session(
        self,
        *,
        session: ApplicationSessionContext,
        correlation: ApplicationCorrelationContext,
        voice_session: VoiceStreamSession,
    ) -> ApplicationCorrelationContext:
        """Bind a verified voice session into immutable application lineage."""

        self.validate_correlation(
            correlation,
            expected_session_id=session.application_session_id,
        )

        if voice_session.correlation_id != correlation.correlation_id:
            raise ApplicationCorrelationError(
                "voice session does not match correlation lineage",
            )

        if correlation.voice_session_id is not None:
            raise ApplicationCorrelationError(
                "correlation already has a voice session bound",
            )

        return replace(
            correlation,
            voice_session_id=voice_session.session_id,
        )

    async def process_text_turn(
        self,
        *,
        session: ApplicationSessionContext,
        correlation: ApplicationCorrelationContext,
        provider_id: str,
        request: ReasonRequest,
        synthesis_factory: SynthesisFactory,
    ) -> AsyncIterator[VoiceOutputChunk]:
        """Process one application-bound text turn through the voice runtime."""

        voice_session = await self._get_bound_voice_session(
            session=session,
            correlation=correlation,
        )

        if (
            correlation.request_id is not None
            and request.request_id != correlation.request_id
        ):
            raise ApplicationCorrelationError(
                "request does not match correlation lineage",
            )

        service = self.voice_streaming_service
        if service is None:
            raise ApplicationRuntimeError(
                "voice streaming service is not configured",
            )

        async for chunk in service.process_text_turn(
            session_id=voice_session.session_id,
            provider_id=provider_id,
            request=request,
            synthesis_factory=synthesis_factory,
        ):
            if chunk.session_id != voice_session.session_id:
                raise ApplicationCorrelationError(
                    "voice output session does not match correlation lineage",
                )

            if (
                correlation.request_id is not None
                and chunk.request_id != correlation.request_id
            ):
                raise ApplicationCorrelationError(
                    "voice output request does not match correlation lineage",
                )

            yield chunk

    async def _get_bound_voice_session(
        self,
        *,
        session: ApplicationSessionContext,
        correlation: ApplicationCorrelationContext,
    ) -> VoiceStreamSession:
        """Resolve and verify the voice session bound to application lineage."""

        self.validate_correlation(
            correlation,
            expected_session_id=session.application_session_id,
        )

        voice_session_id = correlation.voice_session_id
        if voice_session_id is None:
            raise ApplicationCorrelationError(
                "voice session is required for voice operation",
            )

        service = self.voice_streaming_service
        if service is None:
            raise ApplicationRuntimeError(
                "voice streaming service is not configured",
            )

        voice_session = await service.get(voice_session_id)

        if voice_session.correlation_id != correlation.correlation_id:
            raise ApplicationCorrelationError(
                "voice session does not match correlation lineage",
            )

        return voice_session

    async def interrupt(
        self,
        *,
        session: ApplicationSessionContext,
        correlation: ApplicationCorrelationContext,
        request: VoiceInterruptionRequest,
    ) -> VoiceInterruptionResult:
        """Interrupt one application-bound active voice turn."""

        voice_session = await self._get_bound_voice_session(
            session=session,
            correlation=correlation,
        )

        if request.session_id != voice_session.session_id:
            raise ApplicationCorrelationError(
                "voice interruption session does not match correlation lineage",
            )

        if (
            correlation.request_id is not None
            and request.request_id != correlation.request_id
        ):
            raise ApplicationCorrelationError(
                "voice interruption request does not match correlation lineage",
            )

        service = self.voice_streaming_service
        if service is None:
            raise ApplicationRuntimeError(
                "voice streaming service is not configured",
            )

        result = await service.interrupt(request)

        if result.session_id != voice_session.session_id:
            raise ApplicationCorrelationError(
                "voice interruption result does not match correlation lineage",
            )

        if (
            correlation.request_id is not None
            and result.request_id != correlation.request_id
        ):
            raise ApplicationCorrelationError(
                "voice interruption result does not match correlation lineage",
            )

        return result

    async def cancel(
        self,
        *,
        session: ApplicationSessionContext,
        correlation: ApplicationCorrelationContext,
    ) -> VoiceStreamSession:
        """Cancel the voice operation bound to an application session."""

        voice_session = await self._get_bound_voice_session(
            session=session,
            correlation=correlation,
        )

        service = self.voice_streaming_service
        if service is None:
            raise ApplicationRuntimeError(
                "voice streaming service is not configured",
            )

        result = await service.cancel(voice_session.session_id)

        if result.session_id != voice_session.session_id:
            raise ApplicationCorrelationError(
                "voice cancellation result does not match correlation lineage",
            )

        if result.correlation_id != correlation.correlation_id:
            raise ApplicationCorrelationError(
                "voice cancellation result does not match correlation lineage",
            )

        return result

    async def reason(
        self,
        *,
        session: ApplicationSessionContext,
        correlation: ApplicationCorrelationContext,
        request: ReasonRequest,
    ) -> CognitiveResult:
        """Delegate one validated reasoning request to the Cognitive Runtime."""
        self.validate_correlation(
            correlation,
            expected_session_id=session.application_session_id,
        )

        if (
            correlation.request_id is not None
            and request.request_id != correlation.request_id
        ):
            raise ApplicationCorrelationError(
                "request does not match correlation lineage",
            )

        runtime = self.cognitive_runtime
        if runtime is None:
            raise ApplicationRuntimeError(
                "cognitive runtime is not configured",
            )

        return await runtime.reason(request)

    def run_rpii(
        self,
        *,
        session: ApplicationSessionContext,
        correlation: ApplicationCorrelationContext,
        context: RPIIContext,
        candidates: tuple[DecisionCandidate, ...],
        intent: CapabilityIntent | None,
        plan: ExecutionPlan | None,
        sandbox: SandboxConfig | None,
        decision_id: DecisionId | None = None,
        now: datetime | None = None,
    ) -> RPIICycleResult:
        """Delegate one validated interaction to the existing RPII boundary."""

        self.validate_correlation(
            correlation,
            expected_session_id=session.application_session_id,
        )

        if context.session_id != session.application_session_id:
            raise ApplicationSessionError(
                "RPII context session does not match application session",
            )

        if (
            correlation.interaction_id is not None
            and context.interaction_id != correlation.interaction_id
        ):
            raise ApplicationCorrelationError(
                "RPII interaction does not match correlation context",
            )

        service = self.rpii_service
        if service is None:
            raise ApplicationRuntimeError(
                "RPII service is not configured",
            )

        return service.run_once(
            context,
            candidates,
            intent,
            plan,
            sandbox,
            decision_id=decision_id,
            now=now,
        )

    def validate_session_ownership(
        self,
        *,
        principal: ApplicationPrincipalContext,
        session: ApplicationSessionContext,
    ) -> None:
        """Fail closed when a session is not owned by the authenticated principal."""

        if session.principal_id != principal.principal_id:
            raise ApplicationSessionError(
                "application session is not owned by authenticated principal"
            )

    def _validate_session_timestamp(self, created_at: datetime) -> None:
        """Reject malformed or future-dated session creation timestamps."""

        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise ApplicationSessionError(
                "application session created_at must be timezone-aware"
            )

        now = self.clock()

        if now.tzinfo is None or now.utcoffset() is None:
            raise RuntimeError("application clock must return timezone-aware datetime")

        if created_at.astimezone(UTC) > now.astimezone(UTC):
            raise ApplicationSessionError(
                "application session created_at cannot be in the future"
            )
