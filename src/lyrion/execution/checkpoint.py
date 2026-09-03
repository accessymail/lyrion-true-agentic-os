"""Checkpoint and rollback contracts for secure Lyrion execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from threading import Lock
from typing import Any


class CheckpointStatus(StrEnum):
    """Lifecycle state of a checkpoint."""

    CREATED = "CREATED"
    SEALED = "SEALED"
    ROLLBACK_REQUESTED = "ROLLBACK_REQUESTED"
    ROLLED_BACK = "ROLLED_BACK"
    INVALID = "INVALID"


class RollbackReason(StrEnum):
    """Reason for requesting rollback."""

    EXECUTION_FAILURE = "EXECUTION_FAILURE"
    TIMEOUT = "TIMEOUT"
    CANCELLATION = "CANCELLATION"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    MANUAL_REQUEST = "MANUAL_REQUEST"


@dataclass(frozen=True, slots=True)
class CheckpointRecord:
    """Immutable checkpoint record.

    The record itself is immutable, while ``metadata`` remains a mutable
    dictionary so integrity verification can detect post-creation mutation.
    """

    checkpoint_id: str
    execution_id: str
    revision: int
    created_at: datetime
    status: CheckpointStatus
    state_ref: str
    metadata: dict[str, Any]
    content_hash: str


class CheckpointManager:
    """Thread-safe in-memory checkpoint state manager."""

    def __init__(self) -> None:
        """Initialize an empty checkpoint registry."""
        self._records: dict[str, CheckpointRecord] = {}
        self._rollback_reasons: dict[str, RollbackReason] = {}
        self._lock = Lock()

    @staticmethod
    def calculate_content_hash(
        *,
        checkpoint_id: str,
        execution_id: str,
        revision: int,
        state_ref: str,
        metadata: dict[str, Any],
    ) -> str:
        """Calculate a deterministic checkpoint content hash."""
        canonical = (
            f"{checkpoint_id}|"
            f"{execution_id}|"
            f"{revision}|"
            f"{state_ref}|"
            f"{repr(sorted(metadata.items()))}"
        )

        return sha256(
            canonical.encode("utf-8"),
        ).hexdigest()

    def create(
        self,
        *,
        checkpoint_id: str,
        execution_id: str,
        revision: int,
        state_ref: str,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
    ) -> CheckpointRecord:
        """Create a new checkpoint record."""
        normalized_checkpoint_id = checkpoint_id.strip()
        normalized_execution_id = execution_id.strip()
        normalized_state_ref = state_ref.strip()

        if not normalized_checkpoint_id:
            raise ValueError("checkpoint_id must not be empty")

        if not normalized_execution_id:
            raise ValueError("execution_id must not be empty")

        if revision < 1:
            raise ValueError("revision must be positive")

        if not normalized_state_ref:
            raise ValueError("state_ref must not be empty")

        timestamp = created_at or datetime.now(UTC)

        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")

        normalized_metadata = dict(metadata or {})

        with self._lock:
            if normalized_checkpoint_id in self._records:
                raise ValueError("checkpoint_id already exists")

            content_hash = self.calculate_content_hash(
                checkpoint_id=normalized_checkpoint_id,
                execution_id=normalized_execution_id,
                revision=revision,
                state_ref=normalized_state_ref,
                metadata=normalized_metadata,
            )

            record = CheckpointRecord(
                checkpoint_id=normalized_checkpoint_id,
                execution_id=normalized_execution_id,
                revision=revision,
                created_at=timestamp.astimezone(UTC),
                status=CheckpointStatus.CREATED,
                state_ref=normalized_state_ref,
                metadata=normalized_metadata,
                content_hash=content_hash,
            )

            self._records[normalized_checkpoint_id] = record

            return record

    def get(
        self,
        checkpoint_id: str,
    ) -> CheckpointRecord | None:
        """Return one checkpoint record."""
        normalized_checkpoint_id = checkpoint_id.strip()

        if not normalized_checkpoint_id:
            raise ValueError("checkpoint_id must not be empty")

        with self._lock:
            return self._records.get(normalized_checkpoint_id)

    def seal(
        self,
        checkpoint_id: str,
    ) -> CheckpointRecord:
        """Seal a created checkpoint against lifecycle changes."""
        checkpoint = self._require_checkpoint(checkpoint_id)

        with self._lock:
            if checkpoint.status is not CheckpointStatus.CREATED:
                raise ValueError(
                    "only CREATED checkpoints can be sealed"
                )

            updated = self._replace(
                checkpoint,
                status=CheckpointStatus.SEALED,
            )

            self._records[checkpoint.checkpoint_id] = updated

            return updated

    def request_rollback(
        self,
        checkpoint_id: str,
        reason: RollbackReason,
    ) -> CheckpointRecord:
        """Mark a checkpoint for rollback."""
        checkpoint = self._require_checkpoint(checkpoint_id)

        with self._lock:
            if checkpoint.status is not CheckpointStatus.SEALED:
                raise ValueError(
                    "only SEALED checkpoints can be rolled back"
                )

            updated = self._replace(
                checkpoint,
                status=CheckpointStatus.ROLLBACK_REQUESTED,
            )

            self._records[checkpoint.checkpoint_id] = updated
            self._rollback_reasons[checkpoint.checkpoint_id] = reason

            return updated

    def mark_rolled_back(
        self,
        checkpoint_id: str,
    ) -> CheckpointRecord:
        """Record that rollback has completed."""
        checkpoint = self._require_checkpoint(checkpoint_id)

        with self._lock:
            if (
                checkpoint.status
                is not CheckpointStatus.ROLLBACK_REQUESTED
            ):
                raise ValueError(
                    "checkpoint must have rollback requested"
                )

            updated = self._replace(
                checkpoint,
                status=CheckpointStatus.ROLLED_BACK,
            )

            self._records[checkpoint.checkpoint_id] = updated

            return updated

    def rollback_reason(
        self,
        checkpoint_id: str,
    ) -> RollbackReason | None:
        """Return the recorded rollback reason."""
        checkpoint = self._require_checkpoint(checkpoint_id)

        with self._lock:
            return self._rollback_reasons.get(
                checkpoint.checkpoint_id
            )

    def checkpoints_for(
        self,
        execution_id: str,
    ) -> tuple[CheckpointRecord, ...]:
        """Return checkpoints associated with one execution."""
        normalized_execution_id = execution_id.strip()

        if not normalized_execution_id:
            raise ValueError("execution_id must not be empty")

        with self._lock:
            records = [
                record
                for record in self._records.values()
                if record.execution_id == normalized_execution_id
            ]

            return tuple(
                sorted(
                    records,
                    key=lambda record: record.revision,
                )
            )

    def verify(
        self,
        checkpoint_id: str,
    ) -> bool:
        """Verify the stored checkpoint content hash."""
        checkpoint = self._require_checkpoint(checkpoint_id)

        expected_hash = self.calculate_content_hash(
            checkpoint_id=checkpoint.checkpoint_id,
            execution_id=checkpoint.execution_id,
            revision=checkpoint.revision,
            state_ref=checkpoint.state_ref,
            metadata=checkpoint.metadata,
        )

        return checkpoint.content_hash == expected_hash

    def _require_checkpoint(
        self,
        checkpoint_id: str,
    ) -> CheckpointRecord:
        """Return a checkpoint or raise for an unknown identifier."""
        checkpoint = self.get(checkpoint_id)

        if checkpoint is None:
            raise KeyError(
                f"unknown checkpoint: {checkpoint_id}"
            )

        return checkpoint

    @staticmethod
    def _replace(
        checkpoint: CheckpointRecord,
        *,
        status: CheckpointStatus,
    ) -> CheckpointRecord:
        """Create a new immutable record with an updated status."""
        return CheckpointRecord(
            checkpoint_id=checkpoint.checkpoint_id,
            execution_id=checkpoint.execution_id,
            revision=checkpoint.revision,
            created_at=checkpoint.created_at,
            status=status,
            state_ref=checkpoint.state_ref,
            metadata=checkpoint.metadata,
            content_hash=checkpoint.content_hash,
        )
