"""Read-only deterministic Linux host qualification policy registry."""

from __future__ import annotations

from collections.abc import Iterable

from lyrion.execution.backends.linux.host.policy.contracts import (
    LinuxHostPolicyKey,
    LinuxHostPolicyResolution,
    LinuxHostQualificationPolicy,
)
from lyrion.execution.backends.linux.host.profiles.contracts import (
    LinuxArchitecture,
    LinuxDistribution,
    LinuxDistributionFamily,
)


class LinuxHostPolicyRegistryError(ValueError):
    """Raised when a policy registry invariant is violated."""


class LinuxHostQualificationPolicyRegistry:
    """Read-only policy registry.

    The registry selects a declared requirement set based on observed host
    identity. It does not evaluate capabilities, authorize execution,
    enforce controls, execute processes, or mutate the host.
    """

    def __init__(
        self,
        policies: Iterable[LinuxHostQualificationPolicy],
    ) -> None:
        materialized = tuple(policies)

        by_id: dict[str, LinuxHostQualificationPolicy] = {}

        for policy in materialized:
            if policy.policy_id in by_id:
                raise LinuxHostPolicyRegistryError(
                    f"Duplicate policy ID: {policy.policy_id}"
                )

            by_id[policy.policy_id] = policy

        self._policies = tuple(
            sorted(
                materialized,
                key=lambda policy: policy.policy_id,
            )
        )
        self._by_id = by_id

    @property
    def policies(self) -> tuple[LinuxHostQualificationPolicy, ...]:
        return self._policies

    @property
    def policy_ids(self) -> tuple[str, ...]:
        return tuple(policy.policy_id for policy in self._policies)

    def resolve(
        self,
        *,
        distribution: LinuxDistribution,
        distribution_family: LinuxDistributionFamily,
        architecture: LinuxArchitecture,
    ) -> LinuxHostPolicyResolution:
        """Resolve the highest-precedence applicable policy.

        Precedence:
          1. exact distribution + architecture
          2. distribution-only
          3. distribution-family + architecture
          4. generic architecture
        """

        candidates = (
            LinuxHostPolicyKey(
                distribution=distribution,
                architecture=architecture,
            ),
            LinuxHostPolicyKey(
                distribution=distribution,
            ),
            LinuxHostPolicyKey(
                distribution_family=distribution_family,
                architecture=architecture,
            ),
            LinuxHostPolicyKey(
                architecture=architecture,
            ),
        )

        candidate_policy_ids = tuple(
            key.policy_id for key in candidates
        )

        for key in candidates:
            policy = self._by_id.get(key.policy_id)

            if policy is not None:
                return LinuxHostPolicyResolution(
                    policy=policy,
                    matched=True,
                    candidate_policy_ids=candidate_policy_ids,
                )

        return LinuxHostPolicyResolution(
            policy=None,
            matched=False,
            candidate_policy_ids=candidate_policy_ids,
        )
