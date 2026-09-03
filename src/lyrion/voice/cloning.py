"""Provider-neutral voice-cloning domain contracts.

Milestone: 19.4.3 — Voice Cloning

This module defines the Lyrion control-plane contract for voice cloning.
Provider-specific implementations must remain behind the provider boundary.

Security boundaries:
- Consent evidence is mandatory.
- A cloned voice is never an authentication or authorization credential.
- Provider APIs remain behind an adapter/provider boundary.
- Source and output values are references, not raw audio storage.
- Clone lifecycle transitions are explicit and validated.
- Generated voice assets retain provenance metadata.
- Provider-returned identity must match the requested identity.
- Clone duration is bounded.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class VoiceCloneStatus(StrEnum):
    """Lifecycle state of a voice-cloning request."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    REVOKED = "revoked"


class VoiceClonePurpose(StrEnum):
    """Permitted high-level purposes for a clone."""

    PERSONAL_ASSISTANT = "personal_assistant"
    ACCESSIBILITY = "accessibility"
    CREATIVE = "creative"
    TESTING = "testing"


class VoiceCloneOutputFormat(StrEnum):
    """Provider-neutral output formats exposed by the control plane."""

    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    PCM = "pcm"


@dataclass(frozen=True, slots=True)
class VoiceCloneConsent:
    """Immutable consent evidence associated with a cloning request."""

    consent_id: UUID
    subject_identity_id: UUID
    granted_at: datetime
    purpose: VoiceClonePurpose
    terms_version: str
    evidence_reference: str

    def __post_init__(self) -> None:
        if self.granted_at.tzinfo is None:
            raise ValueError("granted_at must be timezone-aware")
        if not self.terms_version.strip():
            raise ValueError("terms_version must not be blank")
        if not self.evidence_reference.strip():
            raise ValueError("evidence_reference must not be blank")


@dataclass(frozen=True, slots=True)
class VoiceCloneSource:
    """Reference to an approved source voice representation.

    Raw audio must not be embedded in this domain object.
    """

    representation_id: UUID
    source_reference: str

    def __post_init__(self) -> None:
        if not self.source_reference.strip():
            raise ValueError("source_reference must not be blank")


@dataclass(frozen=True, slots=True)
class VoiceCloneRequest:
    """Immutable provider-neutral voice-cloning request.

    The UUID-oriented fields support the Lyrion domain/control-plane model.
    The string/reference-oriented fields expose the existing service contract
    used by the repository's 19.4.3 boundary tests.
    """

    identity_id: str | None = None
    source_representation_ref: str | None = None
    consent_evidence_ref: str | None = None
    locale: str | None = None
    output_format: VoiceCloneOutputFormat = VoiceCloneOutputFormat.WAV
    max_duration_seconds: int = 60
    provenance: str | None = None

    request_id: UUID | None = None
    subject_identity_id: UUID | None = None
    profile_id: UUID | None = None
    source: VoiceCloneSource | None = None
    consent: VoiceCloneConsent | None = None
    requested_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.identity_id is None:
            if self.subject_identity_id is None:
                raise ValueError("identity_id must not be blank")
        elif not self.identity_id.strip():
            raise ValueError("identity_id must not be blank")

        source_ref = self.source_representation_ref
        if source_ref is None and self.source is not None:
            source_ref = self.source.source_reference
        if not source_ref or not source_ref.strip():
            raise ValueError("source reference must not be blank")

        consent_ref = self.consent_evidence_ref
        if consent_ref is None and self.consent is not None:
            consent_ref = self.consent.evidence_reference
        if not consent_ref or not consent_ref.strip():
            raise ValueError("consent evidence reference must not be blank")

        if not isinstance(self.output_format, VoiceCloneOutputFormat):
            raise ValueError("output_format must be a VoiceCloneOutputFormat")

        if self.max_duration_seconds <= 0:
            raise ValueError("max_duration_seconds must be greater than zero")

        if self.max_duration_seconds > 300:
            raise ValueError("max_duration_seconds must not exceed 300")

        if self.provenance is None or not self.provenance.strip():
            raise ValueError("provenance must not be blank")

        if self.requested_at is not None and self.requested_at.tzinfo is None:
            raise ValueError("requested_at must be timezone-aware")

        if self.consent is not None:
            if (
                self.subject_identity_id is not None
                and self.subject_identity_id != self.consent.subject_identity_id
            ):
                raise ValueError(
                    "consent subject must match the requested subject identity"
                )

            if self.requested_at is not None and (
                self.requested_at < self.consent.granted_at
            ):
                raise ValueError("requested_at cannot precede consent")


