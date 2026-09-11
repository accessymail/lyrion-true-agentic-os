"""Tests for controlled provider-neutral model failover."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lyrion.core.types import ExecutionTarget
from lyrion.models.contracts import ModelCapability, ModelModality, ModelRequest, ModelResponse
from lyrion.models.failure_state import ModelFailureTracker, ModelTarget
from lyrion.models.resilience import (
    FailoverModelGateway,
    ModelErrorClass,
    ModelFailoverError,
    ModelRetryPolicy,
    classify_model_error,
)
from lyrion.models.router import ModelDescriptor, ModelRouter, ModelRoutingError, ModelSelection


class StatusError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"status {status_code}")
        self.status_code = status_code


class FakeSelectableGateway:
    def __init__(self, failures: dict[ModelTarget, list[Exception]]) -> None:
        self.failures = failures
        self.calls: list[ModelTarget] = []

    async def generate(self, request: ModelRequest) -> ModelResponse:
        raise AssertionError("explicit selection must be used")

    async def generate_for_selection(
        self,
        request: ModelRequest,
        selection: ModelSelection,
    ) -> ModelResponse:
        target = selection.target()
        self.calls.append(target)
        failures = self.failures.get(target)
        if failures:
            raise failures.pop(0)
        return ModelResponse(
            request_id=request.request_id,
            content=f"success:{target.model}",
            provider=target.provider,
            model=target.model,
            execution_target=ExecutionTarget.CLOUD_API,
            confidence=0.9,
            created_at=datetime.now(UTC),
        )


def make_target(name: str) -> ModelTarget:
    return ModelTarget(
        provider="fake",
        model=name,
        execution_target_name=ExecutionTarget.CLOUD_API.value,
    )


def make_request() -> ModelRequest:
    return ModelRequest(
        request_id="request:failover:001",
        objective="test controlled failover",
        modality=ModelModality.TEXT,
        created_at=datetime.now(UTC),
    )


def make_descriptor(name: str, reliability: float) -> ModelDescriptor:
    return ModelDescriptor(
        provider="fake",
        model=name,
        capabilities=frozenset({ModelCapability.GENERATION}),
        modalities=frozenset({ModelModality.TEXT}),
        execution_target_name=ExecutionTarget.CLOUD_API.value,
        reasoning_quality=0.5,
        reliability_score=reliability,
        health_score=1.0,
        latency_score=0.5,
        cost_score=0.5,
    )


def make_router() -> ModelRouter:
    return ModelRouter((
        make_descriptor("cloud-a", 1.0),
        make_descriptor("cloud-b", 0.9),
    ))


def test_retryable_and_terminal_classification() -> None:
    assert classify_model_error(StatusError(503)) is ModelErrorClass.RETRYABLE
    assert classify_model_error(StatusError(400)) is ModelErrorClass.TERMINAL


@pytest.mark.asyncio
async def test_failover_uses_alternate_after_transient_failure() -> None:
    first = make_target("cloud-a")
    second = make_target("cloud-b")
    delegate = FakeSelectableGateway({first: [StatusError(503)]})
    tracker = ModelFailureTracker()
    gateway = FailoverModelGateway(
        delegate=delegate,
        router=make_router(),
        tracker=tracker,
        policy=ModelRetryPolicy(
            max_attempts=1,
            initial_delay_seconds=0.0,
            jitter_ratio=0.0,
        ),
        max_targets=2,
    )
    response = await gateway.generate(make_request())
    assert response.content == "success:cloud-b"
    assert delegate.calls == [first, second]
    assert tracker.is_excluded(first)


@pytest.mark.asyncio
async def test_terminal_failure_does_not_failover() -> None:
    first = make_target("cloud-a")
    delegate = FakeSelectableGateway({first: [StatusError(400)]})
    gateway = FailoverModelGateway(
        delegate=delegate,
        router=make_router(),
        tracker=ModelFailureTracker(),
        policy=ModelRetryPolicy(
            max_attempts=1,
            initial_delay_seconds=0.0,
            jitter_ratio=0.0,
        ),
    )
    with pytest.raises(StatusError):
        await gateway.generate(make_request())
    assert delegate.calls == [first]


@pytest.mark.asyncio
async def test_failover_is_bounded() -> None:
    first = make_target("cloud-a")
    second = make_target("cloud-b")
    delegate = FakeSelectableGateway({
        first: [StatusError(503)],
        second: [StatusError(503)],
    })
    gateway = FailoverModelGateway(
        delegate=delegate,
        router=make_router(),
        tracker=ModelFailureTracker(),
        policy=ModelRetryPolicy(
            max_attempts=1,
            initial_delay_seconds=0.0,
            jitter_ratio=0.0,
        ),
        max_targets=2,
    )
    with pytest.raises(ModelFailoverError):
        await gateway.generate(make_request())
    assert delegate.calls == [first, second]


@pytest.mark.asyncio
async def test_existing_failure_state_excludes_target() -> None:
    first = make_target("cloud-a")
    second = make_target("cloud-b")
    tracker = ModelFailureTracker()
    tracker.record_failure(first)
    delegate = FakeSelectableGateway({})
    gateway = FailoverModelGateway(
        delegate=delegate,
        router=make_router(),
        tracker=tracker,
        policy=ModelRetryPolicy(
            max_attempts=1,
            initial_delay_seconds=0.0,
            jitter_ratio=0.0,
        ),
        max_targets=2,
    )
    response = await gateway.generate(make_request())
    assert response.content == "success:cloud-b"
    assert delegate.calls == [second]


def test_router_fails_closed_when_all_targets_excluded() -> None:
    router = make_router()
    with pytest.raises(ModelRoutingError):
        router.route(
            make_request(),
            excluded_targets={make_target("cloud-a"), make_target("cloud-b")},
        )

@pytest.mark.asyncio
async def test_failover_reuses_one_request_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    first = make_target("cloud-a")
    second = make_target("cloud-b")
    delegate = FakeSelectableGateway({})
    gateway = FailoverModelGateway(
        delegate=delegate,
        router=make_router(),
        tracker=ModelFailureTracker(),
        policy=ModelRetryPolicy(
            max_attempts=1,
            initial_delay_seconds=0.0,
            jitter_ratio=0.0,
        ),
        max_targets=2,
    )
    deadlines: list[float] = []
    calls = 0

    async def fake_retry_operation(
        operation: object,
        request: ModelRequest,
        policy: ModelRetryPolicy,
        deadline: float,
    ) -> ModelResponse:
        nonlocal calls
        deadlines.append(deadline)
        calls += 1
        if calls == 1:
            raise StatusError(503)
        return await delegate.generate_for_selection(
            request,
            ModelSelection(
                provider=second.provider,
                model=second.model,
                execution_target_name=second.execution_target_name,
            ),
        )

    monkeypatch.setattr(
        "lyrion.models.resilience._retry_operation",
        fake_retry_operation,
    )
    response = await gateway.generate(make_request())
    assert response.content == "success:cloud-b"
    assert len(deadlines) == 2
    assert deadlines[0] == deadlines[1]
    assert delegate.calls == [second]
    assert first != second
