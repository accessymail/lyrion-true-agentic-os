"""Orchestration service for the voice authentication boundary."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from lyrion.security.replay import ReplayGuard
from lyrion.voice.authentication.contracts import (
    VoiceAuthenticationAssurance,
    VoiceAuthenticationRequest,
    VoiceAuthenticationResult,
    VoiceAuthenticationStatus,
)
from lyrion.voice.authentication.verifier import (
    VoiceAuthenticationVerifier,
    VoiceVerificationObservation,
)


class AuthenticationClock(Protocol):
    """Clock boundary used by the authentication service."""

    def __call__(self) -> datetime:
        """Return the current timezone-aware UTC time."""


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


class VoiceAuthenticationService:
    """Controlled orchestration boundary for voice authentication.

    This service does not authorize capabilities and does not execute actions.
    It coordinates request validity, replay protection, and verification.
    """

    def __init__(
        self,
        *,
        verifier: VoiceAuthenticationVerifier,
        replay_guard: ReplayGuard | None = None,
        clock: AuthenticationClock = utc_now,
    ) -> None:
        self._verifier = verifier
        self._replay_guard = replay_guard or ReplayGuard()
        self._clock = clock

    def authenticate(
        self,
        *,
        request: VoiceAuthenticationRequest,
        observation: VoiceVerificationObservation,
    ) -> VoiceAuthenticationResult:
        """Authenticate one request through the provider-neutral boundary."""
        now = self._clock().astimezone(UTC)

        request_expires_at = request.expires_at.astimezone(UTC)
        request_requested_at = request.requested_at.astimezone(UTC)

        if now < request_requested_at:
            return VoiceAuthenticationResult.from_request(
                request=request,
                status=VoiceAuthenticationStatus.REJECTED,
                assurance=VoiceAuthenticationAssurance.NONE,
                authenticated_principal_id=None,
                evidence=None,
                evaluated_at=now,
                expires_at=None,
                reason="Authentication request is not yet valid.",
            )

        if now > request_expires_at:
            return VoiceAuthenticationResult.from_request(
                request=request,
                status=VoiceAuthenticationStatus.EXPIRED,
                assurance=VoiceAuthenticationAssurance.NONE,
                authenticated_principal_id=None,
                evidence=None,
                evaluated_at=now,
                expires_at=None,
                reason="Authentication request has expired.",
            )

        accepted = self._replay_guard.check_and_record(
            idempotency_key=request.idempotency_key,
            request_id=request.request_id,
        )

        if not accepted:
            original_request_id = self._replay_guard.request_for(
                request.idempotency_key
            )

            if original_request_id is None:
                reason = "Authentication Replay detected."
            else:
                reason = (
                    "Authentication Replay detected for idempotency key "
                    f"associated with request {original_request_id}."
                )

            return VoiceAuthenticationResult.from_request(
                request=request,
                status=VoiceAuthenticationStatus.REJECTED,
                assurance=VoiceAuthenticationAssurance.NONE,
                authenticated_principal_id=None,
                evidence=None,
                evaluated_at=now,
                expires_at=None,
                reason=reason,
            )

        try:
            return self._verifier.verify(
                request=request,
                observation=observation,
                evaluated_at=now,
            )
        except Exception as exc:
            return VoiceAuthenticationResult.from_request(
                request=request,
                status=VoiceAuthenticationStatus.REJECTED,
                assurance=VoiceAuthenticationAssurance.NONE,
                authenticated_principal_id=None,
                evidence=None,
                evaluated_at=now,
                expires_at=None,
                reason=f"Authentication verification failed closed: {type(exc).__name__}.",
            )
