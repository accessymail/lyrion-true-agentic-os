"""Unit tests for streaming voice interaction and 19.4.7 barge-in."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest

from lyrion.cognition.contracts import (
    CognitiveRequestStatus,
    CognitiveResult,
    ReasonRequest,
)
from lyrion.voice.providers import (
    VoiceAudioChunk,
    VoiceOutputFormat,
    VoiceProviderCapability,
    VoiceProviderDescriptor,
    VoiceProviderGateway,
    VoiceProviderRegistry,
    VoiceSynthesisRequest,
    VoiceSynthesisResult,
)
from lyrion.voice.streaming.contracts import (
    VoiceInputChunk,
    VoiceInterruptionReason,
    VoiceInterruptionRequest,
    VoiceInterruptionStatus,
    VoiceStreamErrorCode,
    VoiceStreamState,
)
from lyrion.voice.streaming.lifecycle import VoiceStreamLifecycle
from lyrion.voice.streaming.service import (
    VoiceStreamExecutionError,
    VoiceStreamingService,
)


class FakeStreamingProvider:
    """Deterministic streaming provider fake."""

    def __init__(self) -> None:
        self._descriptor = VoiceProviderDescriptor(
            provider_id="provider-a",
            display_name="Provider A",
            capabilities=frozenset(
                {
                    VoiceProviderCapability.SYNTHESIS,
                    VoiceProviderCapability.STREAMING,
                }
            ),
            models=("model-1",),
        )

    @property
    def descriptor(self) -> VoiceProviderDescriptor:
        return self._descriptor

    async def synthesize(
        self,
        request: VoiceSynthesisRequest,
    ) -> VoiceSynthesisResult:
        raise AssertionError("non-streaming synthesis is not used")

    async def stream_synthesis(
        self,
        request: VoiceSynthesisRequest,
    ) -> AsyncIterator[VoiceAudioChunk]:
        yield VoiceAudioChunk(
            request_id=request.request_id,
            sequence=0,
            audio=b"audio",
            output_format=request.output_format,
        )


class InvalidSequenceProvider(FakeStreamingProvider):
    """Provider fake emitting an invalid output sequence."""

    async def stream_synthesis(
        self,
        request: VoiceSynthesisRequest,
    ) -> AsyncIterator[VoiceAudioChunk]:
        yield VoiceAudioChunk(
            request_id=request.request_id,
            sequence=1,
            audio=b"audio",
            output_format=request.output_format,
        )


class FakeCognitiveRuntime:
    """Deterministic cognitive runtime fake."""

    async def reason(
        self,
        request: ReasonRequest,
    ) -> CognitiveResult:
        return CognitiveResult(
            request_id=request.request_id,
            status=CognitiveRequestStatus.COMPLETED,
            answer="Hello from Lyri",
            created_at=request.created_at,
        )


def make_gateway(
    provider: FakeStreamingProvider | None = None,
) -> VoiceProviderGateway:
    registry = VoiceProviderRegistry()
    registry.register(provider or FakeStreamingProvider())
    return VoiceProviderGateway(registry)


def make_request(
    request_id: str = "request-1",
) -> VoiceSynthesisRequest:
    return VoiceSynthesisRequest(
        request_id=request_id,
        text="Hello Lyri",
        voice_reference="voice-profile://lyri",
        output_format=VoiceOutputFormat.WAV,
    )


@pytest.mark.asyncio
async def test_start_creates_streaming_session() -> None:
    service = VoiceStreamingService(make_gateway())

    session = await service.start(
        session_id="session-1",
        correlation_id="corr-1",
    )

    assert session.session_id == "session-1"
    assert session.correlation_id == "corr-1"
    assert session.state is VoiceStreamState.STREAMING


@pytest.mark.asyncio
async def test_duplicate_session_is_rejected() -> None:
    service = VoiceStreamingService(make_gateway())

    await service.start(session_id="session-1")

    with pytest.raises(ValueError, match="already exists"):
        await service.start(session_id="session-1")


@pytest.mark.asyncio
async def test_input_sequence_must_be_contiguous() -> None:
    service = VoiceStreamingService(make_gateway())
    await service.start(session_id="session-1")

    await service.accept_input(
        VoiceInputChunk(
            session_id="session-1",
            sequence=0,
            audio=b"audio",
            captured_at=datetime.now(UTC),
        )
    )

    with pytest.raises(VoiceStreamExecutionError) as exc_info:
        await service.accept_input(
            VoiceInputChunk(
                session_id="session-1",
                sequence=2,
                audio=b"audio",
                captured_at=datetime.now(UTC),
            )
        )

    assert exc_info.value.error.code is VoiceStreamErrorCode.INVALID_INPUT


@pytest.mark.asyncio
async def test_input_advances_turn_state() -> None:
    service = VoiceStreamingService(make_gateway())
    await service.start(session_id="session-1")

    session = await service.accept_input(
        VoiceInputChunk(
            session_id="session-1",
            sequence=0,
            audio=b"audio",
            captured_at=datetime.now(UTC),
        )
    )

    assert session.state is VoiceStreamState.TURN_ACTIVE
    assert session.next_input_sequence == 1


@pytest.mark.asyncio
async def test_input_chunk_size_is_bounded() -> None:
    service = VoiceStreamingService(
        make_gateway(),
        max_input_chunk_bytes=4,
    )
    await service.start(session_id="session-1")

    with pytest.raises(
        VoiceStreamExecutionError,
        match="exceeds configured size limit",
    ):
        await service.accept_input(
            VoiceInputChunk(
                session_id="session-1",
                sequence=0,
                audio=b"12345",
                captured_at=datetime.now(UTC),
            )
        )


@pytest.mark.asyncio
async def test_stream_synthesis_exposes_provider_neutral_chunks() -> None:
    service = VoiceStreamingService(make_gateway())
    await service.start(session_id="session-1")

    chunks = [
        chunk
        async for chunk in service.stream_synthesis(
            session_id="session-1",
            provider_id="provider-a",
            request=make_request(),
        )
    ]

    assert len(chunks) == 1
    assert chunks[0].session_id == "session-1"
    assert chunks[0].request_id == "request-1"
    assert chunks[0].sequence == 0
    assert chunks[0].audio == b"audio"

    session = await service.get("session-1")
    assert session.state is VoiceStreamState.STREAMING


@pytest.mark.asyncio
async def test_invalid_provider_output_sequence_fails_stream() -> None:
    service = VoiceStreamingService(make_gateway(InvalidSequenceProvider()))
    await service.start(session_id="session-1")

    with pytest.raises(
        VoiceStreamExecutionError,
        match="provider sequence",
    ):
        _ = [
            chunk
            async for chunk in service.stream_synthesis(
                session_id="session-1",
                provider_id="provider-a",
                request=make_request(),
            )
        ]

    session = await service.get("session-1")
    assert session.state is VoiceStreamState.FAILED


@pytest.mark.asyncio
async def test_cancel_transitions_through_cancel_requested() -> None:
    assert VoiceStreamLifecycle.is_allowed(
        VoiceStreamState.STREAMING,
        VoiceStreamState.CANCEL_REQUESTED,
    )
    assert VoiceStreamLifecycle.is_allowed(
        VoiceStreamState.CANCEL_REQUESTED,
        VoiceStreamState.CANCELLED,
    )

    service = VoiceStreamingService(make_gateway())
    await service.start(session_id="session-1")

    session = await service.cancel("session-1")

    assert session.state is VoiceStreamState.CANCELLED


@pytest.mark.asyncio
async def test_cancelled_session_rejects_input() -> None:
    service = VoiceStreamingService(make_gateway())
    await service.start(session_id="session-1")
    await service.cancel("session-1")

    with pytest.raises(
        VoiceStreamExecutionError,
        match="is not accepted",
    ):
        await service.accept_input(
            VoiceInputChunk(
                session_id="session-1",
                sequence=0,
                audio=b"audio",
                captured_at=datetime.now(UTC),
            )
        )


@pytest.mark.asyncio
async def test_cognitive_turn_streams_synthesized_output() -> None:
    service = VoiceStreamingService(
        make_gateway(),
        cognitive_runtime=FakeCognitiveRuntime(),
    )
    await service.start(session_id="session-1")

    request = ReasonRequest(
        request_id="request-1",
        objective="Say hello",
        created_at=datetime.now(UTC),
    )

    chunks = [
        chunk
        async for chunk in service.process_text_turn(
            session_id="session-1",
            provider_id="provider-a",
            request=request,
            synthesis_factory=lambda result: make_request(result.request_id),
        )
    ]

    assert len(chunks) == 1
    assert chunks[0].request_id == "request-1"

    metrics = await service.metrics("session-1")
    assert metrics.output_chunks == 1
    assert metrics.turns_completed == 1


@pytest.mark.asyncio
async def test_metrics_track_first_output_latency() -> None:
    service = VoiceStreamingService(make_gateway())
    await service.start(session_id="session-1")

    _ = [
        chunk
        async for chunk in service.stream_synthesis(
            session_id="session-1",
            provider_id="provider-a",
            request=make_request(),
        )
    ]

    metrics = await service.metrics("session-1")

    assert metrics.output_chunks == 1
    assert metrics.first_output_latency_seconds is not None
    assert metrics.first_output_latency_seconds >= 0.0


def test_stream_contract_is_immutable() -> None:
    from lyrion.voice.streaming.contracts import VoiceStreamSession

    now = datetime.now(UTC)
    session = VoiceStreamSession(
        session_id="session-1",
        correlation_id="corr-1",
        state=VoiceStreamState.STREAMING,
        started_at=now,
        updated_at=now,
    )

    with pytest.raises((AttributeError, ValueError)):
        session.state = VoiceStreamState.FAILED


class FailingStreamingProvider(FakeStreamingProvider):
    """Provider fake that fails with the real provider error contract."""

    async def stream_synthesis(
        self,
        request: VoiceSynthesisRequest,
    ) -> AsyncIterator[VoiceAudioChunk]:
        from lyrion.voice.providers import (
            VoiceProviderError,
            VoiceProviderErrorCode,
            VoiceProviderInvocationError,
        )

        raise VoiceProviderInvocationError(
            VoiceProviderError(
                code=VoiceProviderErrorCode.PROVIDER_FAILURE,
                message="provider exploded",
                provider_id=self.descriptor.provider_id,
                retryable=True,
            )
        )
        yield  # pragma: no cover


class WrongCorrelationProvider(FakeStreamingProvider):
    """Provider fake emitting a mismatched request correlation ID."""

    async def stream_synthesis(
        self,
        request: VoiceSynthesisRequest,
    ) -> AsyncIterator[VoiceAudioChunk]:
        yield VoiceAudioChunk(
            request_id="wrong-request",
            sequence=0,
            audio=b"audio",
            output_format=request.output_format,
        )


class BlockingStreamingProvider(FakeStreamingProvider):
    """Provider fake that blocks until the consumer is cancelled."""

    async def stream_synthesis(
        self,
        request: VoiceSynthesisRequest,
    ) -> AsyncIterator[VoiceAudioChunk]:
        await asyncio.Event().wait()
        if False:
            yield VoiceAudioChunk(
                request_id=request.request_id,
                sequence=0,
                audio=b"",
                output_format=request.output_format,
            )


@pytest.mark.asyncio
async def test_provider_failure_is_normalized_and_session_fails() -> None:
    service = VoiceStreamingService(
        make_gateway(FailingStreamingProvider()),
    )
    await service.start(session_id="session-1")

    with pytest.raises(
        VoiceStreamExecutionError,
        match="provider exploded",
    ) as exc_info:
        _ = [
            chunk
            async for chunk in service.stream_synthesis(
                session_id="session-1",
                provider_id="provider-a",
                request=make_request(),
            )
        ]

    assert exc_info.value.error.code is VoiceStreamErrorCode.PROVIDER_FAILURE
    assert exc_info.value.error.retryable is True

    session = await service.get("session-1")
    assert session.state is VoiceStreamState.FAILED

    metrics = await service.metrics("session-1")
    assert metrics.provider_failures == 1


@pytest.mark.asyncio
async def test_mismatched_request_correlation_fails_stream() -> None:
    service = VoiceStreamingService(
        make_gateway(WrongCorrelationProvider()),
    )
    await service.start(session_id="session-1")

    with pytest.raises(
        VoiceStreamExecutionError,
        match="request_id does not match",
    ) as exc_info:
        _ = [
            chunk
            async for chunk in service.stream_synthesis(
                session_id="session-1",
                provider_id="provider-a",
                request=make_request(),
            )
        ]

    assert exc_info.value.error.code is VoiceStreamErrorCode.OUTPUT_INVALID

    session = await service.get("session-1")
    assert session.state is VoiceStreamState.FAILED


@pytest.mark.asyncio
async def test_external_cancel_interrupts_active_provider_task() -> None:
    service = VoiceStreamingService(make_gateway(BlockingStreamingProvider()))
    await service.start(session_id="session-1")

    stream_task = asyncio.create_task(
        _consume_stream(
            service,
            session_id="session-1",
            provider_id="provider-a",
            request=make_request(),
        ),
    )

    await _wait_for_active_task(service, "session-1")

    session = await service.cancel("session-1")
    assert session.state is VoiceStreamState.CANCELLED

    with pytest.raises(asyncio.CancelledError):
        await stream_task

    assert "session-1" not in service._active_tasks


@pytest.mark.asyncio
async def test_stream_timeout_fails_session_and_cleans_task() -> None:
    service = VoiceStreamingService(
        make_gateway(BlockingStreamingProvider()),
        stream_timeout_seconds=0.01,
    )
    await service.start(session_id="session-1")

    with pytest.raises(
        VoiceStreamExecutionError,
        match="timed out",
    ) as exc_info:
        _ = [
            chunk
            async for chunk in service.stream_synthesis(
                session_id="session-1",
                provider_id="provider-a",
                request=make_request(),
            )
        ]

    assert exc_info.value.error.code is VoiceStreamErrorCode.TIMEOUT

    session = await service.get("session-1")
    assert session.state is VoiceStreamState.FAILED

    assert "session-1" not in service._active_tasks


class StaleOutputStreamingProvider(FakeStreamingProvider):
    """Provider fake that emits output after interruption is requested."""

    def __init__(self) -> None:
        super().__init__()
        self.release = asyncio.Event()

    async def stream_synthesis(
        self,
        request: VoiceSynthesisRequest,
    ) -> AsyncIterator[VoiceAudioChunk]:
        await self.release.wait()

        yield VoiceAudioChunk(
            request_id=request.request_id,
            sequence=0,
            audio=b"stale-audio",
            output_format=request.output_format,
        )


@pytest.mark.asyncio
async def test_barge_in_interrupts_active_turn_and_preserves_session() -> None:
    provider = BlockingStreamingProvider()
    service = VoiceStreamingService(make_gateway(provider))
    await service.start(session_id="session-1")

    stream_task = asyncio.create_task(
        _consume_stream(
            service,
            session_id="session-1",
            provider_id="provider-a",
            request=make_request(),
        )
    )

    await _wait_for_active_task(service, "session-1")

    result = await service.interrupt(
        VoiceInterruptionRequest(
            session_id="session-1",
            request_id="request-1",
            reason=VoiceInterruptionReason.BARGE_IN,
            requested_at=datetime.now(UTC),
        )
    )

    assert result.status is VoiceInterruptionStatus.REQUESTED

    with pytest.raises(VoiceStreamExecutionError) as exc_info:
        await stream_task

    assert exc_info.value.error.code is VoiceStreamErrorCode.INTERRUPTED

    session = await service.get("session-1")
    assert session.state is VoiceStreamState.STREAMING

    metrics = await service.metrics("session-1")
    assert metrics.interruptions == 1
    assert metrics.turns_completed == 0


@pytest.mark.asyncio
async def test_interrupted_turn_can_be_replaced_by_new_turn() -> None:
    provider = BlockingStreamingProvider()
    service = VoiceStreamingService(make_gateway(provider))
    await service.start(session_id="session-1")

    first_task = asyncio.create_task(
        _consume_stream(
            service,
            session_id="session-1",
            provider_id="provider-a",
            request=make_request("request-1"),
        )
    )

    await _wait_for_active_task(service, "session-1")

    await service.interrupt(
        VoiceInterruptionRequest(
            session_id="session-1",
            request_id="request-1",
            reason=VoiceInterruptionReason.BARGE_IN,
            requested_at=datetime.now(UTC),
        )
    )

    with pytest.raises(VoiceStreamExecutionError):
        await first_task

    second_provider = FakeStreamingProvider()
    service._gateway = make_gateway(second_provider)

    chunks = [
        chunk
        async for chunk in service.stream_synthesis(
            session_id="session-1",
            provider_id="provider-a",
            request=make_request("request-2"),
        )
    ]

    assert len(chunks) == 1
    assert chunks[0].request_id == "request-2"

    session = await service.get("session-1")
    assert session.state is VoiceStreamState.STREAMING


@pytest.mark.asyncio
async def test_interruption_rejects_wrong_active_request() -> None:
    service = VoiceStreamingService(
        make_gateway(BlockingStreamingProvider())
    )
    await service.start(session_id="session-1")

    task = asyncio.create_task(
        _consume_stream(
            service,
            session_id="session-1",
            provider_id="provider-a",
            request=make_request("request-1"),
        )
    )

    await _wait_for_active_task(service, "session-1")

    with pytest.raises(
        VoiceStreamExecutionError,
        match="active voice turn",
    ):
        await service.interrupt(
            VoiceInterruptionRequest(
                session_id="session-1",
                request_id="wrong-request",
                reason=VoiceInterruptionReason.BARGE_IN,
                requested_at=datetime.now(UTC),
            )
        )

    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_duplicate_interruption_is_idempotent() -> None:
    provider = BlockingStreamingProvider()
    service = VoiceStreamingService(make_gateway(provider))
    await service.start(session_id="session-1")

    task = asyncio.create_task(
        _consume_stream(
            service,
            session_id="session-1",
            provider_id="provider-a",
            request=make_request("request-1"),
        )
    )

    await _wait_for_active_task(service, "session-1")

    request = VoiceInterruptionRequest(
        session_id="session-1",
        request_id="request-1",
        reason=VoiceInterruptionReason.BARGE_IN,
        requested_at=datetime.now(UTC),
    )

    first = await service.interrupt(request)

    with pytest.raises(VoiceStreamExecutionError):
        await task

    second = await service.interrupt(request)

    assert first.status is VoiceInterruptionStatus.REQUESTED
    assert second.status is VoiceInterruptionStatus.ALREADY_INTERRUPTED

    metrics = await service.metrics("session-1")
    assert metrics.interruptions == 1


@pytest.mark.asyncio
async def test_interruption_does_not_convert_to_terminal_cancelled_state() -> None:
    provider = BlockingStreamingProvider()
    service = VoiceStreamingService(make_gateway(provider))
    await service.start(session_id="session-1")

    task = asyncio.create_task(
        _consume_stream(
            service,
            session_id="session-1",
            provider_id="provider-a",
            request=make_request("request-1"),
        )
    )

    await _wait_for_active_task(service, "session-1")

    await service.interrupt(
        VoiceInterruptionRequest(
            session_id="session-1",
            request_id="request-1",
            requested_at=datetime.now(UTC),
        )
    )

    with pytest.raises(VoiceStreamExecutionError):
        await task

    assert (await service.get("session-1")).state is VoiceStreamState.STREAMING

    repeated = await service.interrupt(
        VoiceInterruptionRequest(
            session_id="session-1",
            request_id="request-1",
            requested_at=datetime.now(UTC),
        )
    )

    assert repeated.status is VoiceInterruptionStatus.ALREADY_INTERRUPTED
    assert (await service.get("session-1")).state is VoiceStreamState.STREAMING


@pytest.mark.asyncio
async def test_late_provider_output_is_rejected_after_barge_in() -> None:
    provider = StaleOutputStreamingProvider()
    service = VoiceStreamingService(make_gateway(provider))
    await service.start(session_id="session-1")

    task = asyncio.create_task(
        _consume_stream(
            service,
            session_id="session-1",
            provider_id="provider-a",
            request=make_request("request-1"),
        )
    )

    await _wait_for_active_task(service, "session-1")

    result = await service.interrupt(
        VoiceInterruptionRequest(
            session_id="session-1",
            request_id="request-1",
            requested_at=datetime.now(UTC),
        )
    )

    assert result.status is VoiceInterruptionStatus.REQUESTED

    provider.release.set()

    with pytest.raises(VoiceStreamExecutionError) as exc_info:
        await task

    assert exc_info.value.error.code is VoiceStreamErrorCode.INTERRUPTED
    assert (await service.metrics("session-1")).output_chunks == 0
    assert (await service.get("session-1")).state is VoiceStreamState.STREAMING


@pytest.mark.asyncio
async def test_explicit_cancel_remains_terminal_after_19_4_7_changes() -> None:
    service = VoiceStreamingService(make_gateway())
    await service.start(session_id="session-1")

    session = await service.cancel("session-1")

    assert session.state is VoiceStreamState.CANCELLED


@pytest.mark.asyncio
async def test_unknown_session_is_rejected() -> None:
    service = VoiceStreamingService(make_gateway())

    with pytest.raises(
        ValueError,
        match="unknown voice streaming session",
    ):
        await service.get("missing")

    with pytest.raises(
        ValueError,
        match="unknown voice streaming session",
    ):
        await service.cancel("missing")


async def _consume_stream(
    service: VoiceStreamingService,
    *,
    session_id: str,
    provider_id: str,
    request: VoiceSynthesisRequest,
) -> list[object]:
    return [
        chunk
        async for chunk in service.stream_synthesis(
            session_id=session_id,
            provider_id=provider_id,
            request=request,
        )
    ]


async def _wait_for_active_task(
    service: VoiceStreamingService,
    session_id: str,
) -> None:
    for _ in range(100):
        if session_id in service._active_tasks:
            return
        await asyncio.sleep(0)

    raise AssertionError("streaming task was not registered")


@pytest.mark.asyncio
async def test_concurrent_interrupt_requests_only_one_is_accepted() -> None:
    provider = BlockingStreamingProvider()
    service = VoiceStreamingService(make_gateway(provider))
    await service.start(session_id="session-1")

    task = asyncio.create_task(
        _consume_stream(
            service,
            session_id="session-1",
            provider_id="provider-a",
            request=make_request("request-1"),
        )
    )

    await _wait_for_active_task(service, "session-1")

    request = VoiceInterruptionRequest(
        session_id="session-1",
        request_id="request-1",
        reason=VoiceInterruptionReason.BARGE_IN,
        requested_at=datetime.now(UTC),
    )

    first, second = await asyncio.gather(
        service.interrupt(request),
        service.interrupt(request),
    )

    statuses = {first.status, second.status}
    assert statuses == {
        VoiceInterruptionStatus.REQUESTED,
        VoiceInterruptionStatus.ALREADY_INTERRUPTED,
    }

    with pytest.raises(VoiceStreamExecutionError) as exc_info:
        await task

    assert exc_info.value.error.code is VoiceStreamErrorCode.INTERRUPTED
    assert (await service.metrics("session-1")).interruptions == 1
    assert (await service.get("session-1")).state is VoiceStreamState.STREAMING


@pytest.mark.asyncio
async def test_interrupted_old_turn_cannot_complete_after_new_turn_starts() -> None:
    provider = StaleOutputStreamingProvider()
    service = VoiceStreamingService(make_gateway(provider))
    await service.start(session_id="session-1")

    first_task = asyncio.create_task(
        _consume_stream(
            service,
            session_id="session-1",
            provider_id="provider-a",
            request=make_request("request-1"),
        )
    )

    await _wait_for_active_task(service, "session-1")

    await service.interrupt(
        VoiceInterruptionRequest(
            session_id="session-1",
            request_id="request-1",
            reason=VoiceInterruptionReason.BARGE_IN,
            requested_at=datetime.now(UTC),
        )
    )

    with pytest.raises(VoiceStreamExecutionError) as exc_info:
        await first_task

    assert exc_info.value.error.code is VoiceStreamErrorCode.INTERRUPTED

    service._gateway = make_gateway(FakeStreamingProvider())

    chunks = [
        chunk
        async for chunk in service.stream_synthesis(
            session_id="session-1",
            provider_id="provider-a",
            request=make_request("request-2"),
        )
    ]

    assert len(chunks) == 1
    assert chunks[0].request_id == "request-2"

    provider.release.set()

    assert (await service.metrics("session-1")).turns_completed == 0
    assert (await service.get("session-1")).state is VoiceStreamState.STREAMING


@pytest.mark.asyncio
async def test_interrupt_racing_with_provider_output_blocks_stale_chunk() -> None:
    provider = StaleOutputStreamingProvider()
    service = VoiceStreamingService(make_gateway(provider))
    await service.start(session_id="session-1")

    task = asyncio.create_task(
        _consume_stream(
            service,
            session_id="session-1",
            provider_id="provider-a",
            request=make_request("request-1"),
        )
    )

    await _wait_for_active_task(service, "session-1")

    interrupt_task = asyncio.create_task(
        service.interrupt(
            VoiceInterruptionRequest(
                session_id="session-1",
                request_id="request-1",
                reason=VoiceInterruptionReason.BARGE_IN,
                requested_at=datetime.now(UTC),
            )
        )
    )

    result = await interrupt_task
    assert result.status is VoiceInterruptionStatus.REQUESTED

    provider.release.set()

    with pytest.raises(VoiceStreamExecutionError) as exc_info:
        await task

    assert exc_info.value.error.code is VoiceStreamErrorCode.INTERRUPTED
    assert (await service.metrics("session-1")).output_chunks == 0
    assert (await service.get("session-1")).state is VoiceStreamState.STREAMING
