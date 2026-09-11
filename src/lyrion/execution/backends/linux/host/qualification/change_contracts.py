from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ChangeImpact(StrEnum):
    """
    LYRION-defined change-impact classification.

    These classifications are project policy semantics and are not
    claimed to be Linux, Debian, Ubuntu, or industry-standard labels.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ValidationScope(StrEnum):
    """
    LYRION-defined validation scopes selected from observed change impact.
    """

    SMOKE = "smoke"
    TARGETED_REGRESSION = "targeted_regression"
    NATIVE_SECURITY_QUALIFICATION = "native_security_qualification"
    FULL_HOST_QUALIFICATION = "full_host_qualification"


@dataclass(frozen=True, slots=True)
class HostChange:
    """
    Immutable description of an observed host-state difference.

    The object describes a difference; it does not assert why the
    difference occurred.
    """

    component: str
    previous_value: str
    current_value: str
    impact: ChangeImpact
    rationale: str

    def __post_init__(self) -> None:
        if not self.component.strip():
            raise ValueError("component must not be blank")
        if not self.rationale.strip():
            raise ValueError("rationale must not be blank")


@dataclass(frozen=True, slots=True)
class ValidationSelection:
    """
    Deterministic validation scope selected from host changes.
    """

    scope: ValidationScope
    changes: tuple[HostChange, ...]
    rationale: str

    def __post_init__(self) -> None:
        if not self.rationale.strip():
            raise ValueError("rationale must not be blank")


@dataclass(frozen=True, slots=True)
class ChangeClassification:
    """
    Deterministic result of classifying observed host changes.
    """

    impact: ChangeImpact
    changes: tuple[HostChange, ...]
    validation: ValidationSelection

    @property
    def requires_native_security_qualification(self) -> bool:
        return self.impact in {
            ChangeImpact.HIGH,
            ChangeImpact.CRITICAL,
        }

    @property
    def requires_full_host_qualification(self) -> bool:
        return self.impact is ChangeImpact.CRITICAL