@dataclass(frozen=True, slots=True)
class VoiceCloneResult:
    """Immutable metadata returned by a provider boundary."""

    clone_id: str
    identity_id: str
    representation_ref: str
    provider: str
    output_format: VoiceCloneOutputFormat
    created_at: datetime
    provenance: str
    provider_model: str | None = None

    def __post_init__(self) -> None:
        if not self.clone_id.strip():
            raise ValueError("clone_id must not be blank")
        if not self.identity_id.strip():
            raise ValueError("identity_id must not be blank")
        if not self.representation_ref.strip():
            raise ValueError("representation_ref must not be blank")
        if not self.provider.strip():
            raise ValueError("provider must not be blank")
        if not self.provenance.strip():
            raise ValueError("provenance must not be blank")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")


class VoiceCloneProvider(Protocol):
    """Provider boundary for a voice-cloning implementation."""

    async def clone(self, request: VoiceCloneRequest) -> VoiceCloneResult:
        """Create a clone using a provider-specific implementation."""


class VoiceCloneService:
    """Application service enforcing the provider-neutral clone boundary."""

    def __init__(self, provider: VoiceCloneProvider) -> None:
        self._provider = provider

    async def create_clone(self, request: VoiceCloneRequest) -> VoiceCloneResult:
        """Delegate to the provider and enforce identity integrity."""

        result = await self._provider.clone(request)

        requested_identity = request.identity_id
        if requested_identity is None and request.subject_identity_id is not None:
            requested_identity = str(request.subject_identity_id)

        if requested_identity is None:
            raise ValueError("request identity is required")

        if result.identity_id != requested_identity:
            raise ValueError(
                "provider returned an unexpected identity for the clone request"
            )

        if result.output_format is not request.output_format:
            raise ValueError("provider returned an unexpected output format")

        return result


@dataclass(frozen=True, slots=True)
class VoiceCloneJob:
    """Immutable lifecycle representation for a clone job."""

    request: VoiceCloneRequest
    status: VoiceCloneStatus
    created_at: datetime
    updated_at: datetime
    provider: str | None = None
    provider_job_reference: str | None = None
    output_reference: str | None = None
    provenance_reference: str | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValueError("job timestamps must be timezone-aware")

        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot precede created_at")

        if self.status is VoiceCloneStatus.READY:
            if not self.output_reference:
                raise ValueError("READY clone jobs require an output_reference")
            if not self.provenance_reference:
                raise ValueError(
                    "READY clone jobs require provenance_reference"
                )

        if self.status is VoiceCloneStatus.FAILED and not self.error_code:
            raise ValueError("FAILED clone jobs require error_code")


@dataclass(frozen=True, slots=True)
class VoiceCloneArtifact:
    """Provider-neutral metadata for a generated voice artifact."""

    artifact_id: UUID
    job_request_id: UUID
    provider: str
    output_reference: str
    provenance_reference: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("provider must not be blank")
        if not self.output_reference.strip():
            raise ValueError("output_reference must not be blank")
        if not self.provenance_reference.strip():
            raise ValueError("provenance_reference must not be blank")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")


