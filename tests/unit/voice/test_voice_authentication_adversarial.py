from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lyrion.voice.authentication import (
    VoiceAuthenticationAssurance,
    VoiceAuthenticationEvidence,
    VoiceAuthenticationMethod,
    VoiceAuthenticationRequest,
    VoiceAuthenticationResult,
    VoiceAuthenticationStatus,
)


def make_request() -> VoiceAuthenticationRequest:
    requested_at = datetime.now(UTC)
    return VoiceAuthenticationRequest(
        request_id="auth-req-adversarial",
        session_id="session-adversarial",
        claimed_principal_id="principal-a",
        method=VoiceAuthenticationMethod.SPEAKER_VERIFICATION,
        correlation_id="corr-adversarial",
        idempotency_key="idem-adversarial",
        requested_at=requested_at,
        expires_at=requested_at + timedelta(minutes=1),
    )


def make_evidence(
    assurance: VoiceAuthenticationAssurance,
) -> VoiceAuthenticationEvidence:
    return VoiceAuthenticationEvidence(
        evidence_id="evidence-adversarial",
        method=VoiceAuthenticationMethod.SPEAKER_VERIFICATION,
        assurance=assurance,
        provider_id="untrusted-provider",
        reference="opaque:evidence:adversarial",
        observed_at=datetime.now(UTC),
    )


@pytest.mark.parametrize(
    "status",
    [
        VoiceAuthenticationStatus.UNKNOWN,
        VoiceAuthenticationStatus.PENDING,
        VoiceAuthenticationStatus.REJECTED,
        VoiceAuthenticationStatus.EXPIRED,
        VoiceAuthenticationStatus.REVOKED,
        VoiceAuthenticationStatus.STEP_UP_REQUIRED,
    ],
)
def test_non_verified_states_cannot_smuggle_identity(status: VoiceAuthenticationStatus,) -> None:
    request = make_request()

    with pytest.raises(ValidationError):
        VoiceAuthenticationResult.from_request(
            request=request,
            status=status,
            assurance=VoiceAuthenticationAssurance.NONE,
            authenticated_principal_id="principal-a",
            evidence=None,
            evaluated_at=request.requested_at,
            expires_at=None,
            reason="adversarial",
        )


def test_verified_result_cannot_use_none_assurance() -> None:
    request = make_request()
    evidence = make_evidence(VoiceAuthenticationAssurance.NONE)

    with pytest.raises(ValidationError):
        VoiceAuthenticationResult.verified(
            request=request,
            authenticated_principal_id=request.claimed_principal_id,
            evidence=evidence,
            evaluated_at=request.requested_at,
            expires_at=request.expires_at,
            reason="adversarial",
        )


def test_verified_result_cannot_authenticate_different_principal() -> None:
    request = make_request()
    evidence = make_evidence(VoiceAuthenticationAssurance.HIGH)

    with pytest.raises(ValidationError):
        VoiceAuthenticationResult.verified(
            request=request,
            authenticated_principal_id="principal-b",
            evidence=evidence,
            evaluated_at=request.requested_at,
            expires_at=request.expires_at,
            reason="adversarial",
        )


def test_verified_result_cannot_expire_after_request() -> None:
    request = make_request()
    evidence = make_evidence(VoiceAuthenticationAssurance.HIGH)

    with pytest.raises(ValueError, match="cannot exceed request expiry"):
        VoiceAuthenticationResult.verified(
            request=request,
            authenticated_principal_id=request.claimed_principal_id,
            evidence=evidence,
            evaluated_at=request.requested_at,
            expires_at=request.expires_at + timedelta(hours=1),
            reason="adversarial",
        )


def test_result_is_immutable() -> None:
    request = make_request()
    evidence = make_evidence(VoiceAuthenticationAssurance.HIGH)

    result = VoiceAuthenticationResult.verified(
        request=request,
        authenticated_principal_id=request.claimed_principal_id,
        evidence=evidence,
        evaluated_at=request.requested_at,
        expires_at=request.expires_at,
        reason="verified",
    )

    with pytest.raises(ValidationError):
        result.status = VoiceAuthenticationStatus.REJECTED


def test_provider_identity_is_not_authenticated_principal() -> None:
    request = make_request()
    evidence = make_evidence(VoiceAuthenticationAssurance.HIGH)

    result = VoiceAuthenticationResult.verified(
        request=request,
        authenticated_principal_id=request.claimed_principal_id,
        evidence=evidence,
        evaluated_at=request.requested_at,
        expires_at=request.expires_at,
        reason="provider evidence accepted",
    )

    assert result.authenticated_principal_id != evidence.provider_id


def test_blank_idempotency_key_is_rejected() -> None:
    requested_at = datetime.now(UTC)

    with pytest.raises(ValidationError):
        VoiceAuthenticationRequest(
            request_id="req",
            session_id="session",
            claimed_principal_id="principal",
            method=VoiceAuthenticationMethod.SPEAKER_VERIFICATION,
            correlation_id="corr",
            idempotency_key="   ",
            requested_at=requested_at,
            expires_at=requested_at + timedelta(minutes=1),
        )


def test_blank_correlation_id_is_rejected() -> None:
    requested_at = datetime.now(UTC)

    with pytest.raises(ValidationError):
        VoiceAuthenticationRequest(
            request_id="req",
            session_id="session",
            claimed_principal_id="principal",
            method=VoiceAuthenticationMethod.SPEAKER_VERIFICATION,
            correlation_id="   ",
            idempotency_key="idem",
            requested_at=requested_at,
            expires_at=requested_at + timedelta(minutes=1),
        )
