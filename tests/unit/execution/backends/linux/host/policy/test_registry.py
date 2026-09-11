from __future__ import annotations

import pytest

from lyrion.execution.backends.linux.host.contracts import (
    CapabilityState,
    HostPrimitive,
)
from lyrion.execution.backends.linux.host.negotiation.contracts import (
    CapabilityRequirement,
    CapabilityRequirementMode,
    CapabilityRequirementSet,
)
from lyrion.execution.backends.linux.host.policy.contracts import (
    LinuxHostPolicyKey,
    LinuxHostPolicyScope,
    LinuxHostQualificationPolicy,
)
from lyrion.execution.backends.linux.host.policy.registry import (
    LinuxHostPolicyRegistryError,
    LinuxHostQualificationPolicyRegistry,
)
from lyrion.execution.backends.linux.host.profiles.contracts import (
    LinuxArchitecture,
    LinuxDistribution,
    LinuxDistributionFamily,
)


def requirement_set(requirement_id: str) -> CapabilityRequirementSet:
    requirement = CapabilityRequirement(
        requirement_id=requirement_id,
        primitive=HostPrimitive.CGROUPS_V2,
        mode=CapabilityRequirementMode.REQUIRED,
        acceptable_states=(CapabilityState.AVAILABLE,),
        rationale="Test policy requirement.",
    )

    return CapabilityRequirementSet((requirement,))


def policy(
    key: LinuxHostPolicyKey,
    requirement_id: str,
) -> LinuxHostQualificationPolicy:
    return LinuxHostQualificationPolicy(
        key=key,
        requirements=requirement_set(requirement_id),
        policy_id=key.policy_id,
    )


def test_policy_key_is_deterministic() -> None:
    key = LinuxHostPolicyKey(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
    )

    assert key.scope is LinuxHostPolicyScope.EXACT
    assert key.policy_id == "linux-policy:exact:ubuntu:-:x86_64"


def test_distribution_only_key_has_distribution_scope() -> None:
    key = LinuxHostPolicyKey(
        distribution=LinuxDistribution.UBUNTU,
    )

    assert key.scope is LinuxHostPolicyScope.DISTRIBUTION
    assert key.policy_id == "linux-policy:distribution:ubuntu:-:-"


def test_family_architecture_key_has_family_scope() -> None:
    key = LinuxHostPolicyKey(
        distribution_family=LinuxDistributionFamily.DEBIAN,
        architecture=LinuxArchitecture.AARCH64,
    )

    assert key.scope is LinuxHostPolicyScope.FAMILY_ARCHITECTURE
    assert key.policy_id == (
        "linux-policy:family_architecture:-:debian:aarch64"
    )


def test_conflicting_distribution_dimensions_are_rejected() -> None:
    with pytest.raises(ValueError):
        LinuxHostPolicyKey(
            distribution=LinuxDistribution.UBUNTU,
            distribution_family=LinuxDistributionFamily.DEBIAN,
            architecture=LinuxArchitecture.X86_64,
        )


def test_unconstrained_key_is_rejected() -> None:
    with pytest.raises(ValueError):
        LinuxHostPolicyKey()


def test_duplicate_policy_ids_are_rejected() -> None:
    key = LinuxHostPolicyKey(
        distribution=LinuxDistribution.UBUNTU,
        architecture=LinuxArchitecture.X86_64,
    )

    first = policy(key, "requirement-a")
    second = policy(key, "requirement-a")

    with pytest.raises(LinuxHostPolicyRegistryError):
        LinuxHostQualificationPolicyRegistry((first, second))


