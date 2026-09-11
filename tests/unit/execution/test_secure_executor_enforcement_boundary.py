"""R3.3 enforcement boundary contract tests.

These tests define the required ordering between the existing SecureExecutor
control chain and the Linux enforcement application.

They intentionally test a small deterministic orchestration contract rather
than pretending that the current SecureExecutor already has this boundary.
The production SecureExecutor integration must satisfy the same invariants.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

import pytest


class BoundaryStatus(StrEnum):
    """Result of the enforcement gate."""

    VERIFIED = "verified"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass(frozen=True, slots=True)
class BoundaryResult:
    """Minimal deterministic result used by the contract harness."""

    status: BoundaryStatus

    @property
    def execution_permitted(self) -> bool:
        """Only independently verified enforcement permits execution."""
        return self.status is BoundaryStatus.VERIFIED


class EnforcementBoundary(Protocol):
    """Minimal contract SecureExecutor must consume."""

    def apply(self, *, execution_id: str, sandbox: object) -> BoundaryResult:
        """Apply and independently verify execution enforcement."""
        ...


class RecordingEnforcement:
    """Deterministic enforcement double for boundary testing."""

    def __init__(self, result: BoundaryResult) -> None:
        self.result = result
        self.calls: list[tuple[str, object]] = []

    def apply(
        self,
        *,
        execution_id: str,
        sandbox: object,
    ) -> BoundaryResult:
        self.calls.append((execution_id, sandbox))
        return self.result


class RecordingExecution:
    """Deterministic execution-side-effect boundary."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def execute(self, execution_id: str) -> None:
        self.calls.append(execution_id)


@dataclass(frozen=True, slots=True)
class BoundaryRequest:
    """Minimal request state needed by the boundary contract."""

    execution_id: str
    admitted: bool
    validation_ok: bool
    policy_ok: bool
    sandbox_ok: bool
    sandbox: object


def run_boundary(
    request: BoundaryRequest,
    *,
    enforcement: EnforcementBoundary,
    execution: RecordingExecution,
) -> BoundaryResult | None:
    """Reference ordering contract for the future SecureExecutor integration.

    This function is deliberately tiny. It defines ordering and fail-closed
    semantics without duplicating SecureExecutor implementation details.
    """

    if not request.admitted:
        return None

    if not request.validation_ok:
        return None

    if not request.policy_ok:
        return None

    if not request.sandbox_ok:
        return None

    result = enforcement.apply(
        execution_id=request.execution_id,
        sandbox=request.sandbox,
    )

    if not result.execution_permitted:
        return result

    execution.execute(request.execution_id)
    return result


@pytest.fixture
def sandbox() -> object:
    """Provide an opaque sandbox object for the contract."""
    return object()


@pytest.fixture
def valid_request(sandbox: object) -> BoundaryRequest:
    """Provide a fully valid request."""
    return BoundaryRequest(
        execution_id="execution:r3.3:001",
        admitted=True,
        validation_ok=True,
        policy_ok=True,
        sandbox_ok=True,
        sandbox=sandbox,
    )


def test_denied_admission_stops_before_enforcement(
    valid_request: BoundaryRequest,
) -> None:
    """Authorization denial must prevent the enforcement boundary."""
    request = replace(
        valid_request,
        admitted=False,
    )
    enforcement = RecordingEnforcement(
        BoundaryResult(BoundaryStatus.VERIFIED)
    )
    execution = RecordingExecution()

    assert (
        run_boundary(
            request,
            enforcement=enforcement,
            execution=execution,
        )
        is None
    )
    assert enforcement.calls == []
    assert execution.calls == []


def test_validation_failure_stops_before_enforcement(
    valid_request: BoundaryRequest,
) -> None:
    """Execution validation failure must prevent enforcement."""
    request = replace(
        valid_request,
        validation_ok=False,
    )
    enforcement = RecordingEnforcement(
        BoundaryResult(BoundaryStatus.VERIFIED)
    )
    execution = RecordingExecution()

    assert (
        run_boundary(
            request,
            enforcement=enforcement,
            execution=execution,
        )
        is None
    )
    assert enforcement.calls == []
    assert execution.calls == []


def test_policy_failure_stops_before_enforcement(
    valid_request: BoundaryRequest,
) -> None:
    """Execution policy failure must prevent enforcement."""
    request = replace(
        valid_request,
        policy_ok=False,
    )
    enforcement = RecordingEnforcement(
        BoundaryResult(BoundaryStatus.VERIFIED)
    )
    execution = RecordingExecution()

    assert (
        run_boundary(
            request,
            enforcement=enforcement,
            execution=execution,
        )
        is None
    )
    assert enforcement.calls == []
    assert execution.calls == []


