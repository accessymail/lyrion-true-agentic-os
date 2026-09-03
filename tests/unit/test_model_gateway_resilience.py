"""Tests for provider-neutral Model Gateway resilience."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lyrion.core.types import ExecutionTarget
from lyrion.models.contracts import ModelRequest, ModelResponse
from lyrion.models.resilience import (
    ModelErrorClass,
    ModelRetryPolicy,
    RetryingModelGateway,
    classify_model_error,
)


class StatusError(Exception):
    """Deterministic error carrying an HTTP-like status."""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"status {status_code}")
        self.status_code = status_code


class FakeGateway:
    """Gateway that fails a bounded number of times."""

    def __init__(
        self,
        failures: list[Exception],
    ) -> None:
        self.failures = failures
        self.calls = 0

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return ModelResponse(
            request_id=request.request_id,
            content="success",
            provider="fake",
            model="fake-model",
            execution_target=ExecutionTarget.CLOUD_API,
            confidence=0.9,
            created_at=datetime.now(UTC),
        )


def make_request() -> ModelRequest:
    return ModelRequest(
        request_id="request:resilience:001",
        objective="Test resilient gateway.",
        created_at=datetime.now(UTC),
    )


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (TimeoutError("timeout"), ModelErrorClass.RETRYABLE),
        (ConnectionError("connection"), ModelErrorClass.RETRYABLE),
        (StatusError(429), ModelErrorClass.RETRYABLE),
        (StatusError(500), ModelErrorClass.RETRYABLE),
        (StatusError(503), ModelErrorClass.RETRYABLE),
        (StatusError(504), ModelErrorClass.RETRYABLE),
        (StatusError(400), ModelErrorClass.TERMINAL),
        (StatusError(401), ModelErrorClass.TERMINAL),
        (StatusError(403), ModelErrorClass.TERMINAL),
        (StatusError(404), ModelErrorClass.TERMINAL),
        (ValueError("invalid"), ModelErrorClass.TERMINAL),
    ],
)
def test_classify_model_error(
    error: Exception,
    expected: ModelErrorClass,
) -> None:
    assert classify_model_error(error) is expected


@pytest.mark.asyncio
async def test_retrying_gateway_retries_transient_failure() -> None:
    delegate = FakeGateway([
        StatusError(503),
        StatusError(503),
    ])
    gateway = RetryingModelGateway(
        delegate=delegate,
        policy=ModelRetryPolicy(
            max_attempts=3,
            initial_delay_seconds=0.0,
            max_delay_seconds=0.0,
            jitter_ratio=0.0,
        ),
    )

    response = await gateway.generate(make_request())

    assert response.content == "success"
    assert delegate.calls == 3


@pytest.mark.asyncio
async def test_retrying_gateway_does_not_retry_terminal_failure() -> None:
    delegate = FakeGateway([StatusError(400)])
    gateway = RetryingModelGateway(
        delegate=delegate,
        policy=ModelRetryPolicy(
            max_attempts=3,
            initial_delay_seconds=0.0,
            jitter_ratio=0.0,
        ),
    )

    with pytest.raises(StatusError):
        await gateway.generate(make_request())

    assert delegate.calls == 1


@pytest.mark.asyncio
async def test_retrying_gateway_stops_at_max_attempts() -> None:
    delegate = FakeGateway([
        StatusError(503),
        StatusError(503),
        StatusError(503),
        StatusError(503),
    ])
    gateway = RetryingModelGateway(
        delegate=delegate,
        policy=ModelRetryPolicy(
            max_attempts=3,
            initial_delay_seconds=0.0,
            jitter_ratio=0.0,
        ),
    )

    with pytest.raises(StatusError):
        await gateway.generate(make_request())

    assert delegate.calls == 3
