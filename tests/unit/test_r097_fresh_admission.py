"""R097 fresh-admission runtime evidence.

These tests verify that recovered work re-enters the normal capability
authorization boundary and that stale authority is not reusable.

The tests intentionally use the production-shaped:
    CapabilityGateway
        -> AegisAuthorizationService
        -> AegisPolicyEvaluator
        -> AuthorizationGuard
        -> ReplayGuard

No checkpoint authorization or execution admission is injected into the
recovery path.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from lyrion.capabilities.gateway import CapabilityGateway
from lyrion.core.types import (
    AutonomyLevel,
    CorrelationId,
    EventId,
    IdempotencyKey,
    OpportunityId,
    TaskId,
)
from lyrion.events.models import EventSensitivity, EventTrustLevel
from lyrion.integration.proactive_execution import (
    ProactiveExecutionCoordinator,
)
from lyrion.piae.contracts import Opportunity
from lyrion.piae.opportunity_queue import OpportunityQueue
from lyrion.persistence.opportunity_recovery_context import (
    OpportunityRecoveryContextFactory,
)
from lyrion.persistence.opportunity_recovery_context_resolver import (
    OpportunityRecoveryContextResolver,
)
from lyrion.persistence.opportunity_recovery_reentry import (
    OpportunityRecoveryReentryCoordinator,
)
from lyrion.persistence.protocols import OpportunityRecoveryContextStore
from lyrion.security.authorization import AegisAuthorizationService
from lyrion.security.guards import AuthorizationGuard
from lyrion.security.policy import AegisPolicyEvaluator
from lyrion.security.replay import ReplayGuard
from lyrion.security.rules import default_aegis_policy


class InMemoryRecoveryContextStore:
    """Minimal test-only recovery context store."""

    def __init__(self) -> None:
        self._contexts: dict[str, object] = {}

    async def create(self, context: object) -> None:
        opportunity_id = str(context.opportunity_id)
        if opportunity_id in self._contexts:
            raise ValueError("duplicate opportunity_id")
        self._contexts[opportunity_id] = context

    async def get(self, opportunity_id: str) -> object | None:
        return self._contexts.get(opportunity_id)

    async def exists(self, opportunity_id: str) -> bool:
        return opportunity_id in self._contexts


def make_opportunity(*, expires_at: datetime | None) -> Opportunity:
    now = datetime.now(UTC)

    return Opportunity(
        opportunity_id=OpportunityId("r097-3d4e-opportunity"),
        correlation_id=CorrelationId("r097-3d4e-correlation"),
        trigger_event_ids=(EventId("r097-3d4e-event"),),
        relevant_state_ids=("state-r097-3d4e",),
        goal_context=("r097 fresh admission validation",),
        title="R097 fresh admission validation",
        description="Validate stale authority rejection after recovery.",
        user_relevance=0.9,
        expected_benefit=0.8,
        interruption_cost=0.1,
        risk_score=0.2,
        reversibility=0.9,
        urgency=0.5,
        confidence=0.95,
        required_capabilities=("development.prepare",),
        required_autonomy_level=AutonomyLevel.L1,
        sensitivity=EventSensitivity.INTERNAL,
        trust_level=EventTrustLevel.HIGH,
        status="OPEN",
        created_at=now,
        expires_at=expires_at,
    )


def make_gateway() -> CapabilityGateway:
    policy = default_aegis_policy()

    return CapabilityGateway(
        AegisAuthorizationService(
            AegisPolicyEvaluator(policy),
            AuthorizationGuard(policy.policy_version),
            ReplayGuard(),
        )
    )


def make_coordinator() -> ProactiveExecutionCoordinator:
    return ProactiveExecutionCoordinator(
        gateway=make_gateway(),
        executor=__import__(
            "lyrion.execution.executor",
            fromlist=["SecureExecutor"],
        ).SecureExecutor(),
    )


def make_constraints():
    from lyrion.piae.contracts import DecisionConstraints
    from lyrion.core.types import RiskLevel

    return DecisionConstraints(
        max_risk_level=RiskLevel.LOW,
        requires_human_approval=False,
        allow_external_side_effects=False,
        allow_network_access=False,
        max_cost_units=10.0,
        max_runtime_seconds=30.0,
    )


def make_intent():
    from lyrion.capabilities.contracts import CapabilityOperation
    from lyrion.integration.proactive_execution import CapabilityIntent
    from lyrion.core.types import RiskLevel

    return CapabilityIntent(
        principal_id="lyrion-piae",
        capability_id="development.prepare",
        target_scope="lyrion/project/src",
        operation=CapabilityOperation.READ,
        data_classification=EventSensitivity.INTERNAL,
        task_id=TaskId("task-r097-3d4e"),
        risk_level=RiskLevel.LOW,
        justification="R097 fresh-admission runtime validation.",
        idempotency_key=IdempotencyKey("idem-r097-3d4e"),
    )


async def recover_into_queue(
    opportunity: Opportunity,
    *,
    recovery_time: datetime,
) -> Opportunity:
    store = InMemoryRecoveryContextStore()

    context = OpportunityRecoveryContextFactory.from_opportunity(
        opportunity,
        source_provenance_ref="r097-3d4e-runtime",
    )
    await store.create(context)

    resolver = OpportunityRecoveryContextResolver(store)
    queue = OpportunityQueue()

    reentry = OpportunityRecoveryReentryCoordinator(
        resolver=resolver,
        opportunity_queue=queue,
    )

    result = await reentry.reenter(
        str(opportunity.opportunity_id),
        current_time=recovery_time,
    )

    assert result.enqueued is True

    recovered = queue.dequeue(now=recovery_time)
    assert recovered is not None
    assert recovered.opportunity_id == opportunity.opportunity_id

    return recovered


def make_expired_capability_request(
    coordinator: ProactiveExecutionCoordinator,
    *,
    now: datetime,
):
    from lyrion.piae.contracts import (
        DecisionAction,
        DecisionCandidate,
        DecisionContext,
        DecisionReason,
    )
    from lyrion.core.types import RiskLevel
    from lyrion.piae.engine import PIAEDecisionEngine
    from lyrion.core.types import DecisionId

    opportunity = make_opportunity(
        expires_at=now + timedelta(minutes=5),
    )

    decision = PIAEDecisionEngine().decide(
        DecisionContext(
            opportunity=opportunity,
            state_records=(),
            active_task_ids=(),
            autonomy_level=AutonomyLevel.L1,
            constraints=make_constraints(),
            now=now,
        ),
        (
            DecisionCandidate(
                action=DecisionAction.EXECUTE,
                rationale=DecisionReason.EFFICIENCY,
                explanation="Controlled R097 stale-authority validation.",
                confidence=0.95,
                estimated_risk=RiskLevel.LOW,
                estimated_cost_units=0.5,
                estimated_runtime_seconds=1.0,
                requires_human_approval=False,
                has_external_side_effect=False,
                requires_network_access=False,
            ),
        ),
        decision_id=DecisionId("r097-3d4e-decision"),
        input_context_ref="r097-3d4e-runtime",
    )

    return coordinator.create_capability_request(
        decision,
        make_intent(),
        now=now,
    )


@pytest.mark.asyncio
async def test_r097_recovered_work_uses_fresh_capability_request() -> None:
    now = datetime.now(UTC)
    opportunity = make_opportunity(
        expires_at=now + timedelta(minutes=5),
    )

    recovered = await recover_into_queue(
        opportunity,
        recovery_time=now,
    )

    coordinator = make_coordinator()
    request = make_expired_capability_request(
        coordinator,
        now=now,
    )

    assert request.request_id.startswith("capreq:")
    assert str(recovered.opportunity_id) == "r097-3d4e-opportunity"

    assert request.task_id == TaskId("task-r097-3d4e")
    assert request.principal_id == "lyrion-piae"

    assert not hasattr(recovered, "authorization")
    assert not hasattr(recovered, "admission")
    assert not hasattr(recovered, "authority")


@pytest.mark.asyncio
async def test_r097_expired_authority_is_denied_by_real_gateway() -> None:
    now = datetime.now(UTC)

    coordinator = make_coordinator()

    request = make_expired_capability_request(
        coordinator,
        now=now,
    )

    expired_now = request.expires_at + timedelta(seconds=1)

    admission = coordinator.admit(
        request,
        now=expired_now,
    )

    assert admission.admitted is False
    assert "expired" in admission.authorization_reason.lower()


@pytest.mark.asyncio
async def test_r097_recovery_does_not_restore_expired_admission() -> None:
    now = datetime.now(UTC)

    opportunity = make_opportunity(
        expires_at=now + timedelta(minutes=5),
    )

    recovered = await recover_into_queue(
        opportunity,
        recovery_time=now,
    )

    coordinator = make_coordinator()

    request = make_expired_capability_request(
        coordinator,
        now=now,
    )

    expired_now = request.expires_at + timedelta(seconds=1)

    admission = coordinator.admit(
        request,
        now=expired_now,
    )

    assert recovered.opportunity_id == opportunity.opportunity_id
    assert admission.admitted is False
    assert "expired" in admission.authorization_reason.lower()


@pytest.mark.asyncio
async def test_r097_recovered_work_does_not_restore_revoked_authority() -> None:
    """Recovered work must not make a revoked request executable."""
    from lyrion.capabilities.contracts import AuthorizationDecision

    now = datetime.now(UTC)

    opportunity = make_opportunity(
        expires_at=now + timedelta(minutes=5),
    )

    recovered = await recover_into_queue(
        opportunity,
        recovery_time=now,
    )

    coordinator = make_coordinator()

    fresh_request = make_expired_capability_request(
        coordinator,
        now=now,
    )

    request_data = fresh_request.model_dump()
    request_data["authorization_decision"] = (
        AuthorizationDecision.REVOKED
    )
    request_data["authorization_granted"] = False

    revoked_request = type(fresh_request)(**request_data)

    admission = coordinator.admit(
        revoked_request,
        now=now,
    )

    assert recovered.opportunity_id == opportunity.opportunity_id
    assert revoked_request.authorization_decision is (
        AuthorizationDecision.REVOKED
    )
    assert revoked_request.authorization_granted is False
    assert admission.admitted is False
    assert admission.authorization_decision is (
        AuthorizationDecision.REVOKED
    )
    assert "revoked" in admission.authorization_reason.lower()


@pytest.mark.asyncio
async def test_r097_recovery_boundary_contains_no_authority_state() -> None:
    now = datetime.now(UTC)

    opportunity = make_opportunity(
        expires_at=now + timedelta(minutes=5),
    )

    recovered = await recover_into_queue(
        opportunity,
        recovery_time=now,
    )

    assert recovered.opportunity_id == opportunity.opportunity_id
    assert recovered.status == "OPEN"

    for forbidden in (
        "authorization",
        "admission",
        "authority",
        "lease",
        "execution_admission",
    ):
        assert not hasattr(recovered, forbidden)
