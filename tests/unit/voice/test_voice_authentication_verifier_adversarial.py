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


def make_request() -> VoiceAuthenticationRequest:
    requested_at = datetime.now(UTC)
    return VoiceAuthenticationRequest(
        request_id="adversarial-request",
        session_id="adversarial-session",
        claimed_principal_id="principal-a",
        method=VoiceAuthenticationMethod.SPEAKER_VERIFICATION,
        correlation_id="adversarial-correlation",
        idempotency_key="adversarial-idempotency",
        requested_at=requested_at,
        expires_at=requested_at + timedelta(minutes=1),
    )


def make_observation(
    *,
    matched_principal_id: str = "principal-a",
    assurance: VoiceAuthenticationAssurance = VoiceAuthenticationAssurance.HIGH,
    method: VoiceAuthenticationMethod = VoiceAuthenticationMethod.SPEAKER_VERIFICATION,
) -> VoiceVerificationObservation:
    return VoiceVerificationObservation(
        matched_principal_id=matched_principal_id,
        method=method,
        assurance=assurance,
        provider_id="attacker-controlled-provider-label",
        evidence_id="adversarial-evidence",
        evidence_reference="opaque://adversarial/evidence",
        observed_at=datetime.now(UTC),
    )


def test_future_dated_evaluation_is_rejected_by_request_expiry() -> None:
    request = make_request()
    verifier = DeterministicVoiceAuthenticationVerifier()

    result = verifier.verify(
        request=request,
        observation=make_observation(),
        evaluated_at=request.expires_at + timedelta(microseconds=1),
    )

    assert result.status is VoiceAuthenticationStatus.EXPIRED
    assert result.authenticated_principal_id is None


def test_principal_substitution_cannot_produce_verified() -> None:
    request = make_request()
    verifier = DeterministicVoiceAuthenticationVerifier()

    result = verifier.verify(
        request=request,
        observation=make_observation(
            matched_principal_id="principal-attacker",
        ),
        evaluated_at=request.requested_at + timedelta(seconds=1),
    )

    assert result.status is VoiceAuthenticationStatus.REJECTED
    assert result.authenticated_principal_id is None


def test_none_assurance_cannot_escalate_to_verified() -> None:
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


def test_current_method_contract_is_supported() -> None:
    request = make_request()
    verifier = DeterministicVoiceAuthenticationVerifier()

    result = verifier.verify(
        request=request,
        observation=make_observation(),
        evaluated_at=request.requested_at + timedelta(seconds=1),
    )

    assert request.method is VoiceAuthenticationMethod.SPEAKER_VERIFICATION
    assert result.status is VoiceAuthenticationStatus.VERIFIED


def test_authentication_result_does_not_authorize_execution() -> None:
    request = make_request()
    verifier = DeterministicVoiceAuthenticationVerifier()

    result = verifier.verify(
        request=request,
        observation=make_observation(),
        evaluated_at=request.requested_at + timedelta(seconds=1),
    )

    assert result.status is VoiceAuthenticationStatus.VERIFIED
    assert not hasattr(result, "authorization_granted")
    assert not hasattr(result, "capability_id")
    assert not hasattr(result, "execution_authority")


def test_provider_label_cannot_be_used_as_principal() -> None:
    request = make_request()
    verifier = DeterministicVoiceAuthenticationVerifier()

    result = verifier.verify(
        request=request,
        observation=make_observation(),
        evaluated_at=request.requested_at + timedelta(seconds=1),
    )

    assert result.authenticated_principal_id == "principal-a"
    assert result.authenticated_principal_id != (
        "attacker-controlled-provider-label"
    )


def test_invalid_extra_observation_fields_are_rejected() -> None:
    payload: dict[str, object] = {
        "matched_principal_id": "principal-a",
        "method": VoiceAuthenticationMethod.SPEAKER_VERIFICATION,
        "assurance": VoiceAuthenticationAssurance.HIGH,
        "provider_id": "provider",
        "evidence_id": "evidence",
        "evidence_reference": "opaque://reference",
        "observed_at": datetime.now(UTC),
        "authorization_granted": True,
    }

    with pytest.raises(ValidationError):
        VoiceVerificationObservation.model_validate(payload)


def test_blank_provider_id_is_rejected() -> None:
    with pytest.raises(ValidationError):
        VoiceVerificationObservation(
            matched_principal_id="principal-a",
            method=VoiceAuthenticationMethod.SPEAKER_VERIFICATION,
            assurance=VoiceAuthenticationAssurance.HIGH,
            provider_id="   ",
            evidence_id="evidence",
            evidence_reference="opaque://reference",
            observed_at=datetime.now(UTC),
        )


def test_blank_evidence_reference_is_rejected() -> None:
    with pytest.raises(ValidationError):
        VoiceVerificationObservation(
            matched_principal_id="principal-a",
            method=VoiceAuthenticationMethod.SPEAKER_VERIFICATION,
            assurance=VoiceAuthenticationAssurance.HIGH,
            provider_id="provider",
            evidence_id="evidence",
            evidence_reference="   ",
            observed_at=datetime.now(UTC),
        )
