from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from lyrion.core.types import AutonomyLevel
from lyrion.piae.contracts import (
    DecisionConstraints,
    DecisionContext,
    Opportunity,
)
from lyrion.rpii.contracts import (
    RPIIContext,
    RPIICycleResult,
    RPIIStage,
    RPIIStatus,
)

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


def make_opportunity() -> Opportunity:
    fields = Opportunity.model_fields
    values: dict[str, object] = {}

    for name, field in fields.items():
        if field.default is not None:
            values[name] = field.default
        elif field.default_factory is not None:
            values[name] = field.default_factory()
        else:
            values[name] = None

    return Opportunity.model_construct(**values)


def make_decision_context() -> DecisionContext:
    values = {
        "opportunity": make_opportunity(),
        "state_records": (),
        "active_task_ids": (),
        "autonomy_level": AutonomyLevel.L1,
        "constraints": DecisionConstraints(),
        "now": NOW,
    }

    return DecisionContext.model_validate(values)


def make_decision_result() -> object:
    from lyrion.core.types import DecisionAction, DecisionId
    from lyrion.piae.contracts import DecisionReason, DecisionResult, PolicyResult

    return DecisionResult(
        decision_id=DecisionId("decision-1"),
        input_context_ref="rpii-test",
        opportunity_ref="opportunity-1",
        selected_action=DecisionAction.WAIT,
        alternative_actions=(),
        utility_estimate=0.0,
        interruption_cost=0.0,
        risk_estimate=0.0,
        autonomy_level=AutonomyLevel.L1,
        authorization_result=PolicyResult.NOT_EVALUATED,
        policy_result=PolicyResult.NOT_EVALUATED,
        confidence=1.0,
        reason_codes=(DecisionReason.INSUFFICIENT_CONFIDENCE,),
        authorization_required=False,
        authorization_granted=False,
        candidate_count=0,
        correlation_id=None,
        idempotency_key=None,
        expires_at=None,
        decided_at=NOW,
    )


def make_cycle_result(**overrides: object) -> RPIICycleResult:
    values: dict[str, object] = {
        "interaction_id": "interaction-1",
        "session_id": "session-1",
        "status": RPIIStatus.COMPLETED,
        "stage": RPIIStage.EVALUATION,
        "decision": make_decision_result(),
        "started_at": NOW,
    }
    values.update(overrides)

    return RPIICycleResult.model_validate(values)


def test_rpii_stage_values_are_explicit() -> None:
    assert tuple(stage.value for stage in RPIIStage) == (
        "INTERACTION",
        "COGNITION",
        "DECISION",
        "AUTHORIZATION",
        "EXECUTION",
        "VERIFICATION",
        "FEEDBACK",
        "EVALUATION",
    )


def test_rpii_status_values_are_explicit() -> None:
    assert tuple(status.value for status in RPIIStatus) == (
        "COMPLETED",
        "WAITING",
        "DENIED",
        "FAILED",
        "DEGRADED",
    )


def test_context_is_immutable() -> None:
    context = RPIIContext(
        interaction_id="interaction-1",
        session_id="session-1",
        decision_context=make_decision_context(),
        created_at=NOW,
    )

    with pytest.raises(ValidationError):
        context.interaction_id = "attacker-controlled"


def test_context_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        RPIIContext.model_validate(
            {
                "interaction_id": "interaction-1",
                "session_id": "session-1",
                "decision_context": make_decision_context(),
                "created_at": NOW,
                "execution_authorized": True,
            }
        )


@pytest.mark.parametrize(
    "field",
    ("interaction_id", "session_id"),
)
def test_context_rejects_blank_identifiers(field: str) -> None:
    values: dict[str, object] = {
        "interaction_id": "interaction-1",
        "session_id": "session-1",
        "decision_context": make_decision_context(),
        "created_at": NOW,
    }
    values[field] = ""

    with pytest.raises(ValidationError):
        RPIIContext.model_validate(values)


def test_context_rejects_oversized_interaction_id() -> None:
    with pytest.raises(ValidationError):
        RPIIContext.model_validate(
            {
                "interaction_id": "x" * 201,
                "session_id": "session-1",
                "decision_context": make_decision_context(),
                "created_at": NOW,
            }
        )


def test_context_rejects_naive_created_at() -> None:
    with pytest.raises(ValidationError):
        RPIIContext.model_validate(
            {
                "interaction_id": "interaction-1",
                "session_id": "session-1",
                "decision_context": make_decision_context(),
                "created_at": datetime(2026, 9, 4, 12, 0),
            }
        )


