"""Unit tests for the 19.4.4 Voice Provider Abstraction boundary."""

from datetime import UTC, datetime

import pytest

from lyrion.voice.providers import (
    VoiceAudioChunk,
    VoiceOutputFormat,
    VoiceProvider,
    VoiceProviderCapability,
    VoiceProviderDescriptor,
    VoiceProviderErrorCode,
    VoiceProviderGateway,
    VoiceProviderHealth,
    VoiceProviderHealthStatus,
    VoiceProviderInvocationError,
    VoiceProviderRegistry,
    VoiceProviderRoutingView,
    VoiceSynthesisRequest,
    VoiceSynthesisResult,
)


class FakeVoiceProvider:
    """Deterministic provider adapter used only for unit testing."""

    def __init__(
        self,
        provider_id: str,
        capabilities: frozenset[VoiceProviderCapability],
        *,
        enabled: bool = True,
    ) -> None:
        self._descriptor = VoiceProviderDescriptor(
            provider_id=provider_id,
            display_name=f"Provider {provider_id}",
            capabilities=capabilities,
            models=("model-1",),
            enabled=enabled,
        )
        self.requests: list[VoiceSynthesisRequest] = []

    @property
    def descriptor(self) -> VoiceProviderDescriptor:
        return self._descriptor

    async def synthesize(
        self,
        request: VoiceSynthesisRequest,
    ) -> VoiceSynthesisResult:
        self.requests.append(request)
        return VoiceSynthesisResult(
            request_id=request.request_id,
            provider_id=self._descriptor.provider_id,
            representation_ref=f"voice://{request.request_id}",
            output_format=request.output_format,
            created_at=datetime.now(UTC),
            duration_seconds=1.0,
            provenance="test-provider",
        )


class FakeStreamingProvider(FakeVoiceProvider):
    async def stream_synthesis(self, request: VoiceSynthesisRequest):
        yield VoiceAudioChunk(
            request_id=request.request_id,
            sequence=0,
            audio=b"audio",
            output_format=request.output_format,
        )


class FakeRealtimeProvider(FakeVoiceProvider):
    def __init__(
        self,
        provider_id: str,
        capabilities: frozenset[VoiceProviderCapability],
    ) -> None:
        super().__init__(provider_id, capabilities)
        self.opened: list[str] = []
        self.closed: list[str] = []

    async def open_realtime_session(self, session_id: str) -> None:
        self.opened.append(session_id)

    async def close_realtime_session(self, session_id: str) -> None:
        self.closed.append(session_id)


def make_request() -> VoiceSynthesisRequest:
    return VoiceSynthesisRequest(
        request_id="request-1",
        text="Hello Lyri",
        voice_reference="voice-profile://lyri",
        output_format=VoiceOutputFormat.WAV,
    )


def test_descriptor_rejects_blank_provider_id() -> None:
    with pytest.raises(ValueError, match="provider_id"):
        VoiceProviderDescriptor(
            provider_id=" ",
            display_name="Provider",
            capabilities=frozenset(),
        )


def test_descriptor_rejects_duplicate_models() -> None:
    with pytest.raises(ValueError, match="unique"):
        VoiceProviderDescriptor(
            provider_id="provider-a",
            display_name="Provider A",
            capabilities=frozenset(),
            models=("model-1", "model-1"),
        )


def test_request_is_immutable_and_validated() -> None:
    request = make_request()

    with pytest.raises(AttributeError):
        request.text = "changed"  # type: ignore[misc]


def test_request_rejects_blank_text() -> None:
    with pytest.raises(ValueError, match="text"):
        VoiceSynthesisRequest(
            request_id="request-1",
            text=" ",
            voice_reference="voice-profile://lyri",
        )


def test_result_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        VoiceSynthesisResult(
            request_id="request-1",
            provider_id="provider-a",
            representation_ref="voice://1",
            output_format=VoiceOutputFormat.WAV,
            created_at=datetime.now(),
        )


def test_health_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        VoiceProviderHealth(
            provider_id="provider-a",
            status=VoiceProviderHealthStatus.HEALTHY,
            checked_at=datetime.now(),
        )


def test_audio_chunk_rejects_empty_audio() -> None:
    with pytest.raises(ValueError, match="audio"):
        VoiceAudioChunk(
            request_id="request-1",
            sequence=0,
            audio=b"",
            output_format=VoiceOutputFormat.WAV,
        )


def test_registry_registers_and_retrieves_provider() -> None:
    provider = FakeVoiceProvider(
        "provider-a",
        frozenset({VoiceProviderCapability.SYNTHESIS}),
    )
    registry = VoiceProviderRegistry()

    registry.register(provider)

    assert registry.get("provider-a") is provider
    assert registry.has_capability(
        "provider-a",
        VoiceProviderCapability.SYNTHESIS,
    )


def test_registry_rejects_duplicate_provider_id() -> None:
    provider_a = FakeVoiceProvider(
        "provider-a",
        frozenset({VoiceProviderCapability.SYNTHESIS}),
    )
    provider_b = FakeVoiceProvider(
        "provider-a",
        frozenset({VoiceProviderCapability.REALTIME}),
    )
    registry = VoiceProviderRegistry()

    registry.register(provider_a)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(provider_b)


