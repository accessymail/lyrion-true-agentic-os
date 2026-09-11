"""AppArmor primitive adapter for Linux enforcement."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Protocol

from lyrion.execution.backends.linux.enforcement.adapter import PrimitiveAdapter
from lyrion.execution.backends.linux.enforcement.apparmor_policy import (
    AppArmorPolicy,
    AppArmorPolicyValidator,
    attest_policy,
    verify_policy_attestation,
)
from lyrion.execution.backends.linux.enforcement.application import (
    EnforcementApplicationContext,
    EnforcementEvidence,
    EnforcementPrimitiveResult,
)
from lyrion.execution.backends.linux.enforcement.contracts import (
    EnforcementPrimitive,
    EnforcementRequirement,
    EnforcementState,
    LinuxEnforcementPlan,
)


class AppArmorState:
    """Runtime state observed for an AppArmor profile."""

    __slots__ = (
        "loaded",
        "enforcing",
        "profile_name",
        "profile_version",
    )

    def __init__(
        self,
        *,
        loaded: bool,
        enforcing: bool,
        profile_name: str | None,
        profile_version: str | None,
    ) -> None:
        self.loaded = loaded
        self.enforcing = enforcing
        self.profile_name = profile_name
        self.profile_version = profile_version


class AppArmorOperations(Protocol):
    """Host operations required by the AppArmor adapter."""

    def supports(self) -> bool:
        """Return whether AppArmor operations are available."""

    def load_profile(self, policy: AppArmorPolicy) -> None:
        """Load the supplied AppArmor profile."""

    def get_state(self, profile_name: str) -> AppArmorState:
        """Return independently observed profile state."""


class NativeAppArmorOperations:
    """
    Native AppArmor host-operation boundary.

    Capability detection is observational and performs no policy mutation.
    Profile loading remains explicitly blocked until the AppArmor kernel
    interface is available and the native loading path is validated.
    """

    _APPARMOR_ENABLED = "/sys/module/apparmor/parameters/enabled"
    _APPARMOR_SECURITYFS = "/sys/kernel/security/apparmor"
    _PARSER = "/usr/sbin/apparmor_parser"

    def _kernel_enabled(self) -> bool:
        """Return whether the AppArmor kernel component reports enabled."""
        try:
            value = Path(self._APPARMOR_ENABLED).read_text(
                encoding="utf-8",
            ).strip()
        except (OSError, UnicodeError):
            return False

        return value.upper() == "Y"

    def _securityfs_available(self) -> bool:
        """Return whether the AppArmor securityfs interface is available."""
        return Path(self._APPARMOR_SECURITYFS).is_dir()

    def _parser_available(self) -> bool:
        """Return whether the native AppArmor parser is available."""
        return Path(self._PARSER).is_file()

    def supports(self) -> bool:
        """
        Return whether the native AppArmor interface is usable.

        This method is strictly observational and must not modify host state.
        """
        return (
            self._kernel_enabled()
            and self._securityfs_available()
            and self._parser_available()
        )

    def load_profile(self, policy: AppArmorPolicy) -> None:
        """
        Load one application-owned AppArmor profile using apparmor_parser.

        This operation is intentionally add-only. It will not replace an
        existing profile with the same name.
        """
        if not self.supports():
            raise RuntimeError(
                "Native AppArmor enforcement is unavailable: "
                "kernel AppArmor, securityfs, or apparmor_parser is missing."
            )

        if policy.mode.value != "enforce":
            raise RuntimeError(
                "Native LYRION AppArmor loading requires enforce mode."
            )

        validator = AppArmorPolicyValidator()
        validation = validator.validate(
            policy,
            required=True,
        )

        if not validation.success:
            raise RuntimeError(
                f"AppArmor policy validation failed: {validation.reason}"
            )

        temporary_path: str | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                prefix="lyrion-apparmor-",
                suffix=".profile",
                dir="/tmp",
                delete=False,
            ) as profile_file:
                profile_file.write(policy.profile_text)
                profile_file.flush()
                temporary_path = profile_file.name

            result = subprocess.run(
                [
                    self._PARSER,
                    "--add",
                    temporary_path,
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                stderr = result.stderr.strip()
                stdout = result.stdout.strip()

                detail = stderr or stdout or (
                    f"apparmor_parser exited with status "
                    f"{result.returncode}"
                )

                raise RuntimeError(
                    f"AppArmor profile loading failed: {detail}"
                )

        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "AppArmor profile loading timed out."
            ) from exc
        finally:
            if temporary_path is not None:
                try:
                    Path(temporary_path).unlink()
                except FileNotFoundError:
                    pass

    def get_state(self, profile_name: str) -> AppArmorState:
        """
        Reject native verification until the runtime-state implementation
        has been separately validated.
        """
        if not self.supports():
            raise RuntimeError(
                "Native AppArmor verification is unavailable."
            )

        raise RuntimeError(
            "Native AppArmor runtime verification requires the controlled "
            "R3 verification implementation."
        )


class AppArmorAdapter(PrimitiveAdapter):
    """Adapter responsible exclusively for AppArmor enforcement."""

    def __init__(
        self,
        *,
        policy: AppArmorPolicy,
        operations: AppArmorOperations,
    ) -> None:
        self._policy = policy
        self._operations = operations
        self._validator = AppArmorPolicyValidator()

    @property
    def primitive(self) -> EnforcementPrimitive:
        """Return the primitive owned by this adapter."""
        return EnforcementPrimitive.APPARMOR

    @staticmethod
    def _plan_requirement(
        plan: LinuxEnforcementPlan,
    ) -> EnforcementRequirement | None:
        for requirement in plan.requirements:
            if requirement.primitive is EnforcementPrimitive.APPARMOR:
                return requirement
        return None

    @staticmethod
    def _plan_matches(
        plan: LinuxEnforcementPlan,
        requirement: EnforcementRequirement,
    ) -> bool:
        return requirement.required == plan.apparmor.required

    def supports(self, plan: LinuxEnforcementPlan) -> bool:
        """Return support status without mutating host state."""

        requirement = self._plan_requirement(plan)

        if requirement is None:
            return False

        if not self._plan_matches(plan, requirement):
            return False

        if not plan.apparmor.required:
            return True

        return self._operations.supports()

    def validate(
        self,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Validate AppArmor requirements without host mutation."""

        requirement = self._plan_requirement(plan)

        if requirement is None:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason="AppArmor requirement is missing from the plan.",
            )

        if not self._plan_matches(plan, requirement):
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=requirement.required,
                state=EnforcementState.FAILED,
                success=False,
                reason="AppArmor requirement does not match the AppArmor plan.",
            )

        validation = self._validator.validate(
            self._policy,
            required=requirement.required,
        )

        if not validation.success:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=requirement.required,
                state=EnforcementState.FAILED,
                success=False,
                reason=validation.reason,
            )

        if requirement.required and not self._operations.supports():
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason="Required AppArmor operations are unavailable.",
            )

        return EnforcementPrimitiveResult(
            primitive=self.primitive,
            required=requirement.required,
            state=EnforcementState.SUPPORTED,
            success=True,
            reason="AppArmor policy and adapter requirements are valid.",
        )

    def apply(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Apply AppArmor without claiming independent verification."""

        validation = self.validate(plan)

        if not validation.success:
            return validation

        if not plan.apparmor.required:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=False,
                state=EnforcementState.APPLIED,
                success=True,
                reason="AppArmor is not required by the execution plan.",
            )

        try:
            self._operations.load_profile(self._policy)
        except Exception as exc:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason=f"AppArmor profile application failed: {exc}",
            )

        return EnforcementPrimitiveResult(
            primitive=self.primitive,
            required=True,
            state=EnforcementState.APPLIED,
            success=True,
            reason=(
                "AppArmor profile application completed; independent "
                "verification is still required."
            ),
        )

    def verify(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> EnforcementPrimitiveResult:
        """Independently verify AppArmor runtime state and policy identity."""

        validation = self.validate(plan)

        if not validation.success:
            return validation

        if not plan.apparmor.required:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=False,
                state=EnforcementState.VERIFIED,
                success=True,
                reason="AppArmor is not required by the execution plan.",
                evidence=(
                    EnforcementEvidence.verified(
                        primitive=self.primitive,
                        evidence_type="apparmor_not_required",
                        observation=(
                            "The execution plan does not require AppArmor."
                        ),
                    ),
                ),
            )

        try:
            state = self._operations.get_state(
                self._policy.profile_name,
            )
        except Exception as exc:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason=f"AppArmor verification failed: {exc}",
            )

        attestation = attest_policy(self._policy)

        if not state.loaded:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason="AppArmor profile is not loaded.",
            )

        if not state.enforcing:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason="AppArmor profile is not in enforcing state.",
            )

        if state.profile_name != self._policy.profile_name:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason="Observed AppArmor profile name does not match policy.",
            )

        if state.profile_version != self._policy.policy_version:
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason="Observed AppArmor profile version does not match policy.",
            )

        if not verify_policy_attestation(
            self._policy,
            attestation,
        ):
            return EnforcementPrimitiveResult(
                primitive=self.primitive,
                required=True,
                state=EnforcementState.FAILED,
                success=False,
                reason="AppArmor policy attestation verification failed.",
            )

        evidence = (
            EnforcementEvidence.verified(
                primitive=self.primitive,
                evidence_type="apparmor_runtime_state",
                observation=(
                    "AppArmor profile is loaded and independently observed "
                    "in enforcing state."
                ),
            ),
            EnforcementEvidence.verified(
                primitive=self.primitive,
                evidence_type="apparmor_policy_attestation",
                observation=(
                    "Observed AppArmor policy identity matches the "
                    "application-owned policy attestation."
                ),
                evidence_ref=attestation.policy_digest,
            ),
        )

        return EnforcementPrimitiveResult(
            primitive=self.primitive,
            required=True,
            state=EnforcementState.VERIFIED,
            success=True,
            reason="AppArmor enforcement was independently verified.",
            evidence=evidence,
        )

    def evidence(
        self,
        context: EnforcementApplicationContext,
        plan: LinuxEnforcementPlan,
    ) -> tuple[EnforcementEvidence, ...]:
        """Return evidence only when independent verification succeeds."""

        result = self.verify(context, plan)

        if not result.success:
            return ()

        return result.evidence
