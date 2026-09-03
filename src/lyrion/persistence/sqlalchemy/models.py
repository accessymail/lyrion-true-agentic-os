"""SQLAlchemy persistence models for durable Lyrion runtime state."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from lyrion.persistence.sqlalchemy.base import Base


class RuntimeInstanceModel(Base):
    """Persistent runtime instance lifecycle record."""

    __tablename__ = "runtime_instances"

    instance_id: Mapped[str] = mapped_column(
        String(200),
        primary_key=True,
    )
    state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )


class PersistentSchedulerModel(Base):
    """Persistent proactive scheduler lifecycle state."""

    __tablename__ = "persistent_scheduler"

    scheduler_id: Mapped[str] = mapped_column(
        String(200),
        primary_key=True,
    )
    state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )


class RuntimeLeaseModel(Base):
    """Persistent ownership lease for one runtime resource."""

    __tablename__ = "runtime_leases"
    __table_args__ = (
        UniqueConstraint(
            "resource_id",
            name="uq_runtime_leases_resource_id",
        ),
        Index(
            "ix_runtime_leases_resource_id",
            "resource_id",
        ),
        Index(
            "ix_runtime_leases_expires_at",
            "expires_at",
        ),
    )

    lease_id: Mapped[str] = mapped_column(
        String(200),
        primary_key=True,
    )
    resource_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    worker_id: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )


class PersistentOpportunityModel(Base):
    """Persistent opportunity lifecycle record."""

    __tablename__ = "persistent_opportunities"
    __table_args__ = (
        Index(
            "ix_persistent_opportunities_state",
            "state",
        ),
        Index(
            "ix_persistent_opportunities_claimed_at",
            "claimed_at",
        ),
        Index(
            "ix_persistent_opportunities_expires_at",
            "expires_at",
        ),
    )

    opportunity_id: Mapped[str] = mapped_column(
        String(500),
        primary_key=True,
    )
    state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    worker_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    lease_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    execution_id: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )


class PersistentExecutionModel(Base):
    """Persistent execution lifecycle record."""

    __tablename__ = "persistent_executions"
    __table_args__ = (
        Index(
            "ix_persistent_executions_state",
            "state",
        ),
        Index(
            "ix_persistent_executions_opportunity_id",
            "opportunity_id",
        ),
        Index(
            "ix_persistent_executions_worker_id",
            "worker_id",
        ),
    )

    execution_id: Mapped[str] = mapped_column(
        String(500),
        primary_key=True,
    )
    request_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    opportunity_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    task_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    worker_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    lease_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    checkpoint_ref: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    error_code: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        String(4000),
        nullable=True,
    )
    revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )


class PersistentIdempotencyModel(Base):
    """Persistent idempotency reservation."""

    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_idempotency_records_key",
        ),
        Index(
            "ix_idempotency_records_execution_id",
            "execution_id",
        ),
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(500),
        primary_key=True,
    )
    request_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    execution_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    reserved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class RecoveryDecisionModel(Base):
    """Persistent record of one recovery analysis decision."""

    __tablename__ = "recovery_decisions"
    __table_args__ = (
        Index(
            "ix_recovery_decisions_execution_id",
            "execution_id",
        ),
        Index(
            "ix_recovery_decisions_evaluated_at",
            "evaluated_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    execution_id: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    source_revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )


class PersistentVoiceSessionModel(Base):
    """Persistent logical voice-session continuity record."""

    __tablename__ = "voice_sessions"
    __table_args__ = (
        Index(
            "ix_voice_sessions_state",
            "state",
        ),
        Index(
            "ix_voice_sessions_expires_at",
            "expires_at",
        ),
    )

    session_id: Mapped[str] = mapped_column(
        String(200),
        primary_key=True,
    )
    correlation_id: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    session_revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    next_turn_sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    resumable_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    continuity_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )


class PersistentVoiceTurnModel(Base):
    """Persistent metadata for one voice-session turn."""

    __tablename__ = "voice_session_turns"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "sequence",
            name="uq_voice_session_turns_session_sequence",
        ),
        Index(
            "ix_voice_session_turns_session_id",
            "session_id",
        ),
        Index(
            "ix_voice_session_turns_request_id",
            "request_id",
        ),
    )

    turn_id: Mapped[str] = mapped_column(
        String(200),
        primary_key=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    request_id: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    input_reference: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    output_reference: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    provenance: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )


class VoiceIdentityProfileModel(Base):
    """Persistent voice identity profile lifecycle record."""

    __tablename__ = "voice_identity_profiles"
    __table_args__ = (
        Index(
            "ix_voice_identity_profiles_status",
            "status",
        ),
    )

    identity_id: Mapped[str] = mapped_column(
        String(200),
        primary_key=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    representation_refs: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    provenance: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )
    revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
