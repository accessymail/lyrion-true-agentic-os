"""Tests for runtime model failure state and exclusion-aware routing."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from lyrion.core.types import ExecutionTarget
from lyrion.models.contracts import ModelCapability, ModelModality, ModelRequest
from lyrion.models.failure_state import ModelFailurePolicy, ModelFailureTracker, ModelTarget
from lyrion.models.router import ModelDescriptor, ModelRouter, ModelRoutingError


class FakeClock:
    """Deterministic monotonic clock for failure-state tests."""

    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def make_target(name: str = "cloud-a") -> ModelTarget:
    return ModelTarget(
        provider="fake",
        model=name,
        execution_target_name=ExecutionTarget.CLOUD_API.value,
    )


def make_request() -> ModelRequest:
    return ModelRequest(
        request_id="request:failure-state:001",
        objective="test routing failure state",
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


def test_failure_tracker_excludes_and_expires_target() -> None:
    clock = FakeClock()
    tracker = ModelFailureTracker(
        policy=ModelFailurePolicy(
            initial_cooldown_seconds=5.0,
            max_cooldown_seconds=20.0,
            multiplier=2.0,
        ),
        clock=clock,
    )
    target = make_target()
    first = tracker.record_failure(target)
    assert first.failure_count == 1
    assert tracker.is_excluded(target)
    assert target in tracker.excluded_targets()
    clock.advance(5.0)
    assert not tracker.is_excluded(target)
    assert tracker.failure_record(target) is None


def test_failure_tracker_backoff_is_bounded() -> None:
    clock = FakeClock()
    tracker = ModelFailureTracker(
        policy=ModelFailurePolicy(
            initial_cooldown_seconds=5.0,
            max_cooldown_seconds=10.0,
            multiplier=2.0,
        ),
        clock=clock,
    )
    target = make_target()
    first = tracker.record_failure(target)
    second = tracker.record_failure(target)
    third = tracker.record_failure(target)
    assert first.failure_count == 1
    assert second.failure_count == 2
    assert third.failure_count == 3
    assert second.excluded_until - clock.value == pytest.approx(10.0)
    assert third.excluded_until - clock.value == pytest.approx(10.0)


def test_success_clears_failure_state() -> None:
    tracker = ModelFailureTracker()
    target = make_target()
    tracker.record_failure(target)
    assert tracker.is_excluded(target)
    tracker.record_success(target)
    assert not tracker.is_excluded(target)
    assert tracker.failure_record(target) is None


def test_router_excludes_runtime_failed_target() -> None:
    router = ModelRouter((
        make_descriptor("cloud-a", reliability=1.0),
        make_descriptor("cloud-b", reliability=0.9),
    ))
    selection = router.route(
        make_request(),
        excluded_targets={make_target("cloud-a")},
    )
    assert selection.model == "cloud-b"


def test_router_fails_closed_when_all_targets_excluded() -> None:
    router = ModelRouter((
        make_descriptor("cloud-a", reliability=1.0),
        make_descriptor("cloud-b", reliability=0.9),
    ))
    with pytest.raises(ModelRoutingError):
        router.route(
            make_request(),
            excluded_targets={
                make_target("cloud-a"),
                make_target("cloud-b"),
            },
        )

def test_failure_threshold_delays_exclusion() -> None:
    clock = FakeClock()
    target = make_target("cloud-a")
    tracker = ModelFailureTracker(
        policy=ModelFailurePolicy(failure_threshold=2),
        clock=clock,
    )
    first = tracker.record_failure(target)
    assert first.failure_count == 1
    assert first.excluded_until == clock.value
    assert not tracker.is_excluded(target)
    second = tracker.record_failure(target)
    assert second.failure_count == 2
    assert tracker.is_excluded(target)

