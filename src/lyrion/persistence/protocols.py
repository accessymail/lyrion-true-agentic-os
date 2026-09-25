"""Persistence ports for durable Lyrion runtime orchestration."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from lyrion.persistence.contracts import (
    OpportunityRecoveryContext,
    PersistentExecutionRecord,
    PersistentExecutionState,
    PersistentIdempotencyRecord,
    PersistentOpportunity,
    PersistentOpportunityState,
    PersistentScheduler,
    PersistentSchedulerState,
    RecoveryDecision,
    RuntimeInstance,
    RuntimeLease,
)
from lyrion.voice.contracts import VoiceIdentityProfile


class VoiceIdentityProfileStore(Protocol):
    """Durable Voice Identity profile lifecycle boundary."""

    async def get(self, identity_id: str) -> VoiceIdentityProfile | None:
        """Return one durable voice identity profile."""

    async def create(self, profile: VoiceIdentityProfile) -> VoiceIdentityProfile:
        """Atomically create one voice identity profile."""

    async def transition(
        self,
        identity_id: str,
        *,
        expected_revision: int,
        profile: VoiceIdentityProfile,
    ) -> VoiceIdentityProfile:
        """Atomically persist one lifecycle transition."""

    async def update(
        self,
        profile: VoiceIdentityProfile,
        *,
        expected_revision: int,
    ) -> VoiceIdentityProfile:
        """Atomically persist one revision-checked profile update."""


class RuntimeStore(Protocol):
    """Durable storage boundary for runtime lifecycle state."""

    async def get(
        self,
        instance_id: str,
    ) -> RuntimeInstance | None:
        """Return one runtime instance by identifier."""

    async def save(
        self,
        instance: RuntimeInstance,
    ) -> RuntimeInstance:
        """Persist a runtime instance."""

    async def transition(
        self,
        instance_id: str,
        *,
        expected_revision: int,
        state: RuntimeInstance,
    ) -> RuntimeInstance:
        """Atomically persist a lifecycle transition."""


class OpportunityStore(Protocol):
    """Durable opportunity lifecycle boundary."""

    async def create(
        self,
        opportunity: PersistentOpportunity,
    ) -> PersistentOpportunity:
        """Persist one newly queued opportunity."""

    async def get(
        self,
        opportunity_id: str,
    ) -> PersistentOpportunity | None:
        """Return one durable opportunity."""

    async def claim(
        self,
        *,
        opportunity_id: str,
        worker_id: str,
        lease_id: str,
        claimed_at: datetime,
        expected_revision: int,
    ) -> PersistentOpportunity | None:
        """Atomically claim one queued opportunity."""

    async def transition(
        self,
        *,
        opportunity_id: str,
        worker_id: str,
        lease_id: str,
        expected_revision: int,
        target_state: PersistentOpportunityState,
        occurred_at: datetime,
        execution_id: str | None = None,
    ) -> PersistentOpportunity:
        """Atomically advance one owned opportunity."""

    async def find_claimable(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> Sequence[PersistentOpportunity]:
        """Return bounded, unexpired queued opportunities."""

    async def find_recoverable(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> Sequence[PersistentOpportunity]:
        """Return bounded opportunities requiring recovery."""


class SchedulerStore(Protocol):
    """Durable scheduling lifecycle boundary."""

    async def get(
        self,
        scheduler_id: str,
    ) -> PersistentScheduler | None:
        """Return one durable scheduler state."""

    async def save(
        self,
        scheduler: PersistentScheduler,
    ) -> PersistentScheduler:
        """Persist one scheduler state."""

    async def transition(
        self,
        scheduler_id: str,
        *,
        expected_revision: int,
        state: PersistentSchedulerState,
        next_run_at: datetime | None,
    ) -> PersistentScheduler:
        """Atomically persist one scheduler state transition."""


class LeaseStore(Protocol):
    """Durable ownership boundary for runtime resources."""

    async def acquire(
        self,
        *,
        resource_id: str,
        worker_id: str,
        lease_id: str,
        acquired_at: datetime,
        expires_at: datetime,
    ) -> RuntimeLease | None:
        """Atomically acquire an unowned or expired resource."""

    async def get(
        self,
        resource_id: str,
    ) -> RuntimeLease | None:
        """Return the current lease for a resource."""

    async def renew(
        self,
        *,
        lease_id: str,
        worker_id: str,
        expected_revision: int,
        expires_at: datetime,
    ) -> RuntimeLease:
        """Atomically renew a lease owned by the worker."""

    async def release(
        self,
        *,
        lease_id: str,
        worker_id: str,
    ) -> None:
        """Release a lease owned by the worker."""

    async def find_expired(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> Sequence[RuntimeLease]:
        """Return expired leases up to an explicit bound."""


class ExecutionStore(Protocol):
    """Durable execution lifecycle boundary."""

    async def create(
        self,
        record: PersistentExecutionRecord,
    ) -> PersistentExecutionRecord:
        """Create a new execution record."""

    async def get(
        self,
        execution_id: str,
    ) -> PersistentExecutionRecord | None:
        """Return one execution record."""

    async def claim(
        self,
        *,
        execution_id: str,
        worker_id: str,
        lease_id: str,
        claimed_at: datetime,
        expected_revision: int,
    ) -> PersistentExecutionRecord | None:
        """Atomically claim one queued execution."""

    async def transition(
        self,
        *,
        execution_id: str,
        worker_id: str,
        lease_id: str,
        expected_revision: int,
        target_state: PersistentExecutionState,
        occurred_at: datetime,
        checkpoint_ref: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> PersistentExecutionRecord:
        """Atomically advance an owned execution lifecycle."""

    async def requeue(
        self,
        *,
        execution_id: str,
        expected_revision: int,
        occurred_at: datetime,
    ) -> PersistentExecutionRecord:
        """Return a recoverable execution to QUEUED without ownership."""

    async def find_recoverable(
        self,
        *,
        states: Sequence[PersistentExecutionState],
        now: datetime,
        limit: int,
    ) -> Sequence[PersistentExecutionRecord]:
        """Return bounded execution records requiring recovery."""


class IdempotencyStore(Protocol):
    """Durable cross-restart idempotency boundary."""

    async def reserve(
        self,
        record: PersistentIdempotencyRecord,
    ) -> bool:
        """Atomically reserve an idempotency record."""

    async def get(
        self,
        idempotency_key: str,
    ) -> PersistentIdempotencyRecord | None:
        """Return the durable record associated with a key."""

    async def contains(
        self,
        idempotency_key: str,
    ) -> bool:
        """Return whether an idempotency key is already registered."""


class OpportunityRecoveryContextStore(Protocol):
    """Durable immutable recovery-context boundary."""

    async def create(
        self,
        context: OpportunityRecoveryContext,
    ) -> OpportunityRecoveryContext:
        """Atomically persist one immutable recovery context."""

    async def get(
        self,
        opportunity_id: str,
    ) -> OpportunityRecoveryContext | None:
        """Return one recovery context by opportunity identifier."""

    async def exists(
        self,
        opportunity_id: str,
    ) -> bool:
        """Return whether recovery context exists for an opportunity."""


class RecoveryStore(Protocol):
    """Durable record of explicit recovery decisions."""

    async def record(
        self,
        decision: RecoveryDecision,
    ) -> RecoveryDecision:
        """Persist one recovery decision."""

    async def find_for_execution(
        self,
        execution_id: str,
    ) -> Sequence[RecoveryDecision]:
        """Return recovery decisions for one execution."""


class PersistenceUnitOfWork(Protocol):
    """Transactional boundary for related durable mutations."""

    async def __aenter__(self) -> PersistenceUnitOfWork:
        """Enter a persistence transaction."""

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        """Commit or roll back the transaction."""

    @property
    def voice_identity(self) -> VoiceIdentityProfileStore:
        """Return the Voice Identity profile store within the transaction."""

    @property
    def runtime(self) -> RuntimeStore:
        """Return the runtime store within the transaction."""

    @property
    def opportunities(self) -> OpportunityStore:
        """Return the opportunity store within the transaction."""

    @property
    def leases(self) -> LeaseStore:
        """Return the lease store within the transaction."""

    @property
    def executions(self) -> ExecutionStore:
        """Return the execution store within the transaction."""

    @property
    def idempotency(self) -> IdempotencyStore:
        """Return the idempotency store within the transaction."""

    @property
    def recovery(self) -> RecoveryStore:
        """Return the recovery store within the transaction."""
