from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lyrion.voice.authentication import (
    DeterministicVoiceAuthenticationVerifier,
    VoiceAuthenticationAssurance,
    VoiceAuthenticationMethod,
    VoiceAuthenticationRequest,
    VoiceAuthenticationStatus,
    VoiceVerificationObservation,
)


def make_request(
    *,
    requested_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> VoiceAuthenticationRequest:
    requested = requested_at or datetime.now(UTC)
    expiry = expires_at or (requested + timedelta(minutes=1))

    return VoiceAuthenticationRequest(
        request_id="auth-req-1",
        session_id="session-1",
        claimed_principal_id="principal-1",
        method=VoiceAuthenticationMethod.SPEAKER_VERIFICATION,
        correlation_id="corr-1",
        idempotency_key="idem-1",
        requested_at=requested,
        expires_at=expiry,
    )


def make_observation(
    *,
    matched_principal_id: str = "principal-1",
    assurance: VoiceAuthenticationAssurance = VoiceAuthenticationAssurance.HIGH,
    method: VoiceAuthenticationMethod = VoiceAuthenticationMethod.SPEAKER_VERIFICATION,
    provider_id: str = "provider-1",
    evidence_id: str = "evidence-1",
    evidence_reference: str = "opaque:evidence:1",
    observed_at: datetime | None = None,
) -> VoiceVerificationObservation:
    return VoiceVerificationObservation(
        matched_principal_id=matched_principal_id,
        method=method,
        assurance=assurance,
        provider_id=provider_id,
        evidence_id=evidence_id,
        evidence_reference=evidence_reference,
        observed_at=observed_at or datetime.now(UTC),
    )


def test_matching_observation_returns_verified() -> None:
    request = make_request()
    verifier = DeterministicVoiceAuthenticationVerifier()

    result = verifier.verify(
        request=request,
        observation=make_observation(),
        evaluated_at=request.requested_at + timedelta(seconds=1),
    )

    assert result.status is VoiceAuthenticationStatus.VERIFIED
    assert result.assurance is VoiceAuthenticationAssurance.HIGH
    assert result.authenticated_principal_id == request.claimed_principal_id
    assert result.evidence is not None


def test_principal_mismatch_returns_rejected() -> None:
    request = make_request()
    verifier = DeterministicVoiceAuthenticationVerifier()

    result = verifier.verify(
        request=request,
        observation=make_observation(
            matched_principal_id="principal-2",
        ),
        evaluated_at=request.requested_at + timedelta(seconds=1),
    )

    assert result.status is VoiceAuthenticationStatus.REJECTED
    assert result.assurance is VoiceAuthenticationAssurance.NONE
    assert result.authenticated_principal_id is None
    assert result.evidence is None


def test_expired_request_returns_expired() -> None:
    requested_at = datetime.now(UTC)
    request = make_request(
        requested_at=requested_at,
        expires_at=requested_at + timedelta(seconds=1),
    )
    verifier = DeterministicVoiceAuthenticationVerifier()

    result = verifier.verify(
        request=request,
        observation=make_observation(),
        evaluated_at=request.expires_at + timedelta(seconds=1),
    )

    assert result.status is VoiceAuthenticationStatus.EXPIRED
    assert result.authenticated_principal_id is None
    assert result.evidence is None


def test_evaluation_before_request_fails_closed() -> None:
    request = make_request()
    verifier = DeterministicVoiceAuthenticationVerifier()

    with pytest.raises(ValueError, match="evaluation cannot precede"):
        verifier.verify(
            request=request,
            observation=make_observation(),
            evaluated_at=request.requested_at - timedelta(seconds=1),
        )


def test_none_assurance_is_rejected() -> None:
    request = make_request()
    verifier = DeterministicVoiceAuthenticationVerifier()

    result = verifier.verify(
        request=request,
        observation=make_observation(
            assurance=VoiceAuthenticationAssurance.NONE,
        ),
        evaluated_at=request.requested_at + timedelta(seconds=1),
    )

    assert result.status is VoiceAuthenticationStatus.REJECTED
    assert result.assurance is VoiceAuthenticationAssurance.NONE
    assert result.authenticated_principal_id is None


def test_evidence_is_propagated_as_opaque_reference() -> None:
    request = make_request()
    verifier = DeterministicVoiceAuthenticationVerifier()

    result = verifier.verify(
        request=request,
        observation=make_observation(
            evidence_id="ev-123",
            evidence_reference="opaque://verification/ev-123",
            provider_id="provider-x",
        ),
        evaluated_at=request.requested_at + timedelta(seconds=1),
    )

    assert result.evidence is not None
    assert result.evidence.evidence_id == "ev-123"
    assert result.evidence.reference == "opaque://verification/ev-123"
    assert result.evidence.provider_id == "provider-x"


def test_provider_identity_never_becomes_authenticated_identity() -> None:
    request = make_request()
    verifier = DeterministicVoiceAuthenticationVerifier()

    result = verifier.verify(
        request=request,
        observation=make_observation(
            provider_id="provider-trusted-looking",
        ),
        evaluated_at=request.requested_at + timedelta(seconds=1),
    )

    assert result.status is VoiceAuthenticationStatus.VERIFIED
    assert result.authenticated_principal_id == "principal-1"
    assert result.evidence is not None
    assert result.authenticated_principal_id != result.evidence.provider_id


def test_request_correlation_is_preserved() -> None:
    request = make_request()
    verifier = DeterministicVoiceAuthenticationVerifier()

    result = verifier.verify(
        request=request,
        observation=make_observation(),
        evaluated_at=request.requested_at + timedelta(seconds=1),
    )

    assert result.request_id == request.request_id
    assert result.session_id == request.session_id
    assert result.correlation_id == request.correlation_id
    assert result.idempotency_key == request.idempotency_key


def test_verified_expiry_is_bounded_by_request() -> None:
    request = make_request()
    verifier = DeterministicVoiceAuthenticationVerifier()

    result = verifier.verify(
        request=request,
        observation=make_observation(),
        evaluated_at=request.requested_at + timedelta(seconds=1),
    )

    assert result.expires_at == request.expires_at


def test_observation_is_immutable() -> None:
    observation = make_observation()

    with pytest.raises(ValidationError):
        observation.provider_id = "changed"


def test_verifier_protocol_is_structural() -> None:
    verifier = DeterministicVoiceAuthenticationVerifier()

    assert hasattr(verifier, "verify")


def test_observation_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValidationError):
        make_observation(
            observed_at=datetime.now(),
        )
