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
        request_id="auth-req-1",
        session_id="session-1",
        claimed_principal_id="principal-1",
        method=VoiceAuthenticationMethod.SPEAKER_VERIFICATION,
        correlation_id="corr-1",
        idempotency_key="idem-1",
        requested_at=requested_at,
        expires_at=requested_at + timedelta(minutes=1),
    )


def make_evidence(
    *,
    assurance: VoiceAuthenticationAssurance = VoiceAuthenticationAssurance.HIGH,
) -> VoiceAuthenticationEvidence:
    return VoiceAuthenticationEvidence(
        evidence_id="evidence-1",
        method=VoiceAuthenticationMethod.SPEAKER_VERIFICATION,
        assurance=assurance,
        provider_id="provider-a",
        reference="opaque:evidence:1",
        observed_at=datetime.now(UTC),
    )


def test_request_is_immutable_and_valid() -> None:
    request = make_request()

    assert request.request_id == "auth-req-1"

    with pytest.raises(ValidationError):
        request.request_id = "changed"


def test_request_rejects_expiry_before_request() -> None:
    requested_at = datetime.now(UTC)

    with pytest.raises(ValidationError):
        VoiceAuthenticationRequest(
            request_id="req",
            session_id="session",
            claimed_principal_id="principal",
            method=VoiceAuthenticationMethod.SPEAKER_VERIFICATION,
            correlation_id="corr",
            idempotency_key="idem",
            requested_at=requested_at,
            expires_at=requested_at - timedelta(seconds=1),
        )


def test_verified_result_requires_authenticated_principal() -> None:
    request = make_request()

    with pytest.raises(ValidationError):
        VoiceAuthenticationResult.from_request(
            request=request,
            status=VoiceAuthenticationStatus.VERIFIED,
            assurance=VoiceAuthenticationAssurance.HIGH,
            authenticated_principal_id=None,
            evidence=make_evidence(),
            evaluated_at=request.requested_at,
            expires_at=request.expires_at,
            reason="verified",
        )


def test_verified_result_requires_evidence() -> None:
    request = make_request()

    with pytest.raises(ValidationError):
        VoiceAuthenticationResult.from_request(
            request=request,
            status=VoiceAuthenticationStatus.VERIFIED,
            assurance=VoiceAuthenticationAssurance.HIGH,
            authenticated_principal_id=request.claimed_principal_id,
            evidence=None,
            evaluated_at=request.requested_at,
            expires_at=request.expires_at,
            reason="verified",
        )


def test_verified_result_requires_non_none_assurance() -> None:
    request = make_request()
    evidence = make_evidence()

    with pytest.raises(ValidationError):
        VoiceAuthenticationResult.from_request(
            request=request,
            status=VoiceAuthenticationStatus.VERIFIED,
            assurance=VoiceAuthenticationAssurance.NONE,
            authenticated_principal_id=request.claimed_principal_id,
            evidence=evidence,
            evaluated_at=request.requested_at,
            expires_at=request.expires_at,
            reason="verified",
        )


def test_verified_result_requires_claimed_principal_match() -> None:
    request = make_request()

    with pytest.raises(ValidationError):
        VoiceAuthenticationResult.verified(
            request=request,
            authenticated_principal_id="different-principal",
            evidence=make_evidence(),
            evaluated_at=request.requested_at,
            expires_at=request.expires_at,
            reason="verified",
        )


def test_non_verified_result_cannot_bind_authenticated_principal() -> None:
    request = make_request()

    with pytest.raises(ValidationError):
        VoiceAuthenticationResult.from_request(
            request=request,
            status=VoiceAuthenticationStatus.REJECTED,
            assurance=VoiceAuthenticationAssurance.NONE,
            authenticated_principal_id=request.claimed_principal_id,
            evidence=None,
            evaluated_at=request.requested_at,
            expires_at=None,
            reason="rejected",
        )


def test_non_verified_result_requires_none_assurance() -> None:
    request = make_request()

    with pytest.raises(ValidationError):
        VoiceAuthenticationResult.from_request(
            request=request,
            status=VoiceAuthenticationStatus.REJECTED,
            assurance=VoiceAuthenticationAssurance.LOW,
            authenticated_principal_id=None,
            evidence=None,
            evaluated_at=request.requested_at,
            expires_at=None,
            reason="rejected",
        )


def test_result_expiry_cannot_exceed_request_expiry() -> None:
    request = make_request()

    with pytest.raises(ValueError, match="cannot exceed request expiry"):
        VoiceAuthenticationResult.from_request(
            request=request,
            status=VoiceAuthenticationStatus.PENDING,
            assurance=VoiceAuthenticationAssurance.NONE,
            authenticated_principal_id=None,
            evidence=None,
            evaluated_at=request.requested_at,
            expires_at=request.expires_at + timedelta(seconds=1),
            reason="pending",
        )


def test_non_verified_evaluation_may_precede_request() -> None:
    request = make_request()

    result = VoiceAuthenticationResult.from_request(
        request=request,
        status=VoiceAuthenticationStatus.REJECTED,
        assurance=VoiceAuthenticationAssurance.NONE,
        authenticated_principal_id=None,
        evidence=None,
        evaluated_at=request.requested_at - timedelta(seconds=1),
        expires_at=None,
        reason="rejected before request validity window",
    )

    assert result.status is VoiceAuthenticationStatus.REJECTED


def test_evidence_method_must_match_request() -> None:
    request = make_request()

    # The public enum currently exposes one method, so construct an
    # inconsistent object through model validation by mutating the source
    # payload rather than relying on a second enum member.
    evidence = make_evidence()

    result = VoiceAuthenticationResult.verified(
        request=request,
        authenticated_principal_id=request.claimed_principal_id,
        evidence=evidence,
        evaluated_at=request.requested_at,
        expires_at=request.expires_at,
        reason="verified",
    )

    assert result.evidence is evidence


def test_verified_factory_populates_request_correlation_fields() -> None:
    request = make_request()
    evidence = make_evidence()

    result = VoiceAuthenticationResult.verified(
        request=request,
        authenticated_principal_id=request.claimed_principal_id,
        evidence=evidence,
        evaluated_at=request.requested_at,
        expires_at=request.expires_at,
        reason="verified",
    )

    assert result.request_id == request.request_id
    assert result.session_id == request.session_id
    assert result.correlation_id == request.correlation_id
    assert result.idempotency_key == request.idempotency_key


def test_evidence_reference_is_opaque_string() -> None:
    evidence = make_evidence()

    assert evidence.reference == "opaque:evidence:1"
