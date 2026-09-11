from __future__ import annotations

from typing import Protocol

from lyrion.execution.backends.linux.enforcement.application import (
    EnforcementApplicationContext,
    EnforcementEvidence,
    EnforcementPrimitiveResult,
)
from lyrion.execution.backends.linux.enforcement.contracts import (
    EnforcementPrimitive,
    LinuxEnforcementPlan,
)


class PrimitiveAdapter(Protocol):
    """
    Contract for one Linux enforcement primitive.

    Adapters are deliberately narrow:
    - they operate only on their assigned primitive;
    - they do not authorize execution;
    - they do not alter SandboxConfig or ExecutionPolicy;
    - they do not perform implicit fallback;
    - they must distinguish support, application, and verification.
    """

    @property
    def primitive(self) -> EnforcementPrimitive:
        """Return the primitive owned by this adapter."""

    def supports(self, plan: LinuxEnforcementPlan) -> bool:
        """
        Return whether this adapter can support the requested primitive.

        This method must be observational only. It must not mutate host state.
        """

    def validate(self, plan: LinuxEnforcementPlan) -> EnforcementPrimitiveResult:
        """
        Validate the primitive-specific portion of an enforcement plan.

        Validation must not mutate host state.
        """

    def apply(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """
        Apply the primitive-specific enforcement.

        A concrete implementation must never report VERIFIED from apply().
        Verification is a separate lifecycle operation.
        """

    def verify(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """
        Independently verify that the primitive is actually enforced.

        Verification must provide positive evidence before reporting VERIFIED.
        """

    def evidence(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> tuple[EnforcementEvidence, ...]:
        """
        Return primitive-specific evidence available to the adapter.

        Evidence collection must be bounded to the adapter's primitive and
        must not silently establish enforcement merely from capability support.
        """