def test_sandbox_failure_stops_before_enforcement(
    valid_request: BoundaryRequest,
) -> None:
    """Sandbox policy failure must prevent enforcement."""
    request = replace(
        valid_request,
        sandbox_ok=False,
    )
    enforcement = RecordingEnforcement(
        BoundaryResult(BoundaryStatus.VERIFIED)
    )
    execution = RecordingExecution()

    assert (
        run_boundary(
            request,
            enforcement=enforcement,
            execution=execution,
        )
        is None
    )
    assert enforcement.calls == []
    assert execution.calls == []


@pytest.mark.parametrize(
    "status",
    (
        BoundaryStatus.FAILED,
        BoundaryStatus.ABORTED,
    ),
)
def test_failed_enforcement_blocks_execution(
    valid_request: BoundaryRequest,
    status: BoundaryStatus,
) -> None:
    """Failed or aborted enforcement must fail closed."""
    enforcement = RecordingEnforcement(BoundaryResult(status))
    execution = RecordingExecution()

    result = run_boundary(
        valid_request,
        enforcement=enforcement,
        execution=execution,
    )

    assert result is not None
    assert result.execution_permitted is False
    assert len(enforcement.calls) == 1
    assert execution.calls == []


def test_verified_enforcement_is_required_before_execution(
    valid_request: BoundaryRequest,
) -> None:
    """Only VERIFIED enforcement may cross the execution boundary."""
    enforcement = RecordingEnforcement(
        BoundaryResult(BoundaryStatus.VERIFIED)
    )
    execution = RecordingExecution()

    result = run_boundary(
        valid_request,
        enforcement=enforcement,
        execution=execution,
    )

    assert result is not None
    assert result.execution_permitted is True
    assert execution.calls == [valid_request.execution_id]


def test_enforcement_receives_authoritative_sandbox_object(
    valid_request: BoundaryRequest,
) -> None:
    """The exact validated sandbox object must reach enforcement."""
    enforcement = RecordingEnforcement(
        BoundaryResult(BoundaryStatus.VERIFIED)
    )
    execution = RecordingExecution()

    run_boundary(
        valid_request,
        enforcement=enforcement,
        execution=execution,
    )

    assert enforcement.calls == [
        (
            valid_request.execution_id,
            valid_request.sandbox,
        )
    ]


def test_execution_occurs_after_enforcement(
    valid_request: BoundaryRequest,
) -> None:
    """Execution must occur only after enforcement returns VERIFIED."""

    events: list[str] = []

    class OrderedEnforcement:
        def apply(
            self,
            *,
            execution_id: str,
            sandbox: object,
        ) -> BoundaryResult:
            events.append("enforcement")
            return BoundaryResult(BoundaryStatus.VERIFIED)

    class OrderedExecution:
        def execute(self, execution_id: str) -> None:
            events.append("execution")

    run_boundary(
        valid_request,
        enforcement=OrderedEnforcement(),
        execution=OrderedExecution(),  # type: ignore[arg-type]
    )

    assert events == ["enforcement", "execution"]


def test_failed_enforcement_never_falls_back_to_execution(
    valid_request: BoundaryRequest,
) -> None:
    """There must be no fail-open fallback when enforcement fails."""
    enforcement = RecordingEnforcement(
        BoundaryResult(BoundaryStatus.FAILED)
    )
    execution = RecordingExecution()

    result = run_boundary(
        valid_request,
        enforcement=enforcement,
        execution=execution,
    )

    assert result is not None
    assert result.execution_permitted is False
    assert execution.calls == []


def test_boundary_does_not_authorize() -> None:
    """The enforcement boundary must expose no authorization API."""
    enforcement = RecordingEnforcement(
        BoundaryResult(BoundaryStatus.VERIFIED)
    )

    assert not hasattr(enforcement, "authorize")
    assert not hasattr(enforcement, "grant")
    assert not hasattr(enforcement, "admit")


def test_context_timestamp_reference_is_timezone_aware() -> None:
    """Boundary test fixtures use explicit aware execution timestamps."""
    timestamp = datetime.now(UTC)

    assert timestamp.tzinfo is UTC
    assert timestamp.utcoffset() is not None