def test_exact_policy_has_highest_precedence() -> None:
    exact = policy(
        LinuxHostPolicyKey(
            distribution=LinuxDistribution.UBUNTU,
            architecture=LinuxArchitecture.X86_64,
        ),
        "requirement-exact",
    )
    distro = policy(
        LinuxHostPolicyKey(
            distribution=LinuxDistribution.UBUNTU,
        ),
        "requirement-distro",
    )
    family = policy(
        LinuxHostPolicyKey(
            distribution_family=LinuxDistributionFamily.DEBIAN,
            architecture=LinuxArchitecture.X86_64,
        ),
        "requirement-family",
    )
    generic = policy(
        LinuxHostPolicyKey(
            architecture=LinuxArchitecture.X86_64,
        ),
        "requirement-generic",
    )

    registry = LinuxHostQualificationPolicyRegistry(
        (generic, family, distro, exact)
    )

    result = registry.resolve(
        distribution=LinuxDistribution.UBUNTU,
        distribution_family=LinuxDistributionFamily.DEBIAN,
        architecture=LinuxArchitecture.X86_64,
    )

    assert result.matched is True
    assert result.policy is exact


def test_distribution_only_fallback_precedes_family_policy() -> None:
    distro = policy(
        LinuxHostPolicyKey(
            distribution=LinuxDistribution.UBUNTU,
        ),
        "requirement-distro",
    )
    family = policy(
        LinuxHostPolicyKey(
            distribution_family=LinuxDistributionFamily.DEBIAN,
            architecture=LinuxArchitecture.X86_64,
        ),
        "requirement-family",
    )

    registry = LinuxHostQualificationPolicyRegistry((family, distro))

    result = registry.resolve(
        distribution=LinuxDistribution.UBUNTU,
        distribution_family=LinuxDistributionFamily.DEBIAN,
        architecture=LinuxArchitecture.X86_64,
    )

    assert result.policy is distro


def test_family_architecture_fallback_precedes_generic() -> None:
    family = policy(
        LinuxHostPolicyKey(
            distribution_family=LinuxDistributionFamily.DEBIAN,
            architecture=LinuxArchitecture.AARCH64,
        ),
        "requirement-family",
    )
    generic = policy(
        LinuxHostPolicyKey(
            architecture=LinuxArchitecture.AARCH64,
        ),
        "requirement-generic",
    )

    registry = LinuxHostQualificationPolicyRegistry((generic, family))

    result = registry.resolve(
        distribution=LinuxDistribution.KALI,
        distribution_family=LinuxDistributionFamily.DEBIAN,
        architecture=LinuxArchitecture.AARCH64,
    )

    assert result.policy is family


def test_generic_architecture_is_final_fallback() -> None:
    generic = policy(
        LinuxHostPolicyKey(
            architecture=LinuxArchitecture.X86_64,
        ),
        "requirement-generic",
    )

    registry = LinuxHostQualificationPolicyRegistry((generic,))

    result = registry.resolve(
        distribution=LinuxDistribution.OTHER,
        distribution_family=LinuxDistributionFamily.OTHER,
        architecture=LinuxArchitecture.X86_64,
    )

    assert result.policy is generic


def test_no_policy_does_not_qualify_host() -> None:
    registry = LinuxHostQualificationPolicyRegistry(())

    result = registry.resolve(
        distribution=LinuxDistribution.OTHER,
        distribution_family=LinuxDistributionFamily.OTHER,
        architecture=LinuxArchitecture.X86_64,
    )

    assert result.matched is False
    assert result.policy is None


def test_registry_order_is_deterministic() -> None:
    keys = (
        LinuxHostPolicyKey(distribution=LinuxDistribution.UBUNTU),
        LinuxHostPolicyKey(architecture=LinuxArchitecture.X86_64),
        LinuxHostPolicyKey(
            distribution=LinuxDistribution.UBUNTU,
            architecture=LinuxArchitecture.X86_64,
        ),
    )

    registry_a = LinuxHostQualificationPolicyRegistry(
        tuple(
            policy(key, f"requirement-{index}")
            for index, key in enumerate(reversed(keys))
        )
    )
    registry_b = LinuxHostQualificationPolicyRegistry(
        tuple(
            policy(key, f"requirement-{index}")
            for index, key in enumerate(keys)
        )
    )

    assert registry_a.policy_ids == registry_b.policy_ids
