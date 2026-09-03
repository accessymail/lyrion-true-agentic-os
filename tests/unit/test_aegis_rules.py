"""Adversarial unit tests for Aegis policy-as-code rules."""

import pytest
from pydantic import ValidationError

from lyrion.capabilities.contracts import CapabilityOperation, CapabilityRequest
from lyrion.core.types import (
    AutonomyLevel,
    DecisionId,
    IdempotencyKey,
    RiskLevel,
    TaskId,
)
from lyrion.events.models import EventSensitivity
from lyrion.security.rules import (
    AegisPolicy,
    AegisRuleEvaluator,
    CapabilityRule,
    PolicyEvaluation,
    PolicyViolation,
    default_aegis_policy,
)


def make_request(**overrides: object) -> CapabilityRequest:
    """Create a valid baseline capability request."""
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)

    values: dict[str, object] = {
        "request_id": "rules_test_request",
        "decision_id": DecisionId("rules_test_decision"),
        "task_id": TaskId("rules_test_task"),
        "principal_id": "lyrion-piae",
        "capability_id": "development.prepare",
        "target_scope": "lyrion/project/src",
        "operation": CapabilityOperation.READ,
        "data_classification": EventSensitivity.INTERNAL,
        "autonomy_level": AutonomyLevel.L1,
        "risk_level": RiskLevel.LOW,
        "policy_version": "aegis-policy-v1",
        "idempotency_key": IdempotencyKey("rules_test_idempotency"),
        "requested_at": now,
        "expires_at": now + timedelta(minutes=5),
        "justification": "Aegis rule test.",
    }

    values.update(overrides)
    return CapabilityRequest(**values)


def test_default_policy_is_versioned() -> None:
    """The default policy must expose an explicit version."""
    policy = default_aegis_policy()

    assert policy.policy_version == "aegis-policy-v1"
    assert policy.default_deny is True


def test_capability_rule_is_immutable() -> None:
    """Capability rules must not be mutable."""
    rule = CapabilityRule(
        capability_id="test",
        allowed_principals=frozenset({"principal"}),
        allowed_operations=frozenset({CapabilityOperation.READ}),
        target_prefixes=("scope",),
        max_autonomy_level=AutonomyLevel.L1,
        max_risk_level=RiskLevel.LOW,
        max_data_classification=EventSensitivity.INTERNAL,
    )

    with pytest.raises(ValidationError):
        rule.capability_id = "changed"


def test_policy_is_immutable() -> None:
    """Policies must not be mutable."""
    policy = default_aegis_policy()

    with pytest.raises(ValidationError):
        policy.policy_version = "changed"


def test_policy_rejects_unknown_fields() -> None:
    """Policies must reject undeclared fields."""
    with pytest.raises(ValidationError):
        AegisPolicy(
            policy_version="test-v1",
            rules=(),
            unknown_field="not-allowed",
        )


def test_rule_for_returns_matching_rule() -> None:
    """A policy should locate rules by capability identifier."""
    policy = default_aegis_policy()

    rule = policy.rule_for("development.prepare")

    assert rule is not None
    assert rule.capability_id == "development.prepare"


def test_rule_for_returns_none_for_unknown_capability() -> None:
    """Unknown capabilities must have no matching rule."""
    policy = default_aegis_policy()

    assert policy.rule_for("unknown.capability") is None


def test_allowed_principal_and_operation() -> None:
    """Matching principal and operation should satisfy those dimensions."""
    request = make_request()

    evaluation = AegisRuleEvaluator().evaluate(
        request,
        default_aegis_policy(),
    )

    assert evaluation.allowed is True
    assert evaluation.violations == ()


def test_wrong_principal_is_denied() -> None:
    """A principal outside the allow-list must be denied."""
    request = make_request(
        principal_id="unauthorized-principal",
    )

    evaluation = AegisRuleEvaluator().evaluate(
        request,
        default_aegis_policy(),
    )

    assert evaluation.allowed is False
    assert any(
        violation.code == "PRINCIPAL_NOT_ALLOWED"
        for violation in evaluation.violations
    )


def test_wrong_operation_is_denied() -> None:
    """An operation outside the capability allow-list must be denied."""
    request = make_request(
        operation=CapabilityOperation.DELETE,
    )

    evaluation = AegisRuleEvaluator().evaluate(
        request,
        default_aegis_policy(),
    )

    assert evaluation.allowed is False
    assert any(
        violation.code == "OPERATION_NOT_ALLOWED"
        for violation in evaluation.violations
    )


def test_target_scope_is_prefix_bounded() -> None:
    """Nested paths under an allowed prefix should remain permitted."""
    request = make_request(
        target_scope="lyrion/project/src/core",
    )

    evaluation = AegisRuleEvaluator().evaluate(
        request,
        default_aegis_policy(),
    )

    assert evaluation.allowed is True


def test_target_scope_escalation_is_denied() -> None:
    """A target outside the allowed prefix must be denied."""
    request = make_request(
        target_scope="lyrion/project-other",
    )

    evaluation = AegisRuleEvaluator().evaluate(
        request,
        default_aegis_policy(),
    )

    assert evaluation.allowed is False
    assert any(
        violation.code == "TARGET_SCOPE_NOT_ALLOWED"
        for violation in evaluation.violations
    )