def test_result_is_immutable() -> None:
    result = make_cycle_result()

    with pytest.raises(ValidationError):
        result.interaction_id = "attacker-controlled"


def test_result_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        RPIICycleResult.model_validate(
            {
                "interaction_id": "interaction-1",
                "session_id": "session-1",
                "status": RPIIStatus.COMPLETED,
                "stage": RPIIStage.EVALUATION,
                "decision": make_decision_result(),
                "started_at": NOW,
                "execution_authorized": True,
            }
        )


def test_result_rejects_naive_started_at() -> None:
    with pytest.raises(ValidationError):
        RPIICycleResult.model_validate(
            {
                "interaction_id": "interaction-1",
                "session_id": "session-1",
                "status": RPIIStatus.COMPLETED,
                "stage": RPIIStage.EVALUATION,
                "decision": make_decision_result(),
                "started_at": datetime(2026, 9, 4, 12, 0),
            }
        )


def test_result_rejects_naive_completed_at() -> None:
    with pytest.raises(ValidationError):
        RPIICycleResult.model_validate(
            {
                "interaction_id": "interaction-1",
                "session_id": "session-1",
                "status": RPIIStatus.COMPLETED,
                "stage": RPIIStage.EVALUATION,
                "decision": make_decision_result(),
                "started_at": NOW,
                "completed_at": datetime(2026, 9, 4, 12, 1),
            }
        )


def test_result_rejects_completion_before_start() -> None:
    with pytest.raises(ValidationError):
        RPIICycleResult.model_validate(
            {
                "interaction_id": "interaction-1",
                "session_id": "session-1",
                "status": RPIIStatus.COMPLETED,
                "stage": RPIIStage.EVALUATION,
                "decision": make_decision_result(),
                "started_at": NOW,
                "completed_at": NOW - timedelta(seconds=1),
            }
        )


@pytest.mark.parametrize(
    "field",
    ("interaction_id", "session_id"),
)
def test_result_rejects_blank_identifiers(field: str) -> None:
    values: dict[str, object] = {
        "interaction_id": "interaction-1",
        "session_id": "session-1",
        "status": RPIIStatus.COMPLETED,
        "stage": RPIIStage.EVALUATION,
        "decision": make_decision_result(),
        "started_at": NOW,
    }
    values[field] = ""

    with pytest.raises(ValidationError):
        RPIICycleResult.model_validate(values)


def test_result_does_not_expose_authority_fields() -> None:
    result = make_cycle_result()
    payload = result.model_dump()

    assert "authorization_granted" not in payload
    assert "execution_authorized" not in payload
    assert "capability_granted" not in payload
    assert "execution_authority" not in payload


def test_context_rejects_indirect_authority_field_injection() -> None:
    payload = {
        "interaction_id": "interaction-1",
        "session_id": "session-1",
        "decision_context": make_decision_context(),
        "created_at": NOW,
        "authority": {
            "execution_authorized": True,
            "capability_granted": True,
        },
    }

    with pytest.raises(ValidationError):
        RPIIContext.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    ("started_at", "completed_at"),
)
def test_result_rejects_naive_nested_lifecycle_timestamp(
    field: str,
) -> None:
    values: dict[str, object] = {
        "interaction_id": "interaction-1",
        "session_id": "session-1",
        "status": RPIIStatus.COMPLETED,
        "stage": RPIIStage.EVALUATION,
        "decision": make_decision_result(),
        "started_at": NOW,
    }

    if field == "completed_at":
        values[field] = datetime(2026, 9, 4, 12, 1)
    else:
        values[field] = datetime(2026, 9, 4, 12, 0)

    with pytest.raises(ValidationError):
        RPIICycleResult.model_validate(values)


def test_result_rejects_invalid_nested_decision_result() -> None:
    decision = make_decision_result().model_dump()
    decision.pop("decision_id")

    with pytest.raises(ValidationError):
        RPIICycleResult.model_validate(
            {
                "interaction_id": "interaction-1",
                "session_id": "session-1",
                "status": RPIIStatus.COMPLETED,
                "stage": RPIIStage.EVALUATION,
                "decision": decision,
                "started_at": NOW,
            }
        )


def test_result_rejects_nested_decision_authority_escalation() -> None:
    decision = make_decision_result().model_dump(
        mode="python",
    )
    decision["execution_authorized"] = True

    with pytest.raises(ValidationError):
        RPIICycleResult.model_validate(
            {
                "interaction_id": "interaction-1",
                "session_id": "session-1",
                "status": RPIIStatus.COMPLETED,
                "stage": RPIIStage.EVALUATION,
                "decision": decision,
                "started_at": NOW,
            }
        )


