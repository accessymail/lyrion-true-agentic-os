from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from lyrion.security.replay import ReplayGuard
from lyrion.voice.authentication import (
    DeterministicVoiceAuthenticationVerifier,
    VoiceAuthenticationAssurance,
    VoiceAuthenticationMethod,
    VoiceAuthenticationRequest,
    VoiceAuthenticationResult,
    VoiceAuthenticationService,
    VoiceAuthenticationStatus,
    VoiceVerificationObservation,
)


def make_request(
    *,
    request_id: str = "request-1",
    session_id: str = "session-1",
    principal_id: str = "principal-1",
    correlation_id: str = "corr-1",
    idempotency_key: str = "idem-1",
    requested_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> VoiceAuthenticationRequest:
    requested = requested_at or datetime.now(UTC)
    expiry = expires_at or (requested + timedelta(minutes=1))

    return VoiceAuthenticationRequest(
        request_id=request_id,
        session_id=session_id,
        claimed_principal_id=principal_id,
        method=VoiceAuthenticationMethod.SPEAKER_VERIFICATION,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        requested_at=requested,
        expires_at=expiry,
    )


def make_observation(
    *,
    matched_principal_id: str = "principal-1",
    provider_id: str = "provider-1",
    assurance: VoiceAuthenticationAssurance = VoiceAuthenticationAssurance.HIGH,
) -> VoiceVerificationObservation:
    return VoiceVerificationObservation(
        matched_principal_id=matched_principal_id,
        method=VoiceAuthenticationMethod.SPEAKER_VERIFICATION,
        assurance=assurance,
        provider_id=provider_id,
        evidence_id="evidence-1",
        evidence_reference="opaque:evidence:1",
        observed_at=datetime.now(UTC),
    )


class ExplodingVerifier:
    def verify(
        self,
        *,
        request: VoiceAuthenticationRequest,
        observation: VoiceVerificationObservation,
        evaluated_at: datetime,
    ) -> VoiceAuthenticationResult:
        raise RuntimeError("simulated verifier failure")


class RecordingVerifier:
    def __init__(self) -> None:
        self.calls = 0

    def verify(
        self,
        *,
        request: VoiceAuthenticationRequest,
        observation: VoiceVerificationObservation,
        evaluated_at: datetime,
    ) -> VoiceAuthenticationResult:
        self.calls += 1
        return DeterministicVoiceAuthenticationVerifier().verify(
            request=request,
            observation=observation,
            evaluated_at=evaluated_at,
        )


def test_concurrent_same_idempotency_key_allows_only_one_verification() -> None:
    now = datetime.now(UTC)
    request = make_request(requested_at=now)
    observation = make_observation()
    replay_guard = ReplayGuard()
    verifier = RecordingVerifier()

    service = VoiceAuthenticationService(
        verifier=verifier,
        replay_guard=replay_guard,
        clock=lambda: now + timedelta(seconds=1),
    )

    def invoke() -> VoiceAuthenticationStatus:
        return service.authenticate(
            request=request,
            observation=observation,
        ).status

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: invoke(), range(8)))

    assert results.count(VoiceAuthenticationStatus.VERIFIED) == 1
    assert results.count(VoiceAuthenticationStatus.REJECTED) == 7
    assert verifier.calls == 1


def test_verifier_failure_consumes_idempotency_key_fail_closed() -> None:
    now = datetime.now(UTC)
    request = make_request(requested_at=now)
    replay_guard = ReplayGuard()

    failing_service = VoiceAuthenticationService(
        verifier=ExplodingVerifier(),
        replay_guard=replay_guard,
        clock=lambda: now + timedelta(seconds=1),
    )

    first = failing_service.authenticate(
        request=request,
        observation=make_observation(),
    )

    assert first.status is VoiceAuthenticationStatus.REJECTED
    assert replay_guard.seen(request.idempotency_key) is True

    healthy_service = VoiceAuthenticationService(
        verifier=DeterministicVoiceAuthenticationVerifier(),
        replay_guard=replay_guard,
        clock=lambda: now + timedelta(seconds=1),
    )

    second = healthy_service.authenticate(
        request=request,
        observation=make_observation(),
    )

    assert second.status is VoiceAuthenticationStatus.REJECTED
    assert second.authenticated_principal_id is None
    assert "Replay" in second.reason


def test_different_session_is_not_allowed_to_reuse_same_request_key() -> None:
    now = datetime.now(UTC)
    replay_guard = ReplayGuard()

    first_request = make_request(
        request_id="request-1",
        session_id="session-1",
        idempotency_key="same-key",
        requested_at=now,
    )
    second_request = make_request(
        request_id="request-2",
        session_id="session-2",
        idempotency_key="same-key",
        requested_at=now,
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
    assert second.authenticated_principal_id is None


def test_different_principal_cannot_reuse_same_idempotency_key() -> None:
    now = datetime.now(UTC)
    replay_guard = ReplayGuard()

    first_request = make_request(
        request_id="request-1",
        principal_id="principal-1",
        idempotency_key="same-key",
        requested_at=now,
    )
    second_request = make_request(
        request_id="request-2",
        principal_id="principal-2",
        idempotency_key="same-key",
        requested_at=now,
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
        observation=make_observation(
            matched_principal_id="principal-2",
        ),
    )

    assert first.status is VoiceAuthenticationStatus.VERIFIED
    assert second.status is VoiceAuthenticationStatus.REJECTED
    assert second.authenticated_principal_id is None


def test_observation_principal_substitution_is_rejected() -> None:
    now = datetime.now(UTC)
    request = make_request(requested_at=now)

    service = VoiceAuthenticationService(
        verifier=DeterministicVoiceAuthenticationVerifier(),
        clock=lambda: now + timedelta(seconds=1),
    )

    result = service.authenticate(
        request=request,
        observation=make_observation(
            matched_principal_id="attacker-principal",
        ),
    )

    assert result.status is VoiceAuthenticationStatus.REJECTED
    assert result.authenticated_principal_id is None
    assert result.evidence is None


def test_observation_provider_identity_cannot_become_principal() -> None:
    now = datetime.now(UTC)
    request = make_request(requested_at=now)

    service = VoiceAuthenticationService(
        verifier=DeterministicVoiceAuthenticationVerifier(),
        clock=lambda: now + timedelta(seconds=1),
    )

    result = service.authenticate(
        request=request,
        observation=make_observation(
            provider_id="principal-1",
        ),
    )

    assert result.status is VoiceAuthenticationStatus.VERIFIED
    assert result.authenticated_principal_id == "principal-1"
    assert result.evidence is not None
    assert result.evidence.provider_id == "principal-1"


def test_service_does_not_create_authorization_fields() -> None:
    now = datetime.now(UTC)
    request = make_request(requested_at=now)

    service = VoiceAuthenticationService(
        verifier=DeterministicVoiceAuthenticationVerifier(),
        clock=lambda: now + timedelta(seconds=1),
    )

    result = service.authenticate(
        request=request,
        observation=make_observation(),
    )

    assert result.status is VoiceAuthenticationStatus.VERIFIED
    fields = type(result).model_fields
    assert "authorization_granted" not in fields
    assert "capability_id" not in fields
    assert "execution_authority" not in fields