class VoiceCloneLifecycle:
    """Explicit state-transition policy for voice-cloning jobs."""

    _ALLOWED: dict[VoiceCloneStatus, frozenset[VoiceCloneStatus]] = {
        VoiceCloneStatus.PENDING: frozenset(
            {
                VoiceCloneStatus.PROCESSING,
                VoiceCloneStatus.REVOKED,
            }
        ),
        VoiceCloneStatus.PROCESSING: frozenset(
            {
                VoiceCloneStatus.READY,
                VoiceCloneStatus.FAILED,
                VoiceCloneStatus.REVOKED,
            }
        ),
        VoiceCloneStatus.READY: frozenset(
            {VoiceCloneStatus.REVOKED}
        ),
        VoiceCloneStatus.FAILED: frozenset(
            {
                VoiceCloneStatus.PENDING,
                VoiceCloneStatus.REVOKED,
            }
        ),
        VoiceCloneStatus.REVOKED: frozenset(),
    }

    @classmethod
    def can_transition(
        cls,
        current: VoiceCloneStatus,
        target: VoiceCloneStatus,
    ) -> bool:
        """Return whether a lifecycle transition is explicitly permitted."""

        return target in cls._ALLOWED[current]

    @classmethod
    def transition(
        cls,
        job: VoiceCloneJob,
        target: VoiceCloneStatus,
        *,
        now: datetime | None = None,
        provider: str | None = None,
        provider_job_reference: str | None = None,
        output_reference: str | None = None,
        provenance_reference: str | None = None,
        error_code: str | None = None,
    ) -> VoiceCloneJob:
        """Return an immutable replacement after validating the transition."""

        if not cls.can_transition(job.status, target):
            raise ValueError(
                f"invalid voice-clone transition: "
                f"{job.status.value} -> {target.value}"
            )

        timestamp = now or datetime.now(UTC)

        if timestamp.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        return VoiceCloneJob(
            request=job.request,
            status=target,
            created_at=job.created_at,
            updated_at=timestamp,
            provider=provider
            if provider is not None
            else job.provider,
            provider_job_reference=(
                provider_job_reference
                if provider_job_reference is not None
                else job.provider_job_reference
            ),
            output_reference=(
                output_reference
                if output_reference is not None
                else job.output_reference
            ),
            provenance_reference=(
                provenance_reference
                if provenance_reference is not None
                else job.provenance_reference
            ),
            error_code=(
                error_code
                if error_code is not None
                else job.error_code
            ),
        )


def create_voice_clone_request(
    *,
    subject_identity_id: UUID,
    profile_id: UUID,
    representation_id: UUID,
    source_reference: str,
    consent: VoiceCloneConsent,
    requested_at: datetime | None = None,
    locale: str | None = None,
    output_format: VoiceCloneOutputFormat = VoiceCloneOutputFormat.WAV,
    max_duration_seconds: int = 60,
    provenance: str | None = None,
) -> VoiceCloneRequest:
    """Create a validated immutable cloning request."""

    timestamp = requested_at or datetime.now(UTC)

    return VoiceCloneRequest(
        identity_id=str(subject_identity_id),
        subject_identity_id=subject_identity_id,
        profile_id=profile_id,
        source_representation_ref=source_reference,
        consent_evidence_ref=consent.evidence_reference,
        source=VoiceCloneSource(
            representation_id=representation_id,
            source_reference=source_reference,
        ),
        consent=consent,
        requested_at=timestamp,
        locale=locale,
        output_format=output_format,
        max_duration_seconds=max_duration_seconds,
        provenance=(
            provenance
            if provenance is not None
            else f"authorized voice cloning request:{consent.evidence_reference}"
        ),
    )


def create_pending_job(
    request: VoiceCloneRequest,
    *,
    now: datetime | None = None,
) -> VoiceCloneJob:
    """Create the initial PENDING lifecycle representation."""

    timestamp = now or datetime.now(UTC)

    return VoiceCloneJob(
        request=request,
        status=VoiceCloneStatus.PENDING,
        created_at=timestamp,
        updated_at=timestamp,
    )