def test_autonomy_above_rule_is_denied() -> None:
    """Requested autonomy above the rule maximum must be denied."""
    request = make_request(
        autonomy_level=AutonomyLevel.L3,
    )

    evaluation = AegisRuleEvaluator().evaluate(
        request,
        default_aegis_policy(),
    )

    assert evaluation.allowed is False
    assert any(
        violation.code == "AUTONOMY_EXCEEDED"
        for violation in evaluation.violations
    )


def test_risk_above_rule_is_denied() -> None:
    """Requested risk above the rule maximum must be denied."""
    request = make_request(
        risk_level=RiskLevel.HIGH,
    )

    evaluation = AegisRuleEvaluator().evaluate(
        request,
        default_aegis_policy(),
    )

    assert evaluation.allowed is False
    assert any(
        violation.code == "RISK_EXCEEDED"
        for violation in evaluation.violations
    )


def test_data_classification_above_rule_is_denied() -> None:
    """Sensitive data beyond the rule boundary must be denied."""
    request = make_request(
        data_classification=EventSensitivity.SENSITIVE,
    )

    evaluation = AegisRuleEvaluator().evaluate(
        request,
        default_aegis_policy(),
    )

    assert evaluation.allowed is False
    assert any(
        violation.code == "DATA_CLASSIFICATION_EXCEEDED"
        for violation in evaluation.violations
    )


def test_multiple_policy_violations_are_preserved() -> None:
    """Multiple independent violations must remain observable."""
    request = make_request(
        principal_id="wrong-principal",
        operation=CapabilityOperation.DELETE,
        target_scope="protected/resource",
        autonomy_level=AutonomyLevel.L3,
        risk_level=RiskLevel.HIGH,
        data_classification=EventSensitivity.SENSITIVE,
    )

    evaluation = AegisRuleEvaluator().evaluate(
        request,
        default_aegis_policy(),
    )

    codes = {violation.code for violation in evaluation.violations}

    assert evaluation.allowed is False
    assert "PRINCIPAL_NOT_ALLOWED" in codes
    assert "OPERATION_NOT_ALLOWED" in codes
    assert "TARGET_SCOPE_NOT_ALLOWED" in codes
    assert "AUTONOMY_EXCEEDED" in codes
    assert "RISK_EXCEEDED" in codes
    assert "DATA_CLASSIFICATION_EXCEEDED" in codes


def test_unknown_capability_is_default_deny() -> None:
    """Capabilities without explicit rules must be denied."""
    request = make_request(
        capability_id="unregistered.capability",
    )

    evaluation = AegisRuleEvaluator().evaluate(
        request,
        default_aegis_policy(),
    )

    assert evaluation.allowed is False
    assert evaluation.rule_matched is None
    assert evaluation.violations == (
        PolicyViolation(
            code="CAPABILITY_NOT_ALLOWED",
            message="No policy rule exists for the requested capability.",
        ),
    )


def test_policy_version_is_preserved() -> None:
    """Policy evaluation must report the exact policy version used."""
    policy = default_aegis_policy()
    request = make_request()

    evaluation = AegisRuleEvaluator().evaluate(
        request,
        policy,
    )

    assert evaluation.policy_version == policy.policy_version


def test_rule_human_approval_flag_is_preserved() -> None:
    """Rule-level approval requirements must remain explicit."""
    rule = CapabilityRule(
        capability_id="approval.required",
        allowed_principals=frozenset({"lyrion-piae"}),
        allowed_operations=frozenset({CapabilityOperation.EXECUTE}),
        target_prefixes=("protected",),
        max_autonomy_level=AutonomyLevel.L2,
        max_risk_level=RiskLevel.MEDIUM,
        max_data_classification=EventSensitivity.SENSITIVE,
        requires_human_approval=True,
    )

    policy = AegisPolicy(
        policy_version="aegis-test-v1",
        rules=(rule,),
        default_deny=True,
    )

    request = make_request(
        capability_id="approval.required",
        operation=CapabilityOperation.EXECUTE,
        target_scope="protected/resource",
        autonomy_level=AutonomyLevel.L2,
        risk_level=RiskLevel.MEDIUM,
        data_classification=EventSensitivity.SENSITIVE,
        policy_version="aegis-test-v1",
    )

    evaluation = AegisRuleEvaluator().evaluate(
        request,
        policy,
    )

    assert evaluation.allowed is True
    assert evaluation.requires_human_approval is True


def test_policy_evaluation_is_immutable() -> None:
    """Policy evaluations must not be mutable."""
    evaluation = PolicyEvaluation(
        allowed=True,
        requires_human_approval=False,
        policy_version="aegis-test-v1",
    )

    with pytest.raises(ValidationError):
        evaluation.allowed = False


def test_policy_violation_is_immutable() -> None:
    """Policy violations must not be mutable."""
    violation = PolicyViolation(
        code="TEST",
        message="Test violation.",
    )

    with pytest.raises(ValidationError):
        violation.code = "CHANGED"


def test_rule_evaluation_is_deterministic() -> None:
    """Equal inputs must produce equal policy semantics."""
    request = make_request()
    policy = default_aegis_policy()
    evaluator = AegisRuleEvaluator()

    first = evaluator.evaluate(request, policy)
    second = evaluator.evaluate(request, policy)

    assert first == second
