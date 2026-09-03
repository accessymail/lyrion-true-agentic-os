"""Unit tests for 19.4.6 voice session continuity contracts."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lyrion.voice.session.contracts import (
    VoiceSession,
    VoiceSessionError,
    VoiceSessionErrorCode,
    VoiceSessionResumeRequest,
    VoiceSessionResumeResult,
    VoiceSessionState,
    VoiceTurn,
    VoiceTurnStatus,
)
from lyrion.voice.session.lifecycle import VoiceSessionLifecycle

BASE_TIME = datetime(2026, 9, 3, 10, 0, tzinfo=UTC)


def make_session(
    *,
    state: VoiceSessionState = VoiceSessionState.CREATED,
    revision: int = 0,
    next_turn_sequence: int = 0,
) -> VoiceSession:
    return VoiceSession(
        session_id="session-1",
        correlation_id="correlation-1",
        state=state,
        session_revision=revision,
        next_turn_sequence=next_turn_sequence,
        created_at=BASE_TIME,
        last_activity_at=BASE_TIME,
        expires_at=BASE_TIME + timedelta(minutes=30),
        resumable_until=BASE_TIME + timedelta(minutes=10),
    )


def test_voice_session_accepts_valid_contract() -> None:
    session = make_session()

    assert session.session_id == "session-1"
    assert session.state is VoiceSessionState.CREATED
    assert session.session_revision == 0
    assert session.next_turn_sequence == 0
    assert session.continuity_version == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("session_id", ""),
        ("correlation_id", ""),
    ],
)
def test_voice_session_rejects_blank_identifiers(
    field: str,
    value: str,
) -> None:
    with pytest.raises(ValidationError):
        VoiceSession(
            **{
                **make_session().model_dump(),
                field: value,
            }
        )


def test_voice_session_requires_timezone_aware_timestamps() -> None:
    with pytest.raises(ValidationError):
        VoiceSession(
            session_id="session-1",
            correlation_id="correlation-1",
            state=VoiceSessionState.CREATED,
            session_revision=0,
            next_turn_sequence=0,
            created_at=datetime(2026, 9, 3, 10, 0),
            last_activity_at=BASE_TIME,
            expires_at=BASE_TIME + timedelta(minutes=30),
            resumable_until=BASE_TIME + timedelta(minutes=10),
        )


def test_voice_session_rejects_negative_revision() -> None:
    with pytest.raises(ValidationError):
        make_session(revision=-1)


def test_voice_session_rejects_negative_turn_sequence() -> None:
    with pytest.raises(ValidationError):
        make_session(next_turn_sequence=-1)


def test_voice_turn_accepts_valid_contract() -> None:
    turn = VoiceTurn(
        session_id="session-1",
        turn_id="turn-1",
        sequence=0,
        request_id="request-1",
        created_at=BASE_TIME,
        input_reference="voice-input://turn-1",
        output_reference="voice-output://turn-1",
        status=VoiceTurnStatus.COMPLETED,
        provenance="test",
    )

    assert turn.sequence == 0
    assert turn.status is VoiceTurnStatus.COMPLETED


def test_voice_turn_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValidationError):
        VoiceTurn(
            session_id="session-1",
            turn_id="turn-1",
            sequence=0,
            request_id="request-1",
            created_at=datetime(2026, 9, 3, 10, 0),
            status=VoiceTurnStatus.ACCEPTED,
            provenance="test",
        )


def test_resume_request_accepts_valid_contract() -> None:
    request = VoiceSessionResumeRequest(
        session_id="session-1",
        resume_reference="resume://opaque-reference",
        expected_revision=3,
        requested_at=BASE_TIME,
    )

    assert request.session_id == "session-1"
    assert request.expected_revision == 3


def test_resume_request_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValidationError):
        VoiceSessionResumeRequest(
            session_id="session-1",
            resume_reference="resume://opaque-reference",
            expected_revision=0,
            requested_at=datetime(2026, 9, 3, 10, 0),
        )


def test_resume_result_accepts_valid_contract() -> None:
    result = VoiceSessionResumeResult(
        session_id="session-1",
        session_revision=4,
        state=VoiceSessionState.ACTIVE,
        next_turn_sequence=7,
        resumed_at=BASE_TIME,
    )

    assert result.session_revision == 4
    assert result.next_turn_sequence == 7
    assert result.state is VoiceSessionState.ACTIVE


def test_session_error_accepts_valid_contract() -> None:
    error = VoiceSessionError(
        session_id="session-1",
        code=VoiceSessionErrorCode.STALE_SESSION_REVISION,
        message="revision conflict",
        retryable=False,
        occurred_at=BASE_TIME,
    )

    assert error.code is VoiceSessionErrorCode.STALE_SESSION_REVISION
    assert error.retryable is False


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (VoiceSessionState.CREATED, VoiceSessionState.ACTIVE),
        (VoiceSessionState.CREATED, VoiceSessionState.CLOSED),
        (VoiceSessionState.CREATED, VoiceSessionState.EXPIRED),
        (VoiceSessionState.ACTIVE, VoiceSessionState.SUSPENDED),
        (VoiceSessionState.ACTIVE, VoiceSessionState.EXPIRED),
        (VoiceSessionState.ACTIVE, VoiceSessionState.CLOSED),
        (VoiceSessionState.SUSPENDED, VoiceSessionState.RESUMABLE),
        (VoiceSessionState.SUSPENDED, VoiceSessionState.EXPIRED),
        (VoiceSessionState.SUSPENDED, VoiceSessionState.CLOSED),
        (VoiceSessionState.RESUMABLE, VoiceSessionState.ACTIVE),
        (VoiceSessionState.RESUMABLE, VoiceSessionState.EXPIRED),
        (VoiceSessionState.RESUMABLE, VoiceSessionState.CLOSED),
    ],
)
def test_allowed_session_transitions(
    current: VoiceSessionState,
    target: VoiceSessionState,
) -> None:
    assert VoiceSessionLifecycle.is_allowed(current, target) is True
    VoiceSessionLifecycle.validate(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (VoiceSessionState.CREATED, VoiceSessionState.SUSPENDED),
        (VoiceSessionState.CREATED, VoiceSessionState.RESUMABLE),
        (VoiceSessionState.ACTIVE, VoiceSessionState.CREATED),
        (VoiceSessionState.ACTIVE, VoiceSessionState.RESUMABLE),
        (VoiceSessionState.SUSPENDED, VoiceSessionState.ACTIVE),
        (VoiceSessionState.RESUMABLE, VoiceSessionState.SUSPENDED),
        (VoiceSessionState.EXPIRED, VoiceSessionState.ACTIVE),
        (VoiceSessionState.EXPIRED, VoiceSessionState.RESUMABLE),
        (VoiceSessionState.CLOSED, VoiceSessionState.ACTIVE),
        (VoiceSessionState.CLOSED, VoiceSessionState.RESUMABLE),
    ],
)
def test_forbidden_session_transitions_fail_closed(
    current: VoiceSessionState,
    target: VoiceSessionState,
) -> None:
    assert VoiceSessionLifecycle.is_allowed(current, target) is False

    with pytest.raises(ValueError, match="invalid voice session transition"):
        VoiceSessionLifecycle.validate(current, target)


@pytest.mark.parametrize(
    "terminal_state",
    [
        VoiceSessionState.EXPIRED,
        VoiceSessionState.CLOSED,
    ],
)
def test_terminal_states_have_no_outgoing_transitions(
    terminal_state: VoiceSessionState,
) -> None:
    for target in VoiceSessionState:
        assert VoiceSessionLifecycle.is_allowed(
            terminal_state,
            target,
        ) is False


def test_session_contract_is_immutable() -> None:
    session = make_session()

    with pytest.raises(ValidationError):
        session.session_revision = 1  # type: ignore[misc]


def test_turn_contract_is_immutable() -> None:
    turn = VoiceTurn(
        session_id="session-1",
        turn_id="turn-1",
        sequence=0,
        request_id="request-1",
        created_at=BASE_TIME,
        status=VoiceTurnStatus.ACCEPTED,
        provenance="test",
    )

    with pytest.raises(ValidationError):
        turn.sequence = 1  # type: ignore[misc]
