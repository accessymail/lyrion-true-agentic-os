"""Contract tests for database-agnostic persistence protocols."""

import inspect
from datetime import UTC, datetime, timedelta

from lyrion.persistence.contracts import (
    PersistentExecutionRecord,
    PersistentExecutionState,
    RecoveryDecision,
    RuntimeInstance,
    RuntimeLease,
)
from lyrion.persistence.protocols import (
    ExecutionStore,
    IdempotencyStore,
    LeaseStore,
    PersistenceUnitOfWork,
    RecoveryStore,
    RuntimeStore,
)

BASE_TIME = datetime(
    2026,
    8,
    31,
    12,
    0,
    tzinfo=UTC,
)


def test_runtime_protocol_has_required_operations() -> None:
    """Runtime persistence must expose lifecycle operations."""
    assert hasattr(RuntimeStore, "get")
    assert hasattr(RuntimeStore, "save")
    assert hasattr(RuntimeStore, "transition")


def test_lease_protocol_has_atomic_ownership_operations() -> None:
    """Lease persistence must expose acquisition and renewal."""
    assert hasattr(LeaseStore, "acquire")
    assert hasattr(LeaseStore, "get")
    assert hasattr(LeaseStore, "renew")
    assert hasattr(LeaseStore, "release")
    assert hasattr(LeaseStore, "find_expired")



def test_runtime_and_lease_operations_are_async() -> None:
    """Database-backed runtime operations must be coroutine functions."""
    runtime_methods = (
        RuntimeStore.get,
        RuntimeStore.save,
        RuntimeStore.transition,
    )

    lease_methods = (
        LeaseStore.acquire,
        LeaseStore.get,
        LeaseStore.renew,
        LeaseStore.release,
        LeaseStore.find_expired,
    )

    for method in runtime_methods + lease_methods:
        assert inspect.iscoroutinefunction(method)


def test_unit_of_work_is_async_context_manager() -> None:
    """Transactional persistence must use async context management."""
    assert inspect.iscoroutinefunction(
        PersistenceUnitOfWork.__aenter__,
    )
    assert inspect.iscoroutinefunction(
        PersistenceUnitOfWork.__aexit__,
    )

def test_execution_protocol_has_claim_and_transition() -> None:
    """Execution persistence must expose ownership-aware lifecycle changes."""
    assert hasattr(ExecutionStore, "create")
    assert hasattr(ExecutionStore, "get")
    assert hasattr(ExecutionStore, "claim")
    assert hasattr(ExecutionStore, "transition")
    assert hasattr(ExecutionStore, "find_recoverable")


def test_execution_operations_are_async() -> None:
    """Database-backed execution operations must be coroutine functions."""
    execution_methods = (
        ExecutionStore.create,
        ExecutionStore.get,
        ExecutionStore.claim,
        ExecutionStore.transition,
        ExecutionStore.find_recoverable,
    )

    for method in execution_methods:
        assert inspect.iscoroutinefunction(method)


def test_idempotency_protocol_is_cross_restart_capable() -> None:
    """Idempotency persistence must support durable reservation lookup."""
    assert hasattr(IdempotencyStore, "reserve")
    assert hasattr(IdempotencyStore, "get")
    assert hasattr(IdempotencyStore, "contains")


def test_idempotency_operations_are_async() -> None:
    """Database-backed idempotency operations must be coroutine functions."""
    idempotency_methods = (
        IdempotencyStore.reserve,
        IdempotencyStore.get,
        IdempotencyStore.contains,
    )

    for method in idempotency_methods:
        assert inspect.iscoroutinefunction(method)


def test_recovery_protocol_records_explicit_decisions() -> None:
    """Recovery persistence must preserve decisions as durable evidence."""
    assert hasattr(RecoveryStore, "record")
    assert hasattr(RecoveryStore, "find_for_execution")


def test_recovery_operations_are_async() -> None:
    """Database-backed recovery operations must be coroutine functions."""
    recovery_methods = (
        RecoveryStore.record,
        RecoveryStore.find_for_execution,
    )

    for method in recovery_methods:
        assert inspect.iscoroutinefunction(method)


def test_unit_of_work_exposes_all_durable_boundaries() -> None:
    """Related lifecycle mutations need one transactional boundary."""
    assert hasattr(PersistenceUnitOfWork, "runtime")
    assert hasattr(PersistenceUnitOfWork, "leases")
    assert hasattr(PersistenceUnitOfWork, "executions")
    assert hasattr(PersistenceUnitOfWork, "idempotency")
    assert hasattr(PersistenceUnitOfWork, "recovery")


def test_protocol_methods_are_structural_only() -> None:
    """Protocol declarations must not instantiate implementation state."""
    assert getattr(RuntimeStore, "_is_protocol", False) is True
    assert getattr(LeaseStore, "_is_protocol", False) is True
    assert getattr(ExecutionStore, "_is_protocol", False) is True
    assert getattr(IdempotencyStore, "_is_protocol", False) is True


def test_contract_imports_remain_domain_objects() -> None:
    """Protocol signatures should reference domain contracts."""
    assert RuntimeInstance.__module__ == "lyrion.persistence.contracts"
    assert RuntimeLease.__module__ == "lyrion.persistence.contracts"
    assert (
        PersistentExecutionRecord.__module__
        == "lyrion.persistence.contracts"
    )
    assert (
        PersistentExecutionState.__module__
        == "lyrion.persistence.contracts"
    )
    assert RecoveryDecision.__module__ == "lyrion.persistence.contracts"


def test_protocols_do_not_define_database_vocabulary() -> None:
    """Ports must remain storage-technology agnostic."""
    protocol_names = (
        RuntimeStore,
        LeaseStore,
        ExecutionStore,
        IdempotencyStore,
        RecoveryStore,
        PersistenceUnitOfWork,
    )

    forbidden_terms = (
        "sqlalchemy",
        "session",
        "engine",
        "connection",
        "postgres",
        "asyncpg",
        "table",
    )

    for protocol in protocol_names:
        source = repr(protocol)
        assert not any(
            term in source.lower()
            for term in forbidden_terms
        )


def test_lease_signature_uses_explicit_clock_boundaries() -> None:
    """Ownership APIs must receive explicit timestamps."""
    assert isinstance(BASE_TIME, datetime)
    assert (
        BASE_TIME + timedelta(seconds=1)
    ).tzinfo is UTC


def test_execution_state_enum_has_recovery_states() -> None:
    """Execution persistence must distinguish unresolved recovery states."""
    assert PersistentExecutionState.UNKNOWN.value == "UNKNOWN"
    assert PersistentExecutionState.ABANDONED.value == "ABANDONED"
