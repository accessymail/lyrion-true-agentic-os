"""Immutable contracts for Linux host qualification policy selection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from lyrion.execution.backends.linux.host.negotiation.contracts import (
    CapabilityRequirementSet,
)
from lyrion.execution.backends.linux.host.profiles.contracts import (
    LinuxArchitecture,
    LinuxDistribution,
    LinuxDistributionFamily,
)


class LinuxHostPolicyScope(StrEnum):
    """Scope used to match a qualification policy."""

    EXACT = "exact"
    DISTRIBUTION = "distribution"
    FAMILY_ARCHITECTURE = "family_architecture"
    GENERIC_ARCHITECTURE = "generic_architecture"


@dataclass(frozen=True, slots=True)
class LinuxHostPolicyKey:
    """Immutable deterministic identity for policy selection.

    None values are policy-selection wildcards only. They never represent
    satisfied capabilities.
    """

    distribution: LinuxDistribution | None = None
    distribution_family: LinuxDistributionFamily | None = None
    architecture: LinuxArchitecture | None = None

    def __post_init__(self) -> None:
        if self.distribution is not None and self.distribution_family is not None:
            raise ValueError(
                "A policy key cannot specify both distribution and "
                "distribution_family."
            )

        if (
            self.distribution is None
            and self.distribution_family is None
            and self.architecture is None
        ):
            raise ValueError(
                "A policy key must constrain at least one dimension."
            )

    @property
    def scope(self) -> LinuxHostPolicyScope:
        if self.distribution is not None and self.architecture is not None:
            return LinuxHostPolicyScope.EXACT

        if self.distribution is not None:
            return LinuxHostPolicyScope.DISTRIBUTION

        if (
            self.distribution_family is not None
            and self.architecture is not None
        ):
            return LinuxHostPolicyScope.FAMILY_ARCHITECTURE

        return LinuxHostPolicyScope.GENERIC_ARCHITECTURE

    @property
    def policy_id(self) -> str:
        distribution = (
            self.distribution.value if self.distribution is not None else "-"
        )
        family = (
            self.distribution_family.value
            if self.distribution_family is not None
            else "-"
        )
        architecture = (
            self.architecture.value if self.architecture is not None else "-"
        )

        return (
            f"linux-policy:{self.scope.value}:"
            f"{distribution}:{family}:{architecture}"
        )


@dataclass(frozen=True, slots=True)
class LinuxHostQualificationPolicy:
    """Immutable mapping from host identity dimensions to requirements."""

    key: LinuxHostPolicyKey
    requirements: CapabilityRequirementSet
    policy_id: str
    policy_version: str = "1"

    def __post_init__(self) -> None:
        if self.policy_id != self.key.policy_id:
            raise ValueError(
                "policy_id must exactly match the deterministic policy key ID."
            )

        if not isinstance(self.policy_version, str):
            raise TypeError("policy_version must be a string")

        if not self.policy_version.strip():
            raise ValueError("policy_version must not be blank")

        if self.policy_version != self.policy_version.strip():
            raise ValueError(
                "policy_version must not contain surrounding whitespace"
            )


@dataclass(frozen=True, slots=True)
class LinuxHostPolicyResolution:
    """Deterministic policy-selection result.

    Resolution does not mean qualification, authorization, enforcement,
    or production certification.
    """

    policy: LinuxHostQualificationPolicy | None
    matched: bool
    candidate_policy_ids: tuple[str, ...]

    @property
    def policy_id(self) -> str | None:
        return self.policy.policy_id if self.policy is not None else None
