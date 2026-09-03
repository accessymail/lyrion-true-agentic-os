"""Shared domain types for Lyrion Intelligence OS."""

from enum import StrEnum
from typing import NewType

EventId = NewType("EventId", str)
TaskId = NewType("TaskId", str)
OpportunityId = NewType("OpportunityId", str)
DecisionId = NewType("DecisionId", str)
CorrelationId = NewType("CorrelationId", str)
IdempotencyKey = NewType("IdempotencyKey", str)


class AutonomyLevel(StrEnum):
    """Approved PIAE autonomy levels."""

    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"


class DecisionAction(StrEnum):
    """Actions PIAE may select."""

    WAIT = "WAIT"
    SUGGEST = "SUGGEST"
    PREPARE = "PREPARE"
    EXECUTE = "EXECUTE"
    ESCALATE = "ESCALATE"
    DENY = "DENY"


class RiskLevel(StrEnum):
    """Normalized action/data risk levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ExecutionTarget(StrEnum):
    """Supported execution environments."""

    LOCAL_CPU = "LOCAL_CPU"
    LOCAL_GPU = "LOCAL_GPU"
    CLOUD_API = "CLOUD_API"
    CLOUD_GPU = "CLOUD_GPU"
    REMOTE_SANDBOX = "REMOTE_SANDBOX"
