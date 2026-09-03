"""Adversarial tests for execution checkpoint and rollback controls."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest

from lyrion.execution.checkpoint import (
    CheckpointManager,
    CheckpointStatus,
    RollbackReason,
)


def make_manager() -> CheckpointManager:
    """Create a fresh checkpoint manager."""
    return CheckpointManager()


def create_checkpoint(
    manager: CheckpointManager,
    *,
    checkpoint_id: str = "checkpoint-001",
    execution_id: str = "execution-001",
    revision: int = 1,
):
    """Create a baseline checkpoint."""
    return manager.create(
        checkpoint_id=checkpoint_id,
        execution_id=execution_id,
        revision=revision,
        state_ref=f"state-ref-{revision}",
        metadata={
            "task": "execution-test",
            "revision": revision,
        },
        created_at=datetime(
            2026,
            1,
            1,
            tzinfo=UTC,
        ),
    )


def test_checkpoint_creation() -> None:
    """A valid checkpoint should be created."""
    manager = make_manager()

    checkpoint = create_checkpoint(manager)

    assert checkpoint.checkpoint_id == "checkpoint-001"
    assert checkpoint.execution_id == "execution-001"
    assert checkpoint.revision == 1
    assert checkpoint.status is CheckpointStatus.CREATED
    assert len(checkpoint.content_hash) == 64


def test_checkpoint_is_retrievable() -> None:
    """Created checkpoints should be retrievable by ID."""
    manager = make_manager()

    checkpoint = create_checkpoint(manager)

    assert manager.get(
        checkpoint.checkpoint_id
    ) is checkpoint


def test_checkpoint_is_immutable() -> None:
    """Checkpoint records must not be mutable."""
    manager = make_manager()
    checkpoint = create_checkpoint(manager)

    with pytest.raises(AttributeError):
        checkpoint.status = CheckpointStatus.SEALED


def test_blank_checkpoint_id_is_rejected() -> None:
    """Blank checkpoint IDs must be rejected."""
    with pytest.raises(ValueError):
        CheckpointManager().create(
            checkpoint_id="",
            execution_id="execution-001",
            revision=1,
            state_ref="state-ref",
        )


def test_blank_execution_id_is_rejected() -> None:
    """Blank execution IDs must be rejected."""
    with pytest.raises(ValueError):
        CheckpointManager().create(
            checkpoint_id="checkpoint-001",
            execution_id="",
            revision=1,
            state_ref="state-ref",
        )


def test_blank_state_reference_is_rejected() -> None:
    """Blank state references must be rejected."""
    with pytest.raises(ValueError):
        CheckpointManager().create(
            checkpoint_id="checkpoint-001",
            execution_id="execution-001",
            revision=1,
            state_ref="",
        )


def test_revision_must_be_positive() -> None:
    """Checkpoint revisions must start at one."""
    with pytest.raises(ValueError):
        CheckpointManager().create(
            checkpoint_id="checkpoint-001",
            execution_id="execution-001",
            revision=0,
            state_ref="state-ref",
        )


def test_naive_checkpoint_time_is_rejected() -> None:
    """Checkpoint timestamps must be timezone-aware."""
    with pytest.raises(ValueError):
        CheckpointManager().create(
            checkpoint_id="checkpoint-001",
            execution_id="execution-001",
            revision=1,
            state_ref="state-ref",
            created_at=datetime.now(),
        )


def test_duplicate_checkpoint_id_is_rejected() -> None:
    """Checkpoint identifiers must be unique."""
    manager = make_manager()

    create_checkpoint(manager)

    with pytest.raises(ValueError):
        create_checkpoint(manager)


def test_checkpoint_can_be_sealed() -> None:
    """A CREATED checkpoint can transition to SEALED."""
    manager = make_manager()

    create_checkpoint(manager)

    sealed = manager.seal("checkpoint-001")

    assert sealed.status is CheckpointStatus.SEALED
    assert manager.get("checkpoint-001") is sealed


def test_only_created_checkpoint_can_be_sealed() -> None:
    """A sealed checkpoint cannot be sealed twice."""
    manager = make_manager()

    create_checkpoint(manager)
    manager.seal("checkpoint-001")

    with pytest.raises(ValueError):
        manager.seal("checkpoint-001")


def test_sealed_checkpoint_can_request_rollback() -> None:
    """A sealed checkpoint can enter rollback-requested state."""
    manager = make_manager()

    create_checkpoint(manager)
    manager.seal("checkpoint-001")

    checkpoint = manager.request_rollback(
        "checkpoint-001",
        RollbackReason.EXECUTION_FAILURE,
    )

    assert checkpoint.status is CheckpointStatus.ROLLBACK_REQUESTED
    assert manager.rollback_reason(
        "checkpoint-001"
    ) is RollbackReason.EXECUTION_FAILURE


def test_created_checkpoint_cannot_request_rollback() -> None:
    """Rollback requires a sealed checkpoint."""
    manager = make_manager()

    create_checkpoint(manager)

    with pytest.raises(ValueError):
        manager.request_rollback(
            "checkpoint-001",
            RollbackReason.TIMEOUT,
        )


def test_rollback_can_be_completed() -> None:
    """A requested rollback can be marked complete."""
    manager = make_manager()

    create_checkpoint(manager)
    manager.seal("checkpoint-001")
    manager.request_rollback(
        "checkpoint-001",
        RollbackReason.CANCELLATION,
    )

    checkpoint = manager.mark_rolled_back(
        "checkpoint-001",
    )

    assert checkpoint.status is CheckpointStatus.ROLLED_BACK


def test_unrequested_rollback_cannot_complete() -> None:
    """Rollback cannot complete before it is requested."""
    manager = make_manager()

    create_checkpoint(manager)
    manager.seal("checkpoint-001")

    with pytest.raises(ValueError):
        manager.mark_rolled_back(
            "checkpoint-001",
        )


def test_rollback_reason_is_preserved() -> None:
    """Rollback reason must remain associated with the checkpoint."""
    manager = make_manager()

    create_checkpoint(manager)
    manager.seal("checkpoint-001")

    manager.request_rollback(
        "checkpoint-001",
        RollbackReason.POLICY_VIOLATION,
    )

    assert manager.rollback_reason(
        "checkpoint-001"
    ) is RollbackReason.POLICY_VIOLATION


def test_checkpoints_are_ordered_by_revision() -> None:
    """Execution checkpoints should be returned by revision."""
    manager = make_manager()

    create_checkpoint(
        manager,
        checkpoint_id="checkpoint-002",
        revision=2,
    )
    create_checkpoint(
        manager,
        checkpoint_id="checkpoint-001",
        revision=1,
    )
    create_checkpoint(
        manager,
        checkpoint_id="checkpoint-003",
        revision=3,
    )

    checkpoints = manager.checkpoints_for(
        "execution-001",
    )

    assert [
        checkpoint.revision
        for checkpoint in checkpoints
    ] == [1, 2, 3]


def test_checkpoints_are_scoped_to_execution() -> None:
    """Executions must only see their own checkpoints."""
    manager = make_manager()

    create_checkpoint(
        manager,
        checkpoint_id="checkpoint-a",
        execution_id="execution-a",
    )
    create_checkpoint(
        manager,
        checkpoint_id="checkpoint-b",
        execution_id="execution-b",
    )

    checkpoints = manager.checkpoints_for(
        "execution-a",
    )

    assert len(checkpoints) == 1
    assert checkpoints[0].execution_id == "execution-a"


def test_content_hash_is_deterministic() -> None:
    """Equivalent checkpoint inputs must produce the same hash."""
    metadata = {
        "task": "example",
        "revision": 1,
    }

    first = CheckpointManager.calculate_content_hash(
        checkpoint_id="checkpoint-001",
        execution_id="execution-001",
        revision=1,
        state_ref="state-ref",
        metadata=metadata,
    )
    second = CheckpointManager.calculate_content_hash(
        checkpoint_id="checkpoint-001",
        execution_id="execution-001",
        revision=1,
        state_ref="state-ref",
        metadata=metadata,
    )

    assert first == second


def test_content_hash_changes_when_state_reference_changes() -> None:
    """Changing state references must change the content hash."""
    first = CheckpointManager.calculate_content_hash(
        checkpoint_id="checkpoint-001",
        execution_id="execution-001",
        revision=1,
        state_ref="state-a",
        metadata={},
    )
    second = CheckpointManager.calculate_content_hash(
        checkpoint_id="checkpoint-001",
        execution_id="execution-001",
        revision=1,
        state_ref="state-b",
        metadata={},
    )

    assert first != second


def test_checkpoint_integrity_verifies() -> None:
    """An untampered checkpoint should verify successfully."""
    manager = make_manager()

    checkpoint = create_checkpoint(manager)

    assert manager.verify(
        checkpoint.checkpoint_id,
    ) is True


def test_tampering_is_detected() -> None:
    """Changing stored checkpoint metadata must invalidate verification."""
    manager = make_manager()

    checkpoint = create_checkpoint(manager)

    checkpoint.metadata["tampered"] = True

    assert manager.verify(
        checkpoint.checkpoint_id,
    ) is False


def test_unknown_checkpoint_raises_key_error() -> None:
    """Unknown checkpoint IDs must fail clearly."""
    with pytest.raises(KeyError):
        CheckpointManager().verify(
            "unknown-checkpoint",
        )


def test_blank_lookup_id_is_rejected() -> None:
    """Blank checkpoint lookups must be rejected."""
    manager = make_manager()

    with pytest.raises(ValueError):
        manager.get("")


def test_blank_execution_lookup_is_rejected() -> None:
    """Blank execution lookups must be rejected."""
    manager = make_manager()

    with pytest.raises(ValueError):
        manager.checkpoints_for("")


def test_concurrent_checkpoint_creation_has_no_duplicate_ids() -> None:
    """Concurrent unique checkpoint creation must remain consistent."""
    manager = make_manager()

    def create(index: int):
        """Create one unique checkpoint."""
        return create_checkpoint(
            manager,
            checkpoint_id=f"checkpoint-{index}",
            revision=index,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        checkpoints = list(
            executor.map(
                create,
                range(1, 33),
            )
        )

    assert len(checkpoints) == 32
    assert manager.checkpoints_for(
        "execution-001",
    )


def test_concurrent_duplicate_creation_has_single_winner() -> None:
    """Concurrent creation of one ID must permit one winner."""
    manager = make_manager()

    def attempt(index: int) -> bool:
        """Attempt to create the shared checkpoint ID."""
        try:
            create_checkpoint(
                manager,
                checkpoint_id="shared-checkpoint",
                revision=index + 1,
            )
        except ValueError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=16) as executor:
        results = list(
            executor.map(
                attempt,
                range(32),
            )
        )

    assert sum(results) == 1
    assert manager.get(
        "shared-checkpoint",
    ) is not None
