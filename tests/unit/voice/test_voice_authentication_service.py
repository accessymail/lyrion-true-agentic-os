from datetime import UTC, datetime, timedelta

from lyrion.security.replay import ReplayGuard
from lyrion.voice.authentication import (
    DeterministicVoiceAuthenticationVerifier,
    VoiceAuthenticationAssurance,
    VoiceAuthenticationMethod,
    VoiceAuthenticationRequest,
    VoiceAuthenticationService,
    VoiceAuthenticationStatus,
    VoiceVerificationObservation,
)


def make_request(
    *,
    request_id: str = "request-1",
    idempotency_key: str = "idem-1",
    now: datetime | None = None,
) -> VoiceAuthenticationRequest:
    requested_at = now or datetime.now(UTC)

    return VoiceAuthenticationRequest(
        request_id=request_id,
        session_id="session-1",
        claimed_principal_id="principal-1",
        method=VoiceAuthenticationMethod.SPEAKER_VERIFICATION,
        correlation_id="corr-1",
        idempotency_key=idempotency_key,
        requested_at=requested_at,
        expires_at=requested_at + timedelta(minutes=1),
    )


def make_observation() -> VoiceVerificationObservation:
    return VoiceVerificationObservation(
        matched_principal_id="principal-1",
        method=VoiceAuthenticationMethod.SPEAKER_VERIFICATION,
        assurance=VoiceAuthenticationAssurance.HIGH,
        provider_id="provider-1",
        evidence_id="evidence-1",
        evidence_reference="opaque:evidence:1",
        observed_at=datetime.now(UTC),
    )


def test_successful_authentication() -> None:
    now = datetime.now(UTC)
    request = make_request(now=now)
    service = VoiceAuthenticationService(
        verifier=DeterministicVoiceAuthenticationVerifier(),
        clock=lambda: now + timedelta(seconds=1),
    )

    result = service.authenticate(
        request=request,
        observation=make_observation(),
    )

    assert result.status is VoiceAuthenticationStatus.VERIFIED
    assert result.authenticated_principal_id == "principal-1"


def test_replay_is_rejected() -> None:
    now = datetime.now(UTC)
    request = make_request(now=now)
    service = VoiceAuthenticationService(
        verifier=DeterministicVoiceAuthenticationVerifier(),
        replay_guard=ReplayGuard(),
        clock=lambda: now + timedelta(seconds=1),
    )

    first = service.authenticate(
        request=request,
        observation=make_observation(),
    )
    second = service.authenticate(
        request=request,
        observation=make_observation(),
    )

    assert first.status is VoiceAuthenticationStatus.VERIFIED
    assert second.status is VoiceAuthenticationStatus.REJECTED
    assert second.authenticated_principal_id is None


def test_same_idempotency_key_for_different_request_is_rejected() -> None:
    now = datetime.now(UTC)
    replay_guard = ReplayGuard()

    first_request = make_request(
        request_id="request-1",
        idempotency_key="shared-idem",
        now=now,
    )
    second_request = make_request(
        request_id="request-2",
        idempotency_key="shared-idem",
        now=now,
    )

    service = VoiceAuthenticationService(
        verifier=DeterministicVoiceAuthenticationVerifier(),
        replay_guard=replay_guard,
        clock=lambda: now + timedelta(seconds=1),
    )

    first = service.authenticate(
        request=first_request,
        observation=make_observation(),
    )
    second = service.authenticate(
        request=second_request,
        observation=make_observation(),
    )

    assert first.status is VoiceAuthenticationStatus.VERIFIED
    assert second.status is VoiceAuthenticationStatus.REJECTED
    assert "Replay" in second.reason


def test_expired_request_does_not_reach_verifier() -> None:
    now = datetime.now(UTC)
    request = make_request(now=now)
    service = VoiceAuthenticationService(
        verifier=DeterministicVoiceAuthenticationVerifier(),
        clock=lambda: request.expires_at + timedelta(seconds=1),
    )

    result = service.authenticate(
        request=request,
        observation=make_observation(),
    )

    assert result.status is VoiceAuthenticationStatus.EXPIRED


def test_future_request_is_rejected() -> None:
    now = datetime.now(UTC)
    request = make_request(
        now=now + timedelta(minutes=1),
    )
    service = VoiceAuthenticationService(
        verifier=DeterministicVoiceAuthenticationVerifier(),
        clock=lambda: now,
    )

    result = service.authenticate(
        request=request,
        observation=make_observation(),
    )

    assert result.status is VoiceAuthenticationStatus.REJECTED
    assert "not yet valid" in result.reason


def test_authentication_service_does_not_authorize_execution() -> None:
    now = datetime.now(UTC)
    request = make_request(now=now)
    service = VoiceAuthenticationService(
        verifier=DeterministicVoiceAuthenticationVerifier(),
        clock=lambda: now + timedelta(seconds=1),
    )

    result = service.authenticate(
        request=request,
        observation=make_observation(),
    )

    assert not hasattr(result, "authorization_granted")
    assert not hasattr(result, "capability_id")
    assert not hasattr(result, "execution_authority")