def test_result_rejects_nested_capability_request_authority_escalation() -> None:
    request = {
        "request_id": "request-1",
        "decision_id": make_decision_result().decision_id,
        "task_id": "task-1",
        "principal_id": "principal-1",
        "capability_id": "capability-1",
        "target_scope": "test",
        "operation": "READ",
        "data_classification": "PUBLIC",
        "autonomy_level": AutonomyLevel.L1,
        "risk_level": "LOW",
        "policy_version": "policy-1",
        "idempotency_key": "idempotency-1",
        "requested_at": NOW,
        "expires_at": NOW + timedelta(minutes=5),
        "justification": "contract test",
        "execution_authorized": True,
    }

    with pytest.raises(ValidationError):
        RPIICycleResult.model_validate(
            {
                "interaction_id": "interaction-1",
                "session_id": "session-1",
                "status": RPIIStatus.WAITING,
                "stage": RPIIStage.AUTHORIZATION,
                "decision": make_decision_result(),
                "capability_request": request,
                "started_at": NOW,
            }
        )


def test_result_rejects_nested_execution_admission_authority_escalation() -> None:
    admission = {
        "request_id": "request-1",
        "capability_id": "capability-1",
        "target_scope": "test",
        "admitted": True,
        "authorization_decision": "ALLOW",
        "authorization_reason": "contract test",
        "policy_version": "policy-1",
        "admitted_at": NOW,
        "execution_request": {
            "request_id": "request-1",
            "execution_id": "execution-1",
        },
        "execution_authorized": True,
    }

    with pytest.raises(ValidationError):
        RPIICycleResult.model_validate(
            {
                "interaction_id": "interaction-1",
                "session_id": "session-1",
                "status": RPIIStatus.WAITING,
                "stage": RPIIStage.AUTHORIZATION,
                "decision": make_decision_result(),
                "admission": admission,
                "started_at": NOW,
            }
        )


def test_result_accepts_stage_status_without_granting_authority() -> None:
    result = RPIICycleResult.model_validate(
        {
            "interaction_id": "interaction-1",
            "session_id": "session-1",
            "status": RPIIStatus.COMPLETED,
            "stage": RPIIStage.EXECUTION,
            "decision": make_decision_result(),
            "started_at": NOW,
        }
    )

    assert result.status is RPIIStatus.COMPLETED
    assert result.stage is RPIIStage.EXECUTION
    assert "execution_authorized" not in result.model_dump()
    assert "execution_authority" not in result.model_dump()


def test_result_preserves_identifier_references_without_authorizing_them() -> None:
    result = RPIICycleResult.model_validate(
        {
            "interaction_id": "attacker-controlled-reference",
            "session_id": "attacker-controlled-session",
            "status": RPIIStatus.WAITING,
            "stage": RPIIStage.AUTHORIZATION,
            "decision": make_decision_result(),
            "started_at": NOW,
        }
    )

    assert result.interaction_id == "attacker-controlled-reference"
    assert result.session_id == "attacker-controlled-session"
    assert "execution_authorized" not in result.model_dump()


def test_result_serialization_round_trip_does_not_create_authority() -> None:
    result = make_cycle_result()

    payload = result.model_dump(mode="python")
    payload["execution_authorized"] = True

    with pytest.raises(ValidationError):
        RPIICycleResult.model_validate(payload)


def test_result_serialization_round_trip_preserves_authority_neutral_shape() -> None:
    result = make_cycle_result()

    restored = RPIICycleResult.model_validate(
        result.model_dump(mode="python"),
    )

    assert restored == result
    assert "execution_authorized" not in restored.model_dump()
    assert "capability_granted" not in restored.model_dump()
    assert "execution_authority" not in restored.model_dump()


@pytest.mark.parametrize(
    "identifier",
    (
        "interaction_id",
        "session_id",
    ),
)
def test_result_does_not_treat_identifier_substitution_as_authority(
    identifier: str,
) -> None:
    values: dict[str, object] = {
        "interaction_id": "interaction-1",
        "session_id": "session-1",
        "status": RPIIStatus.COMPLETED,
        "stage": RPIIStage.EVALUATION,
        "decision": make_decision_result(),
        "started_at": NOW,
    }

    values[identifier] = "attacker-controlled-reference"

    result = RPIICycleResult.model_validate(values)

    assert getattr(result, identifier) == "attacker-controlled-reference"


def test_result_rejects_indirect_execution_authority_field() -> None:
    payload = make_cycle_result().model_dump(mode="python")
    payload["execution"] = {
        "authorized": True,
        "capability_granted": True,
    }

    with pytest.raises(ValidationError):
        RPIICycleResult.model_validate(payload)
