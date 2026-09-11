"""Deterministic Linux enforcement application orchestrator."""

from __future__ import annotations

from lyrion.execution.backends.linux.enforcement.application import (
    EnforcementApplicationContext,
    EnforcementApplicationResult,
    EnforcementApplicationStatus,
    EnforcementPrimitiveResult,
)
from lyrion.execution.backends.linux.enforcement.contracts import (
    EnforcementPrimitive,
    EnforcementState,
    LinuxEnforcementPlan,
)
from lyrion.execution.backends.linux.enforcement.registry import (
    PrimitiveAdapterRegistry,
)


class LinuxEnforcementApplication:
    """
    Apply and independently verify one immutable Linux enforcement plan.

    This layer orchestrates trusted primitive adapters only. It does not:
    - authorize execution;
    - alter SandboxConfig or ExecutionPolicy;
    - perform low-level Linux operations;
    - dynamically discover adapters;
    - silently downgrade failed controls.
    """

    def __init__(
        self,
        registry: PrimitiveAdapterRegistry,
    ) -> None:
        self._registry = registry

    def apply(
        self,
        plan: LinuxEnforcementPlan,
        context: EnforcementApplicationContext,
    ) -> EnforcementApplicationResult:
        """
        Apply and independently verify every required primitive.

        Any required-control failure terminates the application attempt
        fail-closed. Execution is permitted only when the aggregate result
        reaches VERIFIED.
        """
        if context.execution_id == "":
            return self._aborted(
                context,
                "execution context has an empty execution_id",
            )

        if context.backend_id == "":
            return self._aborted(
                context,
                "execution context has an empty backend_id",
            )

        try:
            plan.assert_planning_only()
        except ValueError as exc:
            return self._aborted(
                context,
                f"invalid enforcement plan: {exc}",
            )

        if plan.has_failed_requirements():
            return self._aborted(
                context,
                "enforcement plan contains failed requirements",
            )

        requirements = plan.requirements

        if self._has_duplicate_requirements(requirements):
            return self._aborted(
                context,
                "enforcement plan contains duplicate primitive requirements",
            )

        results: list[EnforcementPrimitiveResult] = []

        for primitive in plan.required_primitives():
            adapter_result = self._process_required_primitive(
                primitive=primitive,
                plan=plan,
                context=context,
            )

            results.append(adapter_result)

            if not adapter_result.success:
                return self._failed(
                    context,
                    results,
                    (
                        f"required primitive {primitive.value} failed: "
                        f"{adapter_result.reason}"
                    ),
                )

        if not results:
            return self._aborted(
                context,
                "enforcement plan contains no required primitives",
            )

        if any(
            result.state is not EnforcementState.VERIFIED
            for result in results
        ):
            return self._failed(
                context,
                results,
                "required enforcement verification was incomplete",
            )

        return EnforcementApplicationResult(
            execution_id=context.execution_id,
            backend_id=context.backend_id,
            status=EnforcementApplicationStatus.VERIFIED,
            primitive_results=tuple(results),
        )

    def _process_required_primitive(
        self,
        *,
        primitive: EnforcementPrimitive,
        plan: LinuxEnforcementPlan,
        context: EnforcementApplicationContext,
    ) -> EnforcementPrimitiveResult:
        """Resolve, validate, apply, and independently verify one primitive."""
        try:
            adapter = self._registry.resolve(primitive)
        except KeyError as exc:
            return self._failed_primitive(
                primitive,
                f"no trusted adapter registered: {exc}",
            )

        if adapter.primitive is not primitive:
            return self._failed_primitive(
                primitive,
                "resolved adapter primitive does not match plan primitive",
            )

        try:
            if not adapter.supports(plan):
                return self._failed_primitive(
                    primitive,
                    "required primitive is not supported",
                )

            validation = adapter.validate(plan)
        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            return self._failed_primitive(
                primitive,
                f"primitive validation raised an exception: {exc}",
            )

        if not self._valid_result(
            validation,
            primitive=primitive,
            expected_required=True,
        ):
            return self._failed_primitive(
                primitive,
                (
                    "primitive validation returned an invalid result: "
                    f"{validation.reason}"
                ),
            )

        if validation.state is EnforcementState.FAILED:
            return validation

        try:
            applied = adapter.apply(context, plan)
        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            return self._failed_primitive(
                primitive,
                f"primitive application raised an exception: {exc}",
            )

        if not self._valid_result(
            applied,
            primitive=primitive,
            expected_required=True,
        ):
            return self._failed_primitive(
                primitive,
                (
                    "primitive application returned an invalid result: "
                    f"{applied.reason}"
                ),
            )

        if applied.state is EnforcementState.FAILED:
            return applied

        if applied.state is EnforcementState.VERIFIED:
            return self._failed_primitive(
                primitive,
                "adapter apply() must never report VERIFIED",
            )

        if applied.state is not EnforcementState.APPLIED:
            return self._failed_primitive(
                primitive,
                (
                    "primitive application did not reach APPLIED state: "
                    f"{applied.state.value}"
                ),
            )

        try:
            verified = adapter.verify(context, plan)
        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            return self._failed_primitive(
                primitive,
                f"primitive verification raised an exception: {exc}",
            )

        if not self._valid_result(
            verified,
            primitive=primitive,
            expected_required=True,
        ):
            return self._failed_primitive(
                primitive,
                (
                    "primitive verification returned an invalid result: "
                    f"{verified.reason}"
                ),
            )

        if verified.state is not EnforcementState.VERIFIED:
            return self._failed_primitive(
                primitive,
                (
                    "primitive verification did not reach VERIFIED state: "
                    f"{verified.state.value}"
                ),
            )

        return verified

    @staticmethod
    def _valid_result(
        result: EnforcementPrimitiveResult,
        *,
        primitive: EnforcementPrimitive,
        expected_required: bool,
    ) -> bool:
        """Check adapter-result identity and fail-closed invariants."""
        return (
            result.primitive is primitive
            and result.required is expected_required
            and (
                result.state is not EnforcementState.FAILED
                or not result.success
            )
        )

    @staticmethod
    def _failed_primitive(
        primitive: EnforcementPrimitive,
        reason: str,
    ) -> EnforcementPrimitiveResult:
        """Construct a deterministic failed primitive result."""
        return EnforcementPrimitiveResult(
            primitive=primitive,
            required=True,
            state=EnforcementState.FAILED,
            success=False,
            reason=reason,
            evidence=(),
        )

    @staticmethod
    def _has_duplicate_requirements(
        requirements: tuple[object, ...],
    ) -> bool:
        """Reject duplicate primitive requirements before execution."""
        primitives: set[EnforcementPrimitive] = set()

        for requirement in requirements:
            primitive = requirement.primitive  # type: ignore[attr-defined]

            if primitive in primitives:
                return True

            primitives.add(primitive)

        return False

    @staticmethod
    def _failed(
        context: EnforcementApplicationContext,
        results: list[EnforcementPrimitiveResult],
        reason: str,
    ) -> EnforcementApplicationResult:
        """Build a fail-closed application result."""
        return EnforcementApplicationResult(
            execution_id=context.execution_id,
            backend_id=context.backend_id,
            status=EnforcementApplicationStatus.FAILED,
            primitive_results=tuple(results),
            failure_reason=reason,
        )

    @staticmethod
    def _aborted(
        context: EnforcementApplicationContext,
        reason: str,
    ) -> EnforcementApplicationResult:
        """Build a fail-closed aborted application result."""
        return EnforcementApplicationResult(
            execution_id=context.execution_id,
            backend_id=context.backend_id,
            status=EnforcementApplicationStatus.ABORTED,
            primitive_results=(),
            failure_reason=reason,
        )


__all__ = ["LinuxEnforcementApplication"]