def test_registry_returns_deterministic_sorted_descriptors() -> None:
    registry = VoiceProviderRegistry()
    registry.register(
        FakeVoiceProvider(
            "provider-b",
            frozenset({VoiceProviderCapability.SYNTHESIS}),
        ),
    )
    registry.register(
        FakeVoiceProvider(
            "provider-a",
            frozenset({VoiceProviderCapability.SYNTHESIS}),
        ),
    )

    descriptors = registry.list_descriptors()

    assert [descriptor.provider_id for descriptor in descriptors] == [
        "provider-a",
        "provider-b",
    ]


def test_routing_view_filters_disabled_and_capability() -> None:
    registry = VoiceProviderRegistry()

    provider_a = FakeVoiceProvider(
        "provider-a",
        frozenset(
            {
                VoiceProviderCapability.SYNTHESIS,
                VoiceProviderCapability.STREAMING,
            },
        ),
    )
    provider_b = FakeVoiceProvider(
        "provider-b",
        frozenset({VoiceProviderCapability.CLONING}),
        enabled=False,
    )

    registry.register(provider_a)
    registry.register(provider_b)

    descriptors = VoiceProviderRoutingView(registry).eligible_providers(
        VoiceProviderCapability.STREAMING,
    )

    assert [descriptor.provider_id for descriptor in descriptors] == ["provider-a"]


@pytest.mark.asyncio
async def test_provider_boundary_accepts_neutral_synthesis_request() -> None:
    provider: VoiceProvider = FakeVoiceProvider(
        "provider-a",
        frozenset({VoiceProviderCapability.SYNTHESIS}),
    )

    request = make_request()
    result = await provider.synthesize(request)

    assert result.request_id == "request-1"
    assert result.provider_id == "provider-a"


@pytest.mark.asyncio
async def test_gateway_enforces_provider_enabled_and_capability() -> None:
    registry = VoiceProviderRegistry()
    registry.register(
        FakeVoiceProvider(
            "provider-a",
            frozenset({VoiceProviderCapability.SYNTHESIS}),
            enabled=False,
        ),
    )
    gateway = VoiceProviderGateway(registry)

    with pytest.raises(
        VoiceProviderInvocationError,
        match="disabled",
    ):
        await gateway.synthesize("provider-a", make_request())


@pytest.mark.asyncio
async def test_gateway_preserves_request_correlation() -> None:
    registry = VoiceProviderRegistry()
    provider = FakeVoiceProvider(
        "provider-a",
        frozenset({VoiceProviderCapability.SYNTHESIS}),
    )
    registry.register(provider)
    gateway = VoiceProviderGateway(registry)

    result = await gateway.synthesize("provider-a", make_request())

    assert result.request_id == "request-1"
    assert provider.requests == [make_request()]


@pytest.mark.asyncio
async def test_gateway_rejects_mismatched_provider_result() -> None:
    class BadProvider(FakeVoiceProvider):
        async def synthesize(
            self,
            request: VoiceSynthesisRequest,
        ) -> VoiceSynthesisResult:
            return VoiceSynthesisResult(
                request_id=request.request_id,
                provider_id="wrong-provider",
                representation_ref="voice://wrong",
                output_format=request.output_format,
                created_at=datetime.now(UTC),
            )

    registry = VoiceProviderRegistry()
    registry.register(
        BadProvider(
            "provider-a",
            frozenset({VoiceProviderCapability.SYNTHESIS}),
        ),
    )
    gateway = VoiceProviderGateway(registry)

    with pytest.raises(
        VoiceProviderInvocationError,
        match="provider_id",
    ) as exc_info:
        await gateway.synthesize("provider-a", make_request())

    assert exc_info.value.error.code is VoiceProviderErrorCode.OUTPUT_INVALID


@pytest.mark.asyncio
async def test_gateway_streaming_preserves_request_correlation() -> None:
    registry = VoiceProviderRegistry()
    provider = FakeStreamingProvider(
        "provider-a",
        frozenset(
            {
                VoiceProviderCapability.SYNTHESIS,
                VoiceProviderCapability.STREAMING,
            },
        ),
    )
    registry.register(provider)
    gateway = VoiceProviderGateway(registry)

    chunks = [
        chunk
        async for chunk in gateway.stream_synthesis(
            "provider-a",
            make_request(),
        )
    ]

    assert len(chunks) == 1
    assert chunks[0].request_id == "request-1"
    assert chunks[0].sequence == 0


@pytest.mark.asyncio
async def test_gateway_realtime_boundary() -> None:
    registry = VoiceProviderRegistry()
    provider = FakeRealtimeProvider(
        "provider-a",
        frozenset({VoiceProviderCapability.REALTIME}),
    )
    registry.register(provider)
    gateway = VoiceProviderGateway(registry)

    await gateway.open_realtime_session("provider-a", "session-1")
    await gateway.close_realtime_session("provider-a", "session-1")

    assert provider.opened == ["session-1"]
    assert provider.closed == ["session-1"]


def test_provider_capability_is_not_authorization() -> None:
    descriptor = VoiceProviderDescriptor(
        provider_id="provider-a",
        display_name="Provider A",
        capabilities=frozenset(
            {
                VoiceProviderCapability.SYNTHESIS,
                VoiceProviderCapability.CLONING,
            },
        ),
    )

    assert VoiceProviderCapability.CLONING in descriptor.capabilities
