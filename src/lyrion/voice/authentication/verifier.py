"""Provider-neutral voice authentication verification boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lyrion.voice.authentication.contracts import (
    VoiceAuthenticationAssurance,
    VoiceAuthenticationEvidence,
    VoiceAuthenticationMethod,
    VoiceAuthenticationRequest,
    VoiceAuthenticationResult,
    VoiceAuthenticationStatus,
)


class VoiceVerificationObservation(BaseModel):
    """Normalized, untrusted observation produced by a verification adapter.

    This object is evidence input to the authentication boundary. It is not
    itself an authorization decision and does not grant execution authority.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    matched_principal_id: str = Field(min_length=1, max_length=500)
    method: VoiceAuthenticationMethod
    assurance: VoiceAuthenticationAssurance
    provider_id: str = Field(min_length=1, max_length=200)
    evidence_id: str = Field(min_length=1, max_length=500)
    evidence_reference: str = Field(min_length=1, max_length=500)
    observed_at: datetime

    @field_validator(
        "matched_principal_id",
        "provider_id",
        "evidence_id",
        "evidence_reference",
    )
    @classmethod
    def require_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("verification observation fields must not be blank")
        return value

    @field_validator("observed_at")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observation timestamp must be timezone-aware")
        return value


class VoiceAuthenticationVerifier(Protocol):
    """Provider-neutral authentication verifier contract."""

    def verify(
        self,
        *,
        request: VoiceAuthenticationRequest,
        observation: VoiceVerificationObservation,
        evaluated_at: datetime,
    ) -> VoiceAuthenticationResult:
        """Validate an observation against an authentication request."""


class DeterministicVoiceAuthenticationVerifier:
    """Deterministic reference verifier for the provider-neutral boundary.

    This implementation deliberately performs no biometric computation.
    Provider-specific verification happens outside this boundary and supplies
    a normalized observation.
    """

    def verify(
        self,
        *,
        request: VoiceAuthenticationRequest,
        observation: VoiceVerificationObservation,
        evaluated_at: datetime,
    ) -> VoiceAuthenticationResult:
        evaluated_at_utc = evaluated_at.astimezone(UTC)

        if observation.method is not request.method:
            return VoiceAuthenticationResult.from_request(
                request=request,
                status=VoiceAuthenticationStatus.REJECTED,
                assurance=VoiceAuthenticationAssurance.NONE,
                authenticated_principal_id=None,
                evidence=None,
                evaluated_at=evaluated_at_utc,
                expires_at=None,
                reason="Verification method does not match the request.",
            )

        if evaluated_at_utc < request.requested_at.astimezone(UTC):
            raise ValueError("evaluation cannot precede authentication request")

        if evaluated_at_utc > request.expires_at.astimezone(UTC):
            return VoiceAuthenticationResult.from_request(
                request=request,
                status=VoiceAuthenticationStatus.EXPIRED,
                assurance=VoiceAuthenticationAssurance.NONE,
                authenticated_principal_id=None,
                evidence=None,
                evaluated_at=evaluated_at_utc,
                expires_at=None,
                reason="Authentication request has expired.",
            )

        if observation.matched_principal_id != request.claimed_principal_id:
            return VoiceAuthenticationResult.from_request(
                request=request,
                status=VoiceAuthenticationStatus.REJECTED,
                assurance=VoiceAuthenticationAssurance.NONE,
                authenticated_principal_id=None,
                evidence=None,
                evaluated_at=evaluated_at_utc,
                expires_at=None,
                reason="Verified principal does not match the claimed principal.",
            )

        if observation.assurance is VoiceAuthenticationAssurance.NONE:
            return VoiceAuthenticationResult.from_request(
                request=request,
                status=VoiceAuthenticationStatus.REJECTED,
                assurance=VoiceAuthenticationAssurance.NONE,
                authenticated_principal_id=None,
                evidence=None,
                evaluated_at=evaluated_at_utc,
                expires_at=None,
                reason="Verification observation has no authentication assurance.",
            )

        evidence = VoiceAuthenticationEvidence(
            evidence_id=observation.evidence_id,
            method=observation.method,
            assurance=observation.assurance,
            provider_id=observation.provider_id,
            reference=observation.evidence_reference,
            observed_at=observation.observed_at.astimezone(UTC),
        )

        return VoiceAuthenticationResult.verified(
            request=request,
            authenticated_principal_id=observation.matched_principal_id,
            evidence=evidence,
            evaluated_at=evaluated_at_utc,
            expires_at=request.expires_at.astimezone(UTC),
            reason="Voice authentication observation accepted.",
        )
