"""Unit tests for the 19.4.3 voice-cloning domain contract."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from lyrion.voice.cloning import (
    VoiceCloneConsent,
    VoiceCloneLifecycle,
    VoiceClonePurpose,
    VoiceCloneStatus,
    create_pending_job,
    create_voice_clone_request,
)


def _consent(subject_id):
    return VoiceCloneConsent(
        consent_id=uuid4(),
        subject_identity_id=subject_id,
        granted_at=datetime(2026, 9, 3, 10, 0, tzinfo=UTC),
        purpose=VoiceClonePurpose.PERSONAL_ASSISTANT,
        terms_version="voice-cloning-consent-v1",
        evidence_reference="consent:evidence:001",
    )


def _request():
    subject_id = uuid4()
    return create_voice_clone_request(
        subject_identity_id=subject_id,
        profile_id=uuid4(),
        representation_id=uuid4(),
        source_reference="voice-representation:001",
        consent=_consent(subject_id),
        requested_at=datetime(2026, 9, 3, 10, 1, tzinfo=UTC),
    )


def test_request_requires_matching_consent_subject():
    subject_id = uuid4()

    with pytest.raises(ValueError, match="consent subject"):
        create_voice_clone_request(
            subject_identity_id=subject_id,
            profile_id=uuid4(),
            representation_id=uuid4(),
            source_reference="voice-representation:001",
            consent=_consent(uuid4()),
            requested_at=datetime(
                2026, 9, 3, 10, 1, tzinfo=UTC
            ),
        )


def test_request_cannot_precede_consent():
    subject_id = uuid4()
    consent = _consent(subject_id)

    with pytest.raises(ValueError, match="precede consent"):
        create_voice_clone_request(
            subject_identity_id=subject_id,
            profile_id=uuid4(),
            representation_id=uuid4(),
            source_reference="voice-representation:001",
            consent=consent,
            requested_at=datetime(
                2026, 9, 3, 9, 59, tzinfo=UTC
            ),
        )


def test_pending_job_is_immutable():
    request = _request()
    job = create_pending_job(
        request,
        now=datetime(2026, 9, 3, 10, 2, tzinfo=UTC),
    )

    assert job.status is VoiceCloneStatus.PENDING

    with pytest.raises(AttributeError):
        job.status = VoiceCloneStatus.PROCESSING  # type: ignore[misc]


def test_pending_to_processing_is_allowed():
    job = create_pending_job(_request())

    transitioned = VoiceCloneLifecycle.transition(
        job,
        VoiceCloneStatus.PROCESSING,
        now=datetime(2026, 9, 3, 10, 3, tzinfo=UTC),
        provider="provider-adapter",
        provider_job_reference="provider-job:001",
    )

    assert transitioned.status is VoiceCloneStatus.PROCESSING
    assert transitioned.provider == "provider-adapter"
    assert transitioned.provider_job_reference == "provider-job:001"
    assert job.status is VoiceCloneStatus.PENDING


def test_pending_to_ready_is_rejected():
    job = create_pending_job(_request())

    with pytest.raises(ValueError, match="invalid voice-clone transition"):
        VoiceCloneLifecycle.transition(
            job,
            VoiceCloneStatus.READY,
        )


def test_ready_requires_output_and_provenance():
    processing = VoiceCloneLifecycle.transition(
        create_pending_job(_request()),
        VoiceCloneStatus.PROCESSING,
    )

    with pytest.raises(ValueError, match="output_reference"):
        VoiceCloneLifecycle.transition(
            processing,
            VoiceCloneStatus.READY,
            provider="provider-adapter",
        )


def test_ready_requires_provenance():
    processing = VoiceCloneLifecycle.transition(
        create_pending_job(_request()),
        VoiceCloneStatus.PROCESSING,
    )

    with pytest.raises(ValueError, match="provenance_reference"):
        VoiceCloneLifecycle.transition(
            processing,
            VoiceCloneStatus.READY,
            provider="provider-adapter",
            output_reference="artifact:001",
        )


def test_processing_to_ready_requires_provenance_and_output():
    processing = VoiceCloneLifecycle.transition(
        create_pending_job(_request()),
        VoiceCloneStatus.PROCESSING,
    )

    ready = VoiceCloneLifecycle.transition(
        processing,
        VoiceCloneStatus.READY,
        provider="provider-adapter",
        output_reference="artifact:001",
        provenance_reference="provenance:001",
    )

    assert ready.status is VoiceCloneStatus.READY
    assert ready.output_reference == "artifact:001"
    assert ready.provenance_reference == "provenance:001"


def test_ready_can_be_revoked():
    processing = VoiceCloneLifecycle.transition(
        create_pending_job(_request()),
        VoiceCloneStatus.PROCESSING,
    )

    ready = VoiceCloneLifecycle.transition(
        processing,
        VoiceCloneStatus.READY,
        provider="provider-adapter",
        output_reference="artifact:001",
        provenance_reference="provenance:001",
    )

    revoked = VoiceCloneLifecycle.transition(
        ready,
        VoiceCloneStatus.REVOKED,
    )

    assert revoked.status is VoiceCloneStatus.REVOKED


def test_revoked_is_terminal():
    processing = VoiceCloneLifecycle.transition(
        create_pending_job(_request()),
        VoiceCloneStatus.PROCESSING,
    )

    ready = VoiceCloneLifecycle.transition(
        processing,
        VoiceCloneStatus.READY,
        provider="provider-adapter",
        output_reference="artifact:001",
        provenance_reference="provenance:001",
    )

    revoked = VoiceCloneLifecycle.transition(
        ready,
        VoiceCloneStatus.REVOKED,
    )

    with pytest.raises(ValueError, match="invalid voice-clone transition"):
        VoiceCloneLifecycle.transition(
            revoked,
            VoiceCloneStatus.PROCESSING,
        )


def test_failed_job_requires_error_code():
    processing = VoiceCloneLifecycle.transition(
        create_pending_job(_request()),
        VoiceCloneStatus.PROCESSING,
    )

    with pytest.raises(ValueError, match="error_code"):
        VoiceCloneLifecycle.transition(
            processing,
            VoiceCloneStatus.FAILED,
        )


def test_failed_job_can_retry_to_pending():
    processing = VoiceCloneLifecycle.transition(
        create_pending_job(_request()),
        VoiceCloneStatus.PROCESSING,
    )

    failed = VoiceCloneLifecycle.transition(
        processing,
        VoiceCloneStatus.FAILED,
        error_code="PROVIDER_TEMPORARY_FAILURE",
    )

    pending = VoiceCloneLifecycle.transition(
        failed,
        VoiceCloneStatus.PENDING,
    )

    assert failed.status is VoiceCloneStatus.FAILED
    assert pending.status is VoiceCloneStatus.PENDING
