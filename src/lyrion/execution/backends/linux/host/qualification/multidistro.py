from __future__ import annotations

from dataclasses import dataclass

from lyrion.execution.backends.linux.host.contracts import (
    LinuxHostAbstractionSnapshot,
)
from lyrion.execution.backends.linux.host.negotiation.contracts import (
    CapabilityNegotiationStatus,
    CapabilityRequirementSet,
)
from lyrion.execution.backends.linux.host.policy import (
    LinuxHostQualificationPolicyRegistry,
)
from lyrion.execution.backends.linux.host.profiles.contracts import (
    LinuxHostQualificationProfile,
)
from lyrion.execution.backends.linux.host.profiles.engine import (
    LinuxHostQualificationProfileEngine,
)

from .contracts import AdaptiveQualificationResult
from .engine import AdaptiveQualificationEngine
from .evidence import QualificationEvidence


class MultiDistributionQualificationError(ValueError):
    """Raised when qualification inputs are inconsistent."""


@dataclass(frozen=True, slots=True)
class MultiDistributionQualificationResult:
    """
    Immutable multi-distribution qualification result.

    Distribution and architecture identify the observed host.
    Capability qualification is delegated to the validated adaptive
    qualification engine.

    This result never grants execution authorization and never proves
    enforcement.
    """

    profile: LinuxHostQualificationProfile
    adaptive: AdaptiveQualificationResult
    selected_policy_id: str | None = None
    evidence: QualificationEvidence | None = None

    @property
    def status(self) -> CapabilityNegotiationStatus:
        return self.adaptive.status

    @property
    def qualified(self) -> bool:
        return self.adaptive.qualified

    @property
    def degraded(self) -> bool:
        return self.adaptive.degraded

    @property
    def blocked(self) -> bool:
        return self.adaptive.blocked

    @property
    def profile_id(self) -> str:
        return self.adaptive.profile_id

    @property
    def evidence_digest(self) -> str:
        return self.adaptive.evidence_digest

    @property
    def execution_authorized(self) -> bool:
        return False

    @property
    def enforcement_verified(self) -> bool:
        return False


class MultiDistributionQualificationEngine:
    """
    Capability-first qualification orchestrator.

    The engine:
      - derives the host profile from the observed host snapshot;
      - verifies profile/snapshot identity consistency;
      - delegates capability semantics to AdaptiveQualificationEngine;
      - preserves fail-closed qualification decisions.

    It does NOT:
      - authorize execution;
      - apply enforcement;
      - execute processes;
      - mutate the host;
      - infer capability from distribution name;
      - silently downgrade required controls;
      - declare production certification.
    """

    def __init__(
        self,
        *,
        profile_engine: LinuxHostQualificationProfileEngine | None = None,
        adaptive_engine: AdaptiveQualificationEngine | None = None,
        policy_registry: LinuxHostQualificationPolicyRegistry | None = None,
    ) -> None:
        self._profile_engine = (
            profile_engine or LinuxHostQualificationProfileEngine()
        )
        self._adaptive_engine = (
            adaptive_engine or AdaptiveQualificationEngine()
        )
        self._policy_registry = policy_registry

    def qualify(
        self,
        *,
        host_snapshot: LinuxHostAbstractionSnapshot,
        requirements: CapabilityRequirementSet | None = None,
    ) -> MultiDistributionQualificationResult:
        profile = self._profile_engine.build(host_snapshot)

        self._assert_profile_matches_snapshot(
            profile=profile,
            snapshot=host_snapshot,
        )

        selected_policy_id: str | None = None
        selected_policy = None

        if self._policy_registry is not None:
            if requirements is not None:
                raise MultiDistributionQualificationError(
                    "qualification cannot receive both explicit requirements "
                    "and a policy registry"
                )

            resolution = self._policy_registry.resolve(
                distribution=profile.distribution.distribution,
                distribution_family=profile.distribution.family,
                architecture=profile.architecture.architecture,
            )

            if not resolution.matched or resolution.policy is None:
                raise MultiDistributionQualificationError(
                    "no applicable host qualification policy was found"
                )

            selected_policy = resolution.policy
            requirements = selected_policy.requirements
            selected_policy_id = selected_policy.policy_id

        if requirements is None:
            raise MultiDistributionQualificationError(
                "qualification requires explicit requirements or a policy registry"
            )

        adaptive = self._adaptive_engine.qualify(
            host_snapshot=host_snapshot,
            requirements=requirements,
        )

        self._assert_boundary(adaptive)

        evidence = None
        if selected_policy is not None:
            evidence = QualificationEvidence.from_qualification(
                host_snapshot=host_snapshot,
                policy=selected_policy,
                negotiation=adaptive.negotiation,
                qualification_state=adaptive.status.value,
            )

        return MultiDistributionQualificationResult(
            profile=profile,
            adaptive=adaptive,
            selected_policy_id=selected_policy_id,
            evidence=evidence,
        )

    @staticmethod
    def _assert_profile_matches_snapshot(
        *,
        profile: LinuxHostQualificationProfile,
        snapshot: LinuxHostAbstractionSnapshot,
    ) -> None:
        if profile.distribution.raw_id != snapshot.identity.os_name:
            raise MultiDistributionQualificationError(
                "qualification profile distribution does not match "
                "the observed host identity"
            )

        if profile.distribution.version != snapshot.identity.os_version:
            raise MultiDistributionQualificationError(
                "qualification profile version does not match "
                "the observed host identity"
            )

        if profile.architecture.raw_value != snapshot.identity.architecture:
            raise MultiDistributionQualificationError(
                "qualification profile architecture does not match "
                "the observed host identity"
            )

        if profile.kernel != snapshot.identity.kernel:
            raise MultiDistributionQualificationError(
                "qualification profile kernel does not match "
                "the observed host identity"
            )

    @staticmethod
    def _assert_boundary(
        result: AdaptiveQualificationResult,
    ) -> None:
        if result.execution_authorized:
            raise RuntimeError(
                "Multi-distribution qualification cannot authorize execution."
            )

        if result.enforcement_verified:
            raise RuntimeError(
                "Multi-distribution qualification cannot claim "
                "enforcement verification."
            )
