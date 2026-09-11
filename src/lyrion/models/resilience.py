"""Provider-neutral retry and error classification for model access."""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from lyrion.models.contracts import ModelRequest, ModelResponse
from lyrion.models.failure_state import ModelFailureTracker, ModelTarget
from lyrion.models.gateway import ModelGateway
from lyrion.models.router import ModelRouter, ModelSelection


class ModelErrorClass(StrEnum):
    """High-level classification used by the Model Fabric."""

    RETRYABLE = "RETRYABLE"
    TERMINAL = "TERMINAL"


class ModelRetryPolicyError(ValueError):
    """Raised when a retry policy is invalid."""


@dataclass(frozen=True)
class ModelRetryPolicy:
    """Bounded exponential-backoff policy for model access."""

    max_attempts: int = 3
    initial_delay_seconds: float = 0.5
    max_delay_seconds: float = 4.0
    multiplier: float = 2.0
    jitter_ratio: float = 0.2

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ModelRetryPolicyError("max_attempts must be at least 1")
        if self.initial_delay_seconds < 0.0:
            raise ModelRetryPolicyError(
                "initial_delay_seconds must not be negative",
            )
        if self.max_delay_seconds < self.initial_delay_seconds:
            raise ModelRetryPolicyError(
                "max_delay_seconds must be at least initial_delay_seconds",
            )
        if self.multiplier < 1.0:
            raise ModelRetryPolicyError("multiplier must be at least 1")
        if not 0.0 <= self.jitter_ratio <= 1.0:
            raise ModelRetryPolicyError("jitter_ratio must be between 0 and 1")

    def delay_for_attempt(self, attempt: int) -> float:
        """Return the bounded delay before the next attempt."""
        if attempt < 1:
            raise ValueError("attempt must be at least 1")

        base_delay = min(
            self.max_delay_seconds,
            self.initial_delay_seconds * self.multiplier ** (attempt - 1),
        )

        if self.jitter_ratio == 0.0:
            return base_delay

        lower = base_delay * (1.0 - self.jitter_ratio)
        upper = base_delay * (1.0 + self.jitter_ratio)
        return random.uniform(lower, upper)


def classify_model_error(error: BaseException) -> ModelErrorClass:
    """Classify provider failures without importing provider SDKs."""
    if isinstance(error, (TimeoutError, ConnectionError)):
        return ModelErrorClass.RETRYABLE

    status_code = _extract_status_code(error)
    if status_code in {429, 500, 502, 503, 504}:
        return ModelErrorClass.RETRYABLE

    return ModelErrorClass.TERMINAL


def _extract_status_code(error: BaseException) -> int | None:
    """Extract a numeric HTTP-like status code from common error shapes."""
    for attribute in ("status_code", "code"):
        value = getattr(error, attribute, None)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)

    response = getattr(error, "response", None)
    value = getattr(response, "status_code", None)
    if isinstance(value, int):
        return value

    return None


