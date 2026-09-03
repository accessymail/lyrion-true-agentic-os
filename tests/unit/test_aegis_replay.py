"""Adversarial unit tests for Aegis replay protection."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from lyrion.security.replay import ReplayGuard


def test_first_use_is_accepted() -> None:
    """A previously unseen idempotency key should be accepted."""
    guard = ReplayGuard()

    assert guard.check_and_record(
        "idem-001",
        "request-001",
    ) is True


def test_duplicate_same_request_is_rejected() -> None:
    """The same idempotency key cannot be accepted twice."""
    guard = ReplayGuard()

    assert guard.check_and_record(
        "idem-001",
        "request-001",
    ) is True

    assert guard.check_and_record(
        "idem-001",
        "request-001",
    ) is False


def test_same_key_different_request_is_rejected() -> None:
    """An idempotency key cannot be reused by another request."""
    guard = ReplayGuard()

    assert guard.check_and_record(
        "idem-001",
        "request-001",
    ) is True

    assert guard.check_and_record(
        "idem-001",
        "request-002",
    ) is False

    assert guard.request_for("idem-001") == "request-001"


def test_seen_reports_recorded_keys() -> None:
    """seen() should accurately report registry membership."""
    guard = ReplayGuard()

    assert guard.seen("idem-001") is False

    guard.check_and_record(
        "idem-001",
        "request-001",
    )

    assert guard.seen("idem-001") is True


def test_request_for_returns_associated_request() -> None:
    """request_for() should return the original request identifier."""
    guard = ReplayGuard()

    guard.check_and_record(
        "idem-001",
        "request-001",
    )

    assert guard.request_for("idem-001") == "request-001"


def test_unknown_key_has_no_request() -> None:
    """Unknown idempotency keys should have no associated request."""
    guard = ReplayGuard()

    assert guard.request_for("unknown-key") is None


def test_clear_removes_recorded_keys() -> None:
    """clear() should remove all replay state."""
    guard = ReplayGuard()

    guard.check_and_record(
        "idem-001",
        "request-001",
    )

    assert guard.seen("idem-001") is True

    guard.clear()

    assert guard.seen("idem-001") is False
    assert guard.request_for("idem-001") is None


def test_empty_idempotency_key_is_rejected() -> None:
    """Blank idempotency keys must be rejected."""
    guard = ReplayGuard()

    with pytest.raises(ValueError):
        guard.check_and_record(
            "",
            "request-001",
        )


def test_whitespace_only_idempotency_key_is_rejected() -> None:
    """Whitespace-only idempotency keys must be rejected."""
    guard = ReplayGuard()

    with pytest.raises(ValueError):
        guard.check_and_record(
            "   ",
            "request-001",
        )


def test_empty_request_id_is_rejected() -> None:
    """Blank request identifiers must be rejected."""
    guard = ReplayGuard()

    with pytest.raises(ValueError):
        guard.check_and_record(
            "idem-001",
            "",
        )


def test_whitespace_only_request_id_is_rejected() -> None:
    """Whitespace-only request identifiers must be rejected."""
    guard = ReplayGuard()

    with pytest.raises(ValueError):
        guard.check_and_record(
            "idem-001",
            "   ",
        )


def test_seen_rejects_empty_key() -> None:
    """seen() must reject an empty key."""
    guard = ReplayGuard()

    with pytest.raises(ValueError):
        guard.seen("")


def test_request_for_rejects_empty_key() -> None:
    """request_for() must reject an empty key."""
    guard = ReplayGuard()

    with pytest.raises(ValueError):
        guard.request_for("")


def test_replay_record_is_immutable() -> None:
    """Replay records should be immutable value objects."""
    from lyrion.security.replay import ReplayRecord

    record = ReplayRecord(
        request_id="request-001",
    )

    with pytest.raises(AttributeError):
        record.request_id = "changed"


def test_concurrent_first_use_has_single_winner() -> None:
    """Concurrent reuse of one key should allow exactly one winner."""
    guard = ReplayGuard()

    def attempt(index: int) -> bool:
        """Attempt to register the same idempotency key."""
        return guard.check_and_record(
            "idem-concurrent",
            f"request-{index}",
        )

    with ThreadPoolExecutor(max_workers=16) as executor:
        results = list(
            executor.map(
                attempt,
                range(32),
            )
        )

    assert sum(results) == 1
    assert guard.seen("idem-concurrent") is True
    assert guard.request_for("idem-concurrent") is not None


def test_concurrent_reuse_preserves_one_request_binding() -> None:
    """Concurrent registration must preserve the winning request binding."""
    guard = ReplayGuard()

    def attempt(index: int) -> bool:
        """Attempt to register a shared key."""
        return guard.check_and_record(
            "idem-binding",
            f"request-{index}",
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(
            executor.map(
                attempt,
                range(16),
            )
        )

    assert sum(results) == 1

    stored_request = guard.request_for("idem-binding")

    assert stored_request is not None
    assert stored_request.startswith("request-")


def test_replay_behavior_is_deterministic() -> None:
    """Repeated replay attempts should produce stable results."""
    guard = ReplayGuard()

    first = guard.check_and_record(
        "idem-deterministic",
        "request-001",
    )
    second = guard.check_and_record(
        "idem-deterministic",
        "request-001",
    )
    third = guard.check_and_record(
        "idem-deterministic",
        "request-002",
    )

    assert first is True
    assert second is False
    assert third is False
    assert guard.request_for("idem-deterministic") == "request-001"
