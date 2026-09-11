"""Declarative Aegis authorization policy rules."""

from enum import IntEnum

from pydantic import BaseModel, ConfigDict, Field

from lyrion.capabilities.contracts import CapabilityOperation, CapabilityRequest
from lyrion.core.types import AutonomyLevel, RiskLevel
from lyrion.events.models import EventSensitivity


class AutonomyRank(IntEnum):
    """Ordering for Lyrion autonomy levels."""

    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4
    L5 = 5


class RiskRank(IntEnum):
    """Ordering for Lyrion risk levels."""

    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


class SensitivityRank(IntEnum):
    """Ordering for event/data sensitivity levels."""

    PUBLIC = 0
    INTERNAL = 1
    SENSITIVE = 2
    HIGHLY_SENSITIVE = 3


class CapabilityRule(BaseModel):
    """Explicit authorization rule for one capability."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    capability_id: str = Field(min_length=1, max_length=500)

    allowed_principals: frozenset[str] = Field(min_length=1)
    allowed_operations: frozenset[CapabilityOperation] = Field(min_length=1)

    target_prefixes: tuple[str, ...] = Field(min_length=1)

    max_autonomy_level: AutonomyLevel
    max_risk_level: RiskLevel
    max_data_classification: EventSensitivity

    requires_human_approval: bool = False


class AegisPolicy(BaseModel):
    """Immutable versioned Aegis policy-as-code definition."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    policy_version: str = Field(min_length=1, max_length=200)

    rules: tuple[CapabilityRule, ...] = Field(min_length=1)

    default_deny: bool = True

    def rule_for(self, capability_id: str) -> CapabilityRule | None:
        """Return the rule matching a capability identifier."""
        for rule in self.rules:
            if rule.capability_id == capability_id:
                return rule
        return None


class PolicyViolation(BaseModel):
    """Structured explanation for a policy rejection."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    code: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=2000)


class PolicyEvaluation(BaseModel):
    """Deterministic result of evaluating a request against policy rules."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    allowed: bool
    requires_human_approval: bool

    policy_version: str

    rule_matched: str | None = None

    violations: tuple[PolicyViolation, ...] = Field(
        default_factory=tuple,
    )


class AegisRuleEvaluator:
    """Evaluate CapabilityRequest objects against explicit Aegis rules."""

    _autonomy_rank = {
        AutonomyLevel.L0: AutonomyRank.L0,
        AutonomyLevel.L1: AutonomyRank.L1,
        AutonomyLevel.L2: AutonomyRank.L2,
        AutonomyLevel.L3: AutonomyRank.L3,
        AutonomyLevel.L4: AutonomyRank.L4,
        AutonomyLevel.L5: AutonomyRank.L5,
    }

    _risk_rank = {
        RiskLevel.LOW: RiskRank.LOW,
        RiskLevel.MEDIUM: RiskRank.MEDIUM,
        RiskLevel.HIGH: RiskRank.HIGH,
        RiskLevel.CRITICAL: RiskRank.CRITICAL,
    }

    _sensitivity_rank = {
        EventSensitivity.PUBLIC: SensitivityRank.PUBLIC,
        EventSensitivity.INTERNAL: SensitivityRank.INTERNAL,
        EventSensitivity.SENSITIVE: SensitivityRank.SENSITIVE,
        EventSensitivity.HIGHLY_SENSITIVE: SensitivityRank.HIGHLY_SENSITIVE,
    }

    def evaluate(
        self,
        request: CapabilityRequest,
        policy: AegisPolicy,
    ) -> PolicyEvaluation:
        """Evaluate a request without granting or executing authority."""

        rule = policy.rule_for(request.capability_id)

        if rule is None:
            return PolicyEvaluation(
                allowed=False,
                requires_human_approval=False,
                policy_version=policy.policy_version,
                violations=(
                    PolicyViolation(
                        code="CAPABILITY_NOT_ALLOWED",
                        message=(
                            "No policy rule exists for the requested capability."
                        ),
                    ),
                ),
            )

        violations: list[PolicyViolation] = []

        if request.principal_id not in rule.allowed_principals:
            violations.append(
                PolicyViolation(
                    code="PRINCIPAL_NOT_ALLOWED",
                    message="Principal is not authorized for this capability.",
                )
            )

        if request.operation not in rule.allowed_operations:
            violations.append(
                PolicyViolation(
                    code="OPERATION_NOT_ALLOWED",
                    message="Requested operation is not authorized.",
                )
            )

        if not any(
            request.target_scope == prefix
            or request.target_scope.startswith(f"{prefix}/")
            for prefix in rule.target_prefixes
        ):
            violations.append(
                PolicyViolation(
                    code="TARGET_SCOPE_NOT_ALLOWED",
                    message="Requested target is outside the permitted scope.",
                )
            )

        if (
            self._autonomy_rank[request.autonomy_level]
            > self._autonomy_rank[rule.max_autonomy_level]
        ):
            violations.append(
                PolicyViolation(
                    code="AUTONOMY_EXCEEDED",
                    message="Requested autonomy exceeds the capability policy.",
                )
            )

        if self._risk_rank[request.risk_level] > self._risk_rank[rule.max_risk_level]:
            violations.append(
                PolicyViolation(
                    code="RISK_EXCEEDED",
                    message="Requested risk exceeds the capability policy.",
                )
            )

        if (
            self._sensitivity_rank[request.data_classification]
            > self._sensitivity_rank[rule.max_data_classification]
        ):
            violations.append(
                PolicyViolation(
                    code="DATA_CLASSIFICATION_EXCEEDED",
                    message=(
                        "Requested data classification exceeds the "
                        "capability policy."
                    ),
                )
            )

        return PolicyEvaluation(
            allowed=not violations,
            requires_human_approval=rule.requires_human_approval,
            policy_version=policy.policy_version,
            rule_matched=rule.capability_id,
            violations=tuple(violations),
        )


def default_aegis_policy() -> AegisPolicy:
    """Return the initial deliberately restrictive development policy."""

    return AegisPolicy(
        policy_version="aegis-policy-v1",
        default_deny=True,
        rules=(
            CapabilityRule(
                capability_id="development.prepare",
                allowed_principals=frozenset({"lyrion-piae"}),
                allowed_operations=frozenset(
                    {
                        CapabilityOperation.READ,
                        CapabilityOperation.TRANSFORM,
                    }
                ),
                target_prefixes=("lyrion/project",),
                max_autonomy_level=AutonomyLevel.L1,
                max_risk_level=RiskLevel.LOW,
                max_data_classification=EventSensitivity.INTERNAL,
                requires_human_approval=False,
            ),
        ),
    )