class RetryingModelGateway:
    """Add bounded provider-neutral retry behavior to a Model Gateway."""

    def __init__(
        self,
        *,
        delegate: ModelGateway,
        policy: ModelRetryPolicy | None = None,
    ) -> None:
        self._delegate = delegate
        self._policy = policy or ModelRetryPolicy()

    @property
    def delegate(self) -> ModelGateway:
        return self._delegate

    @property
    def policy(self) -> ModelRetryPolicy:
        return self._policy

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate a response within the request runtime budget."""
        deadline = time.monotonic() + request.budget.max_runtime_seconds
        attempt = 1

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0.0:
                raise TimeoutError("model gateway runtime budget exhausted")

            try:
                return await asyncio.wait_for(
                    self._delegate.generate(request),
                    timeout=remaining,
                )
            except Exception as error:
                if (
                    attempt >= self._policy.max_attempts
                    or classify_model_error(error)
                    is ModelErrorClass.TERMINAL
                ):
                    raise

                delay = self._policy.delay_for_attempt(attempt)
                remaining = deadline - time.monotonic()
                if remaining <= delay:
                    raise TimeoutError(
                        "model gateway retry budget exhausted",
                    ) from error

                await asyncio.sleep(delay)
                attempt += 1


class SelectableModelGateway(Protocol):
    async def generate_for_selection(
        self,
        request: ModelRequest,
        selection: ModelSelection,
    ) -> ModelResponse:
        ...


class ModelFailoverError(RuntimeError):
    """Raised when no model target can complete a request."""


class FailoverModelGateway:
    """Retry transient failures and fail over between eligible model targets."""

    def __init__(
        self,
        *,
        delegate: SelectableModelGateway,
        router: ModelRouter,
        tracker: ModelFailureTracker | None = None,
        policy: ModelRetryPolicy | None = None,
        max_targets: int = 2,
    ) -> None:
        if max_targets < 1:
            raise ValueError("max_targets must be at least 1")

        self._delegate = delegate
        self._router = router
        self._tracker = tracker or ModelFailureTracker()
        self._policy = policy or ModelRetryPolicy()
        self._max_targets = max_targets

    @property
    def delegate(self) -> SelectableModelGateway:
        return self._delegate

    @property
    def tracker(self) -> ModelFailureTracker:
        return self._tracker

    @property
    def policy(self) -> ModelRetryPolicy:
        return self._policy

    @property
    def max_targets(self) -> int:
        return self._max_targets

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate through bounded retries and alternate-target failover."""
        delegate = self._delegate
        failed_targets: set[ModelTarget] = set()
        last_error: Exception | None = None
        deadline = time.monotonic() + request.budget.max_runtime_seconds

        for _ in range(self._max_targets):
            if time.monotonic() >= deadline:
                if last_error is not None:
                    raise ModelFailoverError(
                        "model failover runtime budget exhausted",
                    ) from last_error
                raise TimeoutError(
                    "model gateway runtime budget exhausted",
                )

            excluded_targets = self._tracker.excluded_targets() | frozenset(failed_targets)

            try:
                selection = self._router.route(
                    request,
                    excluded_targets=excluded_targets,
                )
            except Exception as error:
                if last_error is not None:
                    raise last_error from None
                raise error from None

            target = selection.target()

            try:
                async def execute_selected(
                    current_request: ModelRequest,
                    selected: ModelSelection = selection,
                ) -> ModelResponse:
                    return await delegate.generate_for_selection(
                        current_request,
                        selected,
                    )

                response = await _retry_operation(
                    execute_selected,
                    request,
                    self._policy,
                    deadline,

                )
            except Exception as error:
                if classify_model_error(error) is ModelErrorClass.TERMINAL:
                    raise

                failed_targets.add(target)
                self._tracker.record_failure(target)
                last_error = error
                continue

            self._tracker.record_success(target)
            return response

        if last_error is not None:
            raise ModelFailoverError(
                "all eligible model targets failed",
            ) from last_error

        raise ModelFailoverError("no model target was available")


async def _retry_operation(
    operation: Callable[[ModelRequest], Awaitable[ModelResponse]],
    request: ModelRequest,
    policy: ModelRetryPolicy,
    deadline: float,
) -> ModelResponse:
    """Execute one target within the shared request runtime budget."""
    attempt = 1

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0.0:
            raise TimeoutError("model gateway runtime budget exhausted")

        try:
            return await asyncio.wait_for(operation(request), timeout=remaining)
        except Exception as error:
            if (
                attempt >= policy.max_attempts
                or classify_model_error(error) is ModelErrorClass.TERMINAL
            ):
                raise

            delay = policy.delay_for_attempt(attempt)
            remaining = deadline - time.monotonic()
            if remaining <= delay:
                raise TimeoutError("model gateway retry budget exhausted") from error

            await asyncio.sleep(delay)
            attempt += 1
