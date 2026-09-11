"""Replay and idempotency protection for Aegis authorization."""

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True, slots=True)
class ReplayRecord:
    """Immutable record of a previously accepted idempotency key."""

    request_id: str


class ReplayGuard:
    """Process-local replay guard for capability authorization requests.

    A key may be accepted once for a specific request. Reuse is rejected.
    """

    def __init__(self) -> None:
        """Initialize an empty replay registry."""
        self._records: dict[str, ReplayRecord] = {}
        self._lock = Lock()

    def check_and_record(
        self,
        idempotency_key: str,
        request_id: str,
    ) -> bool:
        """Atomically accept a new key or reject a replay."""

        key = idempotency_key.strip()
        request = request_id.strip()

        if not key:
            raise ValueError("idempotency_key must not be empty")

        if not request:
            raise ValueError("request_id must not be empty")

        with self._lock:
            existing = self._records.get(key)

            if existing is not None:
                return False

            self._records[key] = ReplayRecord(
                request_id=request,
            )

            return True

    def seen(self, idempotency_key: str) -> bool:
        """Return whether an idempotency key has already been recorded."""

        key = idempotency_key.strip()

        if not key:
            raise ValueError("idempotency_key must not be empty")

        with self._lock:
            return key in self._records

    def request_for(self, idempotency_key: str) -> str | None:
        """Return the request associated with a recorded key."""

        key = idempotency_key.strip()

        if not key:
            raise ValueError("idempotency_key must not be empty")

        with self._lock:
            record = self._records.get(key)

            return None if record is None else record.request_id

    def clear(self) -> None:
        """Clear all recorded keys."""

        with self._lock:
            self._records.clear()
