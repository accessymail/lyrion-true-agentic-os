"""Provider-neutral Voice Provider Abstraction.

Milestone: 19.4.4 — Voice Provider Abstraction

This module defines the control-plane and execution-boundary contracts used by
Lyri's Voice Runtime to interact with replaceable voice providers.

Provider adapters translate between these contracts and provider-specific APIs.
They do not own authorization, identity, authentication, or execution authority.

Security boundaries:
- Provider selection does not grant authorization.
- Provider output is untrusted external data.
- Provider identity is metadata, not an identity authority.
- Provider adapters remain replaceable.
- Routing policy belongs above provider adapters.
- The gateway is an execution boundary, not an authorization authority.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from lyrion.voice.cloning import VoiceCloneRequest, VoiceCloneResult


class VoiceProviderCapability(StrEnum):
    """Capabilities a provider may advertise."""

    SYNTHESIS = "synthesis"
    STREAMING = "streaming"
    REALTIME = "realtime"
    CLONING = "cloning"
    VOICE_DESIGN = "voice_design"


class VoiceOutputFormat(StrEnum):
    """Provider-neutral audio output formats."""

    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    PCM = "pcm"


class VoiceProviderHealthStatus(StrEnum):
    """Normalized provider health state."""

    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class VoiceProviderErrorCode(StrEnum):
    """Normalized provider failure categories."""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    INVALID_REQUEST = "invalid_request"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    TEMPORARY = "temporary"
    PROVIDER_FAILURE = "provider_failure"
    OUTPUT_INVALID = "output_invalid"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class VoiceProviderDescriptor:
    """Static provider metadata exposed to routing/control-plane logic."""

    provider_id: str
    display_name: str
    capabilities: frozenset[VoiceProviderCapability]
    models: tuple[str, ...] = ()
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be blank")

        if not self.display_name.strip():
            raise ValueError("display_name must not be blank")

        if any(not model.strip() for model in self.models):
            raise ValueError("provider models must not be blank")

        if len(set(self.models)) != len(self.models):
            raise ValueError("provider models must be unique")


@dataclass(frozen=True, slots=True)
class VoiceProviderHealth:
    """Normalized provider health information."""

    provider_id: str
    status: VoiceProviderHealthStatus
    checked_at: datetime
    detail: str | None = None

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be blank")

        if self.checked_at.tzinfo is None or self.checked_at.utcoffset() is None:
            raise ValueError("checked_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class VoiceProviderError:
    """Normalized provider error.

    Raw provider exceptions remain inside the adapter boundary.
    """

    code: VoiceProviderErrorCode
    message: str
    provider_id: str
    retryable: bool = False

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("message must not be blank")

        if not self.provider_id.strip():
            raise ValueError("provider_id must not be blank")


class VoiceProviderInvocationError(RuntimeError):
    """Normalized exception raised when a provider invocation fails."""

    def __init__(self, error: VoiceProviderError) -> None:
        self.error = error
        super().__init__(error.message)


@dataclass(frozen=True, slots=True)
class VoiceSynthesisRequest:
    """Provider-neutral request for voice synthesis."""

    request_id: str
    text: str
    voice_reference: str
    output_format: VoiceOutputFormat = VoiceOutputFormat.WAV
    model: str | None = None
    locale: str | None = None

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must not be blank")

        if not self.text.strip():
            raise ValueError("text must not be blank")

        if not self.voice_reference.strip():
            raise ValueError("voice_reference must not be blank")

        if self.model is not None and not self.model.strip():
            raise ValueError("model must not be blank when supplied")

        if self.locale is not None and not self.locale.strip():
            raise ValueError("locale must not be blank when supplied")


@dataclass(frozen=True, slots=True)
class VoiceSynthesisResult:
    """Provider-neutral synthesis result metadata."""

    request_id: str
    provider_id: str
    representation_ref: str
    output_format: VoiceOutputFormat
    created_at: datetime
    duration_seconds: float | None = None
    provenance: str = ""

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must not be blank")

        if not self.provider_id.strip():
            raise ValueError("provider_id must not be blank")

        if not self.representation_ref.strip():
            raise ValueError("representation_ref must not be blank")

        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")

        if self.duration_seconds is not None and self.duration_seconds <= 0:
            raise ValueError("duration_seconds must be greater than zero")


@dataclass(frozen=True, slots=True)
class VoiceAudioChunk:
    """Provider-neutral bounded streaming audio chunk."""

    request_id: str
    sequence: int
    audio: bytes
    output_format: VoiceOutputFormat

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must not be blank")

        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")

        if not self.audio:
            raise ValueError("audio must not be empty")


class VoiceProvider(Protocol):
    """Base provider boundary for non-streaming synthesis."""

    @property
    def descriptor(self) -> VoiceProviderDescriptor:
        """Return provider metadata."""

    async def synthesize(
        self,
        request: VoiceSynthesisRequest,
    ) -> VoiceSynthesisResult:
        """Synthesize speech through the provider adapter."""


@runtime_checkable
class VoiceStreamingProvider(Protocol):
    """Optional streaming synthesis capability boundary."""

    def stream_synthesis(
        self,
        request: VoiceSynthesisRequest,
    ) -> AsyncIterator[VoiceAudioChunk]:
        """Return an async iterator of provider-neutral streaming chunks."""


@runtime_checkable
class VoiceRealtimeProvider(Protocol):
    """Optional realtime capability boundary."""

    async def open_realtime_session(self, session_id: str) -> None:
        """Open a realtime provider session."""

    async def close_realtime_session(self, session_id: str) -> None:
        """Close a realtime provider session."""


class VoiceCloneCapability(Protocol):
    """Optional cloning capability boundary."""

    async def clone(
        self,
        request: VoiceCloneRequest,
    ) -> VoiceCloneResult:
        """Perform provider-specific cloning behind the adapter boundary."""


class VoiceProviderRegistry:
    """Deterministic registry for replaceable voice provider adapters.

    Registration is explicit and duplicate provider IDs are rejected.
    This registry does not perform authorization or routing policy.
    """

    def __init__(self) -> None:
        self._providers: dict[str, VoiceProvider] = {}

    def register(self, provider: VoiceProvider) -> None:
        """Register one provider adapter."""

        provider_id = provider.descriptor.provider_id

        if provider_id in self._providers:
            raise ValueError(
                f"voice provider already registered: {provider_id}",
            )

        self._providers[provider_id] = provider

    def get(self, provider_id: str) -> VoiceProvider:
        """Return a registered provider by stable provider ID."""

        if not provider_id.strip():
            raise ValueError("provider_id must not be blank")

        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise KeyError(
                f"voice provider not registered: {provider_id}",
            ) from exc

    def list_descriptors(self) -> tuple[VoiceProviderDescriptor, ...]:
        """Return deterministic provider descriptors sorted by provider ID."""

        return tuple(
            provider.descriptor
            for provider in sorted(
                self._providers.values(),
                key=lambda item: item.descriptor.provider_id,
            )
        )

    def has_capability(
        self,
        provider_id: str,
        capability: VoiceProviderCapability,
    ) -> bool:
        """Return whether a provider advertises a requested capability."""

        return capability in self.get(provider_id).descriptor.capabilities

    def clear(self) -> None:
        """Clear providers for controlled startup/test lifecycle management."""

        self._providers.clear()


class VoiceProviderRoutingView:
    """Read-only capability view used by higher-level routing policy."""

    def __init__(self, registry: VoiceProviderRegistry) -> None:
        self._registry = registry

    def eligible_providers(
        self,
        capability: VoiceProviderCapability,
    ) -> tuple[VoiceProviderDescriptor, ...]:
        """Return enabled providers advertising the requested capability."""

        return tuple(
            descriptor
            for descriptor in self._registry.list_descriptors()
            if descriptor.enabled and capability in descriptor.capabilities
        )


class VoiceProviderGateway:
    """Controlled execution boundary between Voice Runtime and providers.

    The gateway does not decide which provider should win. Higher-level
    routing logic supplies the selected provider ID. The gateway verifies
    that the provider is enabled, advertises the required capability, and
    that returned results/chunks remain correlated to the originating request.
    """

    def __init__(self, registry: VoiceProviderRegistry) -> None:
        self._registry = registry

    def _provider(
        self,
        provider_id: str,
        capability: VoiceProviderCapability,
    ) -> VoiceProvider:
        provider = self._registry.get(provider_id)
        descriptor = provider.descriptor

        if not descriptor.enabled:
            raise VoiceProviderInvocationError(
                VoiceProviderError(
                    code=VoiceProviderErrorCode.PROVIDER_FAILURE,
                    message=f"voice provider is disabled: {provider_id}",
                    provider_id=provider_id,
                    retryable=False,
                ),
            )

        if capability not in descriptor.capabilities:
            raise VoiceProviderInvocationError(
                VoiceProviderError(
                    code=VoiceProviderErrorCode.UNSUPPORTED_CAPABILITY,
                    message=(
                        f"voice provider does not support "
                        f"{capability.value}: {provider_id}"
                    ),
                    provider_id=provider_id,
                    retryable=False,
                ),
            )

        return provider

    async def synthesize(
        self,
        provider_id: str,
        request: VoiceSynthesisRequest,
    ) -> VoiceSynthesisResult:
        """Execute bounded provider synthesis through the gateway."""

        provider = self._provider(
            provider_id,
            VoiceProviderCapability.SYNTHESIS,
        )

        try:
            result = await provider.synthesize(request)
        except VoiceProviderInvocationError:
            raise

        if result.request_id != request.request_id:
            raise VoiceProviderInvocationError(
                VoiceProviderError(
                    code=VoiceProviderErrorCode.OUTPUT_INVALID,
                    message="provider response request_id does not match request",
                    provider_id=provider_id,
                    retryable=False,
                ),
            )

        if result.provider_id != provider_id:
            raise VoiceProviderInvocationError(
                VoiceProviderError(
                    code=VoiceProviderErrorCode.OUTPUT_INVALID,
                    message="provider response provider_id does not match provider",
                    provider_id=provider_id,
                    retryable=False,
                ),
            )

        return result

    async def stream_synthesis(
        self,
        provider_id: str,
        request: VoiceSynthesisRequest,
    ) -> AsyncIterator[VoiceAudioChunk]:
        """Execute provider streaming synthesis through the gateway."""

        provider = self._provider(
            provider_id,
            VoiceProviderCapability.STREAMING,
        )

        if not isinstance(provider, VoiceStreamingProvider):
            raise VoiceProviderInvocationError(
                VoiceProviderError(
                    code=VoiceProviderErrorCode.UNSUPPORTED_CAPABILITY,
                    message=(
                        f"provider advertises streaming but does not "
                        f"implement the streaming contract: {provider_id}"
                    ),
                    provider_id=provider_id,
                    retryable=False,
                ),
            )

        async for chunk in provider.stream_synthesis(request):
            if chunk.request_id != request.request_id:
                raise VoiceProviderInvocationError(
                    VoiceProviderError(
                        code=VoiceProviderErrorCode.OUTPUT_INVALID,
                        message=(
                            "provider streaming chunk request_id "
                            "does not match request"
                        ),
                        provider_id=provider_id,
                        retryable=False,
                    ),
                )

            yield chunk

    async def open_realtime_session(
        self,
        provider_id: str,
        session_id: str,
    ) -> None:
        """Open a provider realtime session through the gateway."""

        if not session_id.strip():
            raise ValueError("session_id must not be blank")

        provider = self._provider(
            provider_id,
            VoiceProviderCapability.REALTIME,
        )

        if not isinstance(provider, VoiceRealtimeProvider):
            raise VoiceProviderInvocationError(
                VoiceProviderError(
                    code=VoiceProviderErrorCode.UNSUPPORTED_CAPABILITY,
                    message=(
                        f"provider advertises realtime but does not "
                        f"implement the realtime contract: {provider_id}"
                    ),
                    provider_id=provider_id,
                    retryable=False,
                ),
            )

        await provider.open_realtime_session(session_id)

    async def close_realtime_session(
        self,
        provider_id: str,
        session_id: str,
    ) -> None:
        """Close a provider realtime session through the gateway."""

        if not session_id.strip():
            raise ValueError("session_id must not be blank")

        provider = self._provider(
            provider_id,
            VoiceProviderCapability.REALTIME,
        )

        if not isinstance(provider, VoiceRealtimeProvider):
            raise VoiceProviderInvocationError(
                VoiceProviderError(
                    code=VoiceProviderErrorCode.UNSUPPORTED_CAPABILITY,
                    message=(
                        f"provider advertises realtime but does not "
                        f"implement the realtime contract: {provider_id}"
                    ),
                    provider_id=provider_id,
                    retryable=False,
                ),
            )

        await provider.close_realtime_session(session_id)


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for provider metadata."""

    return datetime.now(UTC)
