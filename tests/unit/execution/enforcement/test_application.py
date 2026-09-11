"""Tests for C2.1 Linux enforcement application contracts."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from lyrion.execution.backends.linux.enforcement import (
    EnforcementApplicationContext,
    EnforcementApplicationResult,
    EnforcementApplicationStatus,
    EnforcementEvidence,
    EnforcementPrimitive,
    EnforcementPrimitiveResult,
    EnforcementState,
)


def verified_primitive(
    primitive: EnforcementPrimitive = EnforcementPrimitive.NO_NEW_PRIVS,
) -> EnforcementPrimitiveResult:
    """Build one valid verified primitive result."""
    evidence = EnforcementEvidence.verified(
        primitive=primitive,
        evidence_type="kernel-observation",
        observation="control verified",
    )

    return EnforcementPrimitiveResult(
        primitive=primitive,
        required=True,
        state=EnforcementState.VERIFIED,
        success=True,
        reason="verified",
        evidence=(evidence,),
    )


def test_context_is_immutable() -> None:
    context = EnforcementApplicationContext.create(
        execution_id="exec-1",
        backend_id="linux-native",
        started_at=datetime.now(UTC),
    )

    with pytest.raises(ValidationError):
        context.execution_id = "changed"  # type: ignore[misc]


def test_context_normalizes_timestamp_and_metadata() -> None:
    timestamp = datetime(
        2026,
        9,
        7,
        10,
        0,
        tzinfo=UTC,
    )

    context = EnforcementApplicationContext.create(
        execution_id="exec-1",
        backend_id="linux-native",
        started_at=timestamp,
        metadata={"z": "2", "a": "1"},
    )

    assert context.started_at == timestamp
    assert context.metadata == (
        ("a", "1"),
        ("z", "2"),
    )


def test_verified_evidence_is_explicitly_verified() -> None:
    evidence = EnforcementEvidence.verified(
        primitive=EnforcementPrimitive.NO_NEW_PRIVS,
        evidence_type="kernel-observation",
        observation="no_new_privs verified",
    )

    assert evidence.observed_state is EnforcementState.VERIFIED


def test_verified_primitive_requires_evidence() -> None:
    with pytest.raises(
        ValueError,
        match="requires evidence",
    ):
        EnforcementPrimitiveResult(
            primitive=EnforcementPrimitive.NO_NEW_PRIVS,
            required=True,
            state=EnforcementState.VERIFIED,
            success=True,
            reason="verified",
        )


def test_failed_primitive_cannot_report_success() -> None:
    with pytest.raises(
        ValueError,
        match="cannot be successful",
    ):
        EnforcementPrimitiveResult(
            primitive=EnforcementPrimitive.NO_NEW_PRIVS,
            required=True,
            state=EnforcementState.FAILED,
            success=True,
            reason="failed",
        )


def test_verified_primitive_requires_matching_evidence() -> None:
    evidence = EnforcementEvidence.verified(
        primitive=EnforcementPrimitive.CAPABILITIES,
        evidence_type="kernel-observation",
        observation="verified",
    )

    with pytest.raises(
        ValueError,
        match="match the verified primitive",
    ):
        EnforcementPrimitiveResult(
            primitive=EnforcementPrimitive.NO_NEW_PRIVS,
            required=True,
            state=EnforcementState.VERIFIED,
            success=True,
            reason="verified",
            evidence=(evidence,),
        )


def test_verified_application_requires_all_required_primitives_verified() -> None:
    with pytest.raises(
        ValueError,
        match="every required primitive",
    ):
        EnforcementApplicationResult(
            execution_id="exec-1",
            backend_id="linux-native",
            status=EnforcementApplicationStatus.VERIFIED,
            primitive_results=(
                EnforcementPrimitiveResult(
                    primitive=EnforcementPrimitive.NO_NEW_PRIVS,
                    required=True,
                    state=EnforcementState.PLANNED,
                    success=True,
                    reason="not yet verified",
                ),
            ),
        )


def test_failed_application_is_not_execution_permitted() -> None:
    result = EnforcementApplicationResult(
        execution_id="exec-1",
        backend_id="linux-native",
        status=EnforcementApplicationStatus.FAILED,
        primitive_results=(),
        failure_reason="mandatory control failed",
    )

    assert result.execution_permitted is False


def test_verified_application_permits_execution() -> None:
    result = EnforcementApplicationResult(
        execution_id="exec-1",
        backend_id="linux-native",
        status=EnforcementApplicationStatus.VERIFIED,
        primitive_results=(verified_primitive(),),
    )

    assert result.execution_permitted is True


def test_verified_application_cannot_have_failure_reason() -> None:
    with pytest.raises(
        ValueError,
        match="cannot contain a failure reason",
    ):
        EnforcementApplicationResult(
            execution_id="exec-1",
            backend_id="linux-native",
            status=EnforcementApplicationStatus.VERIFIED,
            primitive_results=(verified_primitive(),),
            failure_reason="incorrect",
        )


def test_aborted_application_requires_failure_reason() -> None:
    with pytest.raises(
        ValueError,
        match="requires a failure reason",
    ):
        EnforcementApplicationResult(
            execution_id="exec-1",
            backend_id="linux-native",
            status=EnforcementApplicationStatus.ABORTED,
            primitive_results=(),
        )


def test_unknown_application_status_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EnforcementApplicationResult(
            execution_id="exec-1",
            backend_id="linux-native",
            status="unknown",
            primitive_results=(),
        )
