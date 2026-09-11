"""Application service for provider-neutral streaming voice interaction."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from time import monotonic
from uuid import uuid4

from lyrion.cognition.contracts import CognitiveResult, ReasonRequest
from lyrion.cognition.runtime import CognitiveRuntime
from lyrion.voice.providers import (
    VoiceProviderErrorCode,
    VoiceProviderGateway,
    VoiceProviderInvocationError,
    VoiceSynthesisRequest,
)
from lyrion.voice.streaming.contracts import (
    VoiceInputChunk,
    VoiceInterruptionRequest,
    VoiceInterruptionResult,
    VoiceInterruptionStatus,
    VoiceOutputChunk,
    VoiceStreamError,
    VoiceStreamErrorCode,
    VoiceStreamMetrics,
    VoiceStreamSession,
    VoiceStreamState,
    utc_now,
)
from lyrion.voice.streaming.lifecycle import VoiceStreamLifecycle


class VoiceStreamExecutionError(RuntimeError):
    """Raised when a streaming operation cannot continue safely."""

    def __init__(self, error: VoiceStreamError) -> None:
        self.error = error
        super().__init__(error.message)


@dataclass(slots=True)
class _Session:
    """Mutable runtime state protected by the service lock."""

    snapshot: VoiceStreamSession
    cancel_event: asyncio.Event
    started_monotonic: float
    input_chunks: int = 0
    output_chunks: int = 0
    turns_completed: int = 0
    provider_failures: int = 0
    cancellations: int = 0
    first_output_monotonic: float | None = None
    last_input_sequence: int = -1
    turn_generation: int = 0
    active_request_id: str | None = None
    interruption_requested: bool = False
    last_interrupted_request_id: str | None = None
    interruptions: int = 0


class VoiceStreamingService:
    """Own one bounded streaming interaction lifecycle."""

    def __init__(
        self,
        gateway: VoiceProviderGateway,
        *,
        cognitive_runtime: CognitiveRuntime | None = None,
        stream_timeout_seconds: float = 30.0,
        max_input_chunk_bytes: int = 1024 * 1024,
        max_turn_text_length: int = 8000,
    ) -> None:
        if stream_timeout_seconds <= 0:
            raise ValueError("stream_timeout_seconds must be > 0")
        if max_input_chunk_bytes < 1:
            raise ValueError("max_input_chunk_bytes must be >= 1")
        if max_turn_text_length < 1:
            raise ValueError("max_turn_text_length must be >= 1")

        self._gateway = gateway
        self._cognitive_runtime = cognitive_runtime
        self._stream_timeout_seconds = stream_timeout_seconds
        self._max_input_chunk_bytes = max_input_chunk_bytes
        self._max_turn_text_length = max_turn_text_length

        self._lock = asyncio.Lock()
        self._sessions: dict[str, _Session] = {}
        self._active_tasks: dict[str, asyncio.Task[object]] = {}

    async def start(
        self,
        *,
        session_id: str | None = None,
        correlation_id: str | None = None,
    ) -> VoiceStreamSession:
        """Create a new streaming session."""
        sid = (session_id or str(uuid4())).strip()
        cid = (correlation_id or sid).strip()

        if not sid:
            raise ValueError("session_id must not be blank")
        if not cid:
            raise ValueError("correlation_id must not be blank")

        async with self._lock:
            if sid in self._sessions:
                raise ValueError(f"voice session already exists: {sid}")

            now = utc_now()
            session = VoiceStreamSession(
                session_id=sid,
                correlation_id=cid,
                state=VoiceStreamState.STARTING,
                started_at=now,
                updated_at=now,
            )
            runtime = _Session(
                snapshot=session,
                cancel_event=asyncio.Event(),
                started_monotonic=monotonic(),
            )
            self._sessions[sid] = runtime
            self._transition_locked(runtime, VoiceStreamState.STREAMING)
            return runtime.snapshot

    async def get(self, session_id: str) -> VoiceStreamSession:
        """Return the immutable current session snapshot."""
        sid = self._require_id(session_id, "session_id")
        async with self._lock:
            return self._get_locked(sid).snapshot

    async def accept_input(
        self,
        chunk: VoiceInputChunk,
    ) -> VoiceStreamSession:
        """Accept one bounded, strictly ordered input chunk."""
        if len(chunk.audio) > self._max_input_chunk_bytes:
            raise self._error(
                chunk.session_id,
                VoiceStreamErrorCode.BUFFER_LIMIT,
                "input audio chunk exceeds configured size limit",
            )

        async with self._lock:
            runtime = self._get_locked(chunk.session_id)

            if runtime.snapshot.state not in {
                VoiceStreamState.STREAMING,
                VoiceStreamState.TURN_ACTIVE,
            }:
                raise self._error(
                    chunk.session_id,
                    VoiceStreamErrorCode.INVALID_STATE,
                    f"input is not accepted in state {runtime.snapshot.state}",
                )

            expected = runtime.last_input_sequence + 1
            if chunk.sequence != expected:
                raise self._error(
                    chunk.session_id,
                    VoiceStreamErrorCode.INVALID_INPUT,
                    f"input sequence must be {expected}, received {chunk.sequence}",
                )

            runtime.last_input_sequence = chunk.sequence
            runtime.input_chunks += 1

            if runtime.snapshot.state is VoiceStreamState.STREAMING:
                self._transition_locked(
                    runtime,
                    VoiceStreamState.TURN_ACTIVE,
                )

            runtime.snapshot = runtime.snapshot.model_copy(
                update={
                    "next_input_sequence": chunk.sequence + 1,
                    "updated_at": utc_now(),
                }
            )
            return runtime.snapshot

    async def stream_synthesis(
        self,
        *,
        session_id: str,
        provider_id: str,
        request: VoiceSynthesisRequest,
        _generation: int | None = None,
    ) -> AsyncIterator[VoiceOutputChunk]:
        """Stream provider output through the existing gateway.

        Provider chunk sequence numbers are request-local.
        """
        sid = self._require_id(session_id, "session_id")
        pid = self._require_id(provider_id, "provider_id")
        task = asyncio.current_task()

        if task is None:
            raise RuntimeError("streaming requires an active asyncio task")

        generation = await self._begin_output(
            sid,
            request.request_id,
            generation=_generation,
        )
        await self._register_task(sid, task)

        try:
            expected_sequence = 0

            await self._raise_if_interrupted(
                sid,
                request.request_id,
                generation,
            )

            async with asyncio.timeout(self._stream_timeout_seconds):
                async for chunk in self._gateway.stream_synthesis(
                    pid,
                    request,
                ):
                    await self._raise_if_interrupted(
                        sid,
                        request.request_id,
                        generation,
                    )
                    self._raise_if_cancelled(sid)

                    if chunk.request_id != request.request_id:
                        error = self._error(
                            sid,
                            VoiceStreamErrorCode.OUTPUT_INVALID,
                            "provider chunk request_id does not match request",
                        )
                        await self._fail(sid, error.error)
                        raise error

                    if chunk.sequence != expected_sequence:
                        error = self._error(
                            sid,
                            VoiceStreamErrorCode.OUTPUT_INVALID,
                            (
                                "provider sequence must be "
                                f"{expected_sequence}, received {chunk.sequence}"
                            ),
                        )
                        await self._fail(sid, error.error)
                        raise error

                    expected_sequence += 1
                    await self._record_output(sid)

                    yield VoiceOutputChunk(
                        session_id=sid,
                        request_id=chunk.request_id,
                        sequence=chunk.sequence,
                        audio=chunk.audio,
                        output_format=chunk.output_format,
                    )

            await self._return_to_streaming(
                sid,
                generation,
            )

        except asyncio.CancelledError:
            if await self._consume_interruption(sid, generation):
                error = self._error(
                    sid,
                    VoiceStreamErrorCode.INTERRUPTED,
                    "voice turn was interrupted",
                )
                raise error from None

            await self._cancel_session(sid)
            raise
        except TimeoutError as exc:
            error = self._error(
                sid,
                VoiceStreamErrorCode.TIMEOUT,
                "voice output streaming timed out",
                retryable=True,
            )
            await self._fail(sid, error.error)
            raise error from exc
        except VoiceProviderInvocationError as exc:
            error = self._normalize_provider_error(sid, exc)
            await self._fail(sid, error.error)
            raise error from exc
        finally:
            await self._clear_task(sid, task)

    async def process_text_turn(
        self,
        *,
        session_id: str,
        provider_id: str,
        request: ReasonRequest,
        synthesis_factory: Callable[
            [CognitiveResult],
            VoiceSynthesisRequest,
        ],
    ) -> AsyncIterator[VoiceOutputChunk]:
        """Run one bounded cognitive turn and stream its answer."""
        sid = self._require_id(session_id, "session_id")
        pid = self._require_id(provider_id, "provider_id")

        if len(request.objective) > self._max_turn_text_length:
            raise self._error(
                sid,
                VoiceStreamErrorCode.INVALID_INPUT,
                "reasoning objective exceeds configured length",
            )

        runtime = self._cognitive_runtime
        if runtime is None:
            raise ValueError("cognitive_runtime is required for process_text_turn")

        task = asyncio.current_task()
        if task is None:
            raise RuntimeError("cognitive turn requires an active asyncio task")

        generation = await self._begin_turn(
            sid,
            request.request_id,
        )
        await self._begin_processing(sid)
        await self._register_task(sid, task)

        try:
            async with asyncio.timeout(self._stream_timeout_seconds):
                await self._raise_if_interrupted(
                    sid,
                    request.request_id,
                    generation,
                )
                result = await runtime.reason(request)

                await self._raise_if_interrupted(
                    sid,
                    request.request_id,
                    generation,
                )

                if result.status.value != "COMPLETED" or not result.answer:
                    error = self._error(
                        sid,
                        VoiceStreamErrorCode.PROVIDER_FAILURE,
                        "cognitive runtime did not return a completed answer",
                    )
                    await self._fail(sid, error.error)
                    raise error

                synthesis_request = synthesis_factory(result)

                async for chunk in self.stream_synthesis(
                    session_id=sid,
                    provider_id=pid,
                    request=synthesis_request,
                    _generation=generation,
                ):
                    yield chunk

                await self._complete_turn(sid)

        except asyncio.CancelledError:
            if await self._consume_interruption(sid, generation):
                error = self._error(
                    sid,
                    VoiceStreamErrorCode.INTERRUPTED,
                    "voice turn was interrupted",
                )
                raise error from None

            await self._cancel_session(sid)
            raise
        except TimeoutError as exc:
            error = self._error(
                sid,
                VoiceStreamErrorCode.TIMEOUT,
                "voice cognitive turn timed out",
                retryable=True,
            )
            await self._fail(sid, error.error)
            raise error from exc
        finally:
            await self._clear_task(sid, task)

    async def cancel(self, session_id: str) -> VoiceStreamSession:
        """Cancel the active operation associated with a session."""
        sid = self._require_id(session_id, "session_id")
        return await self._cancel_session(sid)

    async def interrupt(
        self,
        request: VoiceInterruptionRequest,
    ) -> VoiceInterruptionResult:
        """Interrupt the active voice turn without cancelling the session."""
        sid = self._require_id(request.session_id, "session_id")
        rid = self._require_id(request.request_id, "request_id")

        async with self._lock:
            runtime = self._get_locked(sid)

            if runtime.snapshot.state in {
                VoiceStreamState.CANCELLED,
                VoiceStreamState.FAILED,
            }:
                raise self._error(
                    sid,
                    VoiceStreamErrorCode.INVALID_STATE,
                    f"voice turn interruption is not allowed in state "
                    f"{runtime.snapshot.state}",
                )

            if runtime.active_request_id != rid:
                if runtime.last_interrupted_request_id == rid:
                    return VoiceInterruptionResult(
                        session_id=sid,
                        request_id=rid,
                        status=VoiceInterruptionStatus.ALREADY_INTERRUPTED,
                        occurred_at=utc_now(),
                    )

                raise self._error(
                    sid,
                    VoiceStreamErrorCode.INVALID_INPUT,
                    "interruption request_id does not match active voice turn",
                )

            if runtime.interruption_requested:
                return VoiceInterruptionResult(
                    session_id=sid,
                    request_id=rid,
                    status=VoiceInterruptionStatus.ALREADY_INTERRUPTED,
                    occurred_at=utc_now(),
                )

            runtime.interruption_requested = True
            runtime.last_interrupted_request_id = rid
            runtime.interruptions += 1

            if runtime.snapshot.state in {
                VoiceStreamState.TURN_ACTIVE,
                VoiceStreamState.PROCESSING,
                VoiceStreamState.OUTPUT_STREAMING,
            }:
                self._transition_locked(
                    runtime,
                    VoiceStreamState.STREAMING,
                )

            task = self._active_tasks.get(sid)
            if task is not None and task is not asyncio.current_task():
                task.cancel()

            return VoiceInterruptionResult(
                session_id=sid,
                request_id=rid,
                status=VoiceInterruptionStatus.REQUESTED,
                occurred_at=utc_now(),
            )

    async def metrics(self, session_id: str) -> VoiceStreamMetrics:
        """Return immutable streaming metrics."""
        sid = self._require_id(session_id, "session_id")

        async with self._lock:
            runtime = self._get_locked(sid)
            latency = None
            if runtime.first_output_monotonic is not None:
                latency = max(
                    0.0,
                    runtime.first_output_monotonic - runtime.started_monotonic,
                )

            return VoiceStreamMetrics(
                session_id=sid,
                input_chunks=runtime.input_chunks,
                output_chunks=runtime.output_chunks,
                turns_completed=runtime.turns_completed,
                provider_failures=runtime.provider_failures,
                cancellations=runtime.cancellations,
                interruptions=runtime.interruptions,
                duration_seconds=max(
                    0.0,
                    monotonic() - runtime.started_monotonic,
                ),
                first_output_latency_seconds=latency,
            )

    async def _begin_turn(
        self,
        sid: str,
        request_id: str,
    ) -> int:
        async with self._lock:
            runtime = self._get_locked(sid)

            if runtime.snapshot.state not in {
                VoiceStreamState.STREAMING,
                VoiceStreamState.TURN_ACTIVE,
            }:
                raise self._error(
                    sid,
                    VoiceStreamErrorCode.INVALID_STATE,
                    f"voice turn is not allowed in state {runtime.snapshot.state}",
                )

            if runtime.active_request_id is not None:
                raise self._error(
                    sid,
                    VoiceStreamErrorCode.INVALID_STATE,
                    "voice session already has an active turn",
                )

            runtime.turn_generation += 1
            runtime.active_request_id = request_id
            runtime.interruption_requested = False

            if runtime.snapshot.state is VoiceStreamState.STREAMING:
                self._transition_locked(
                    runtime,
                    VoiceStreamState.TURN_ACTIVE,
                )

            return runtime.turn_generation

    async def _begin_processing(self, sid: str) -> None:
        async with self._lock:
            runtime = self._get_locked(sid)
            if runtime.snapshot.state is VoiceStreamState.STREAMING:
                self._transition_locked(
                    runtime,
                    VoiceStreamState.TURN_ACTIVE,
                )
            self._transition_locked(runtime, VoiceStreamState.PROCESSING)

    async def _begin_output(
        self,
        sid: str,
        request_id: str,
        *,
        generation: int | None = None,
    ) -> int:
        async with self._lock:
            runtime = self._get_locked(sid)

            if generation is not None:
                if runtime.turn_generation != generation:
                    raise self._error(
                        sid,
                        VoiceStreamErrorCode.INTERRUPTED,
                        "voice turn generation is no longer active",
                    )

                if runtime.active_request_id != request_id:
                    raise self._error(
                        sid,
                        VoiceStreamErrorCode.INVALID_STATE,
                        "voice session active turn does not match request",
                    )

                resolved_generation = generation

            elif runtime.active_request_id is None:
                runtime.turn_generation += 1
                runtime.active_request_id = request_id
                runtime.interruption_requested = False
                resolved_generation = runtime.turn_generation

            elif runtime.active_request_id == request_id:
                resolved_generation = runtime.turn_generation

            else:
                raise self._error(
                    sid,
                    VoiceStreamErrorCode.INVALID_STATE,
                    "voice session already has a different active turn",
                )

            if runtime.snapshot.state is VoiceStreamState.PROCESSING:
                self._transition_locked(
                    runtime,
                    VoiceStreamState.OUTPUT_STREAMING,
                )
                return resolved_generation

            if runtime.snapshot.state is VoiceStreamState.TURN_ACTIVE:
                self._transition_locked(
                    runtime,
                    VoiceStreamState.PROCESSING,
                )
                self._transition_locked(
                    runtime,
                    VoiceStreamState.OUTPUT_STREAMING,
                )
                return resolved_generation

            if runtime.snapshot.state is VoiceStreamState.STREAMING:
                self._transition_locked(
                    runtime,
                    VoiceStreamState.OUTPUT_STREAMING,
                )
                return resolved_generation

            raise self._error(
                sid,
                VoiceStreamErrorCode.INVALID_STATE,
                f"output streaming is not allowed in state "
                f"{runtime.snapshot.state}",
            )

    async def _return_to_streaming(
        self,
        sid: str,
        generation: int | None = None,
    ) -> None:
        async with self._lock:
            runtime = self._get_locked(sid)

            if (
                generation is not None
                and runtime.turn_generation != generation
            ):
                return

            if runtime.interruption_requested:
                runtime.active_request_id = None
                runtime.interruption_requested = False

            if runtime.snapshot.state is VoiceStreamState.OUTPUT_STREAMING:
                self._transition_locked(
                    runtime,
                    VoiceStreamState.STREAMING,
                )

            if generation is not None and runtime.active_request_id is not None:
                runtime.active_request_id = None

    async def _complete_turn(self, sid: str) -> None:
        async with self._lock:
            runtime = self._get_locked(sid)
            runtime.turns_completed += 1
            runtime.active_request_id = None
            runtime.interruption_requested = False

    async def _record_output(self, sid: str) -> None:
        async with self._lock:
            runtime = self._get_locked(sid)
            runtime.output_chunks += 1
            if runtime.first_output_monotonic is None:
                runtime.first_output_monotonic = monotonic()

    async def _raise_if_interrupted(
        self,
        sid: str,
        request_id: str,
        generation: int,
    ) -> None:
        async with self._lock:
            runtime = self._get_locked(sid)

            if runtime.interruption_requested and (
                runtime.turn_generation == generation
                and runtime.active_request_id == request_id
            ):
                runtime.interruption_requested = False
                runtime.active_request_id = None

                if runtime.snapshot.state in {
                    VoiceStreamState.TURN_ACTIVE,
                    VoiceStreamState.PROCESSING,
                    VoiceStreamState.OUTPUT_STREAMING,
                }:
                    self._transition_locked(
                        runtime,
                        VoiceStreamState.STREAMING,
                    )

                raise self._error(
                    sid,
                    VoiceStreamErrorCode.INTERRUPTED,
                    "voice turn was interrupted",
                )

            if (
                runtime.turn_generation != generation
                or runtime.active_request_id != request_id
            ):
                raise self._error(
                    sid,
                    VoiceStreamErrorCode.INTERRUPTED,
                    "voice turn was interrupted or superseded",
                )

    async def _consume_interruption(
        self,
        sid: str,
        generation: int,
    ) -> bool:
        async with self._lock:
            runtime = self._get_locked(sid)

            if (
                runtime.turn_generation != generation
                or not runtime.interruption_requested
            ):
                return False

            runtime.interruption_requested = False
            runtime.active_request_id = None

            if runtime.snapshot.state in {
                VoiceStreamState.TURN_ACTIVE,
                VoiceStreamState.PROCESSING,
                VoiceStreamState.OUTPUT_STREAMING,
            }:
                self._transition_locked(
                    runtime,
                    VoiceStreamState.STREAMING,
                )

            return True

    async def _cancel_session(self, sid: str) -> VoiceStreamSession:
        async with self._lock:
            runtime = self._get_locked(sid)

            if runtime.snapshot.state in {
                VoiceStreamState.CANCELLED,
                VoiceStreamState.FAILED,
            }:
                return runtime.snapshot

            if runtime.snapshot.state is not VoiceStreamState.CANCEL_REQUESTED:
                self._transition_locked(
                    runtime,
                    VoiceStreamState.CANCEL_REQUESTED,
                )

            runtime.cancel_event.set()
            runtime.cancellations += 1
            runtime.active_request_id = None
            runtime.interruption_requested = False

            task = self._active_tasks.get(sid)
            if task is not None and task is not asyncio.current_task():
                task.cancel()

            self._transition_locked(
                runtime,
                VoiceStreamState.CANCELLED,
            )
            return runtime.snapshot

    async def _fail(
        self,
        sid: str,
        error: VoiceStreamError,
    ) -> None:
        async with self._lock:
            runtime = self._get_locked(sid)
            if runtime.snapshot.state not in {
                VoiceStreamState.FAILED,
                VoiceStreamState.CANCELLED,
            }:
                self._transition_locked(
                    runtime,
                    VoiceStreamState.FAILED,
                )

            if error.code in {
                VoiceStreamErrorCode.PROVIDER_FAILURE,
                VoiceStreamErrorCode.OUTPUT_INVALID,
            }:
                runtime.provider_failures += 1

    async def _register_task(
        self,
        sid: str,
        task: asyncio.Task[object],
    ) -> None:
        async with self._lock:
            current = self._active_tasks.get(sid)
            if current is not None and current is not task:
                raise self._error(
                    sid,
                    VoiceStreamErrorCode.INVALID_STATE,
                    "voice session already has an active operation",
                )
            self._active_tasks[sid] = task

    async def _clear_task(
        self,
        sid: str,
        task: asyncio.Task[object],
    ) -> None:
        async with self._lock:
            if self._active_tasks.get(sid) is task:
                self._active_tasks.pop(sid, None)

    def _raise_if_cancelled(self, sid: str) -> None:
        runtime = self._sessions.get(sid)
        if runtime is None or runtime.cancel_event.is_set():
            raise self._error(
                sid,
                VoiceStreamErrorCode.CANCELLED,
                "voice stream was cancelled",
            )

    def _transition_locked(
        self,
        runtime: _Session,
        target: VoiceStreamState,
    ) -> None:
        VoiceStreamLifecycle.validate(
            runtime.snapshot.state,
            target,
        )
        runtime.snapshot = runtime.snapshot.model_copy(
            update={
                "state": target,
                "updated_at": utc_now(),
            }
        )

    def _get_locked(self, sid: str) -> _Session:
        runtime = self._sessions.get(sid)
        if runtime is None:
            raise ValueError(f"unknown voice streaming session: {sid}")
        return runtime

    @staticmethod
    def _require_id(value: str, field: str) -> str:
        resolved = value.strip()
        if not resolved:
            raise ValueError(f"{field} must not be blank")
        return resolved

    @staticmethod
    def _error(
        sid: str,
        code: VoiceStreamErrorCode,
        message: str,
        *,
        retryable: bool = False,
    ) -> VoiceStreamExecutionError:
        return VoiceStreamExecutionError(
            VoiceStreamError(
                session_id=sid,
                code=code,
                message=message,
                retryable=retryable,
                occurred_at=utc_now(),
            )
        )

    @staticmethod
    def _normalize_provider_error(
        sid: str,
        exc: VoiceProviderInvocationError,
    ) -> VoiceStreamExecutionError:
        provider_error = exc.error

        code = VoiceStreamErrorCode.PROVIDER_FAILURE

        if provider_error.code is VoiceProviderErrorCode.TIMEOUT:
            code = VoiceStreamErrorCode.TIMEOUT
        elif provider_error.code is VoiceProviderErrorCode.UNSUPPORTED_CAPABILITY:
            code = VoiceStreamErrorCode.UNSUPPORTED_CAPABILITY
        elif provider_error.code is VoiceProviderErrorCode.OUTPUT_INVALID:
            code = VoiceStreamErrorCode.OUTPUT_INVALID

        return VoiceStreamExecutionError(
            VoiceStreamError(
                session_id=sid,
                code=code,
                message=provider_error.message,
                retryable=provider_error.retryable,
                occurred_at=utc_now(),
            )
        )
