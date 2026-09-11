"""Immutable contracts for the LYRION child-enforcement bootstrap."""

from __future__ import annotations

import hashlib
import hmac
import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lyrion.execution.backends.linux.enforcement.contracts import (
    EnforcementPlanStatus,
    EnforcementState,
    LinuxEnforcementPlan,
)
from lyrion.execution.process_boundary.supervisor import ProcessLaunchSpec


class BootstrapContractError(ValueError):
    """Raised when a bootstrap contract violates a security invariant."""


class BootstrapState(StrEnum):
    """Ordered lifecycle states of one child bootstrap."""

    CREATED = "created"
    IDENTITY_BOUND = "identity_bound"
    HANDOFF_VALIDATED = "handoff_validated"
    RESOURCES_PREPARED = "resources_prepared"
    NAMESPACES_PREPARED = "namespaces_prepared"
    FILESYSTEM_NETWORK_PREPARED = "filesystem_network_prepared"
    NO_NEW_PRIVS_APPLIED = "no_new_privs_applied"
    CAPABILITIES_REDUCED = "capabilities_reduced"
    LANDLOCK_APPLIED = "landlock_applied"
    SECCOMP_APPLIED = "seccomp_applied"
    ENFORCEMENT_VERIFIED = "enforcement_verified"
    EXEC_READY = "exec_ready"
    EXEC_STARTED = "exec_started"
    FAILED = "failed"


class LaunchHandoff(BaseModel):
    """
    Immutable integrity-bound handoff for one authorized execution.

    This contract carries already-authorized execution intent into the child
    bootstrap. It does not authorize execution and cannot grant authority.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    execution_id: str = Field(min_length=1, max_length=500)
    request_id: str = Field(min_length=1, max_length=500)
    backend_id: str = Field(min_length=1, max_length=200)
    policy_version: str = Field(min_length=1, max_length=200)
    authorization_reference: str = Field(min_length=1, max_length=500)

    argv: tuple[str, ...]
    cwd: str
    environment: tuple[tuple[str, str], ...]

    timeout_seconds: float = Field(gt=0)
    max_output_bytes: int = Field(gt=0)

    enforcement_plan: tuple[tuple[str, Any], ...]
    integrity_sha256: str = Field(
        min_length=64,
        max_length=64,
    )

    @field_validator("execution_id", "request_id", "backend_id")
    @classmethod
    def validate_identity(cls, value: str) -> str:
        """Reject blank security identities."""
        if not value.strip():
            raise ValueError("security identity must not be blank")
        return value

    @field_validator(
        "policy_version",
        "authorization_reference",
    )
    @classmethod
    def validate_reference(cls, value: str) -> str:
        """Reject blank authorization references."""
        if not value.strip():
            raise ValueError("security reference must not be blank")
        return value

    @field_validator("argv")
    @classmethod
    def validate_argv(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Require explicit non-empty, NUL-free arguments."""
        if not value:
            raise ValueError("argv must not be empty")

        if any(not isinstance(item, str) or not item for item in value):
            raise ValueError(
                "argv must contain only non-empty strings"
            )

        if any("\x00" in item for item in value):
            raise ValueError("argv must not contain NUL characters")

        return value

    @field_validator("cwd")
    @classmethod
    def validate_cwd(cls, value: str) -> str:
        """Require an absolute working directory."""
        path = Path(value)

        if not value:
            raise ValueError("cwd must not be empty")

        if not path.is_absolute():
            raise ValueError("cwd must be an absolute path")

        return value

    @field_validator("environment")
    @classmethod
    def validate_environment(
        cls,
        value: tuple[tuple[str, str], ...],
    ) -> tuple[tuple[str, str], ...]:
        """Require deterministic, NUL-free environment entries."""
        keys: set[str] = set()

        for key, environment_value in value:
            if not key:
                raise ValueError(
                    "environment keys must not be empty"
                )

            if "\x00" in key or "\x00" in environment_value:
                raise ValueError(
                    "environment must not contain NUL characters"
                )

            if key in keys:
                raise ValueError(
                    "environment must not contain duplicate keys"
                )

            keys.add(key)

        return value

    @field_validator("enforcement_plan")
    @classmethod
    def validate_plan_payload(
        cls,
        value: tuple[tuple[str, Any], ...],
    ) -> tuple[tuple[str, Any], ...]:
        """
        Require a non-empty deterministic planning-only plan payload.

        The serialized payload must represent a READY planning contract and
        must not contain failed, applied, or verified enforcement states.
        """
        if not value:
            raise ValueError("enforcement_plan must not be empty")

        payload = {
            key: item
            for key, item in value
        }

        status = payload.get("status")
        if status != EnforcementPlanStatus.READY.value:
            raise ValueError(
                "enforcement_plan must have READY status"
            )

        requirements = payload.get("requirements")
        if not isinstance(requirements, list):
            raise ValueError(
                "enforcement_plan requirements must be a list"
            )

        for requirement in requirements:
            if not isinstance(requirement, dict):
                raise ValueError(
                    "enforcement_plan requirements must contain objects"
                )

            state = requirement.get("state")
            if state in {
                EnforcementState.APPLIED.value,
                EnforcementState.VERIFIED.value,
            }:
                raise ValueError(
                    "enforcement_plan cannot claim applied or verified controls"
                )

            if state == EnforcementState.FAILED.value:
                raise ValueError(
                    "enforcement_plan cannot contain failed requirements"
                )

        return value

    @field_validator("integrity_sha256")
    @classmethod
    def validate_digest_format(cls, value: str) -> str:
        """Require a lowercase SHA-256 hexadecimal digest."""
        if any(
            character not in "0123456789abcdef"
            for character in value
        ):
            raise ValueError(
                "integrity_sha256 must contain lowercase hexadecimal"
            )

        return value

    @classmethod
    def from_components(
        cls,
        *,
        execution_id: str,
        request_id: str,
        backend_id: str,
        policy_version: str,
        authorization_reference: str,
        launch_spec: ProcessLaunchSpec,
        enforcement_plan: LinuxEnforcementPlan,
    ) -> LaunchHandoff:
        """Create a canonical integrity-bound launch handoff."""
        environment = tuple(
            sorted(
                launch_spec.environment.items(),
                key=lambda item: item[0],
            )
        )

        if enforcement_plan.status is not EnforcementPlanStatus.READY:
            raise BootstrapContractError(
                "launch handoff requires a READY enforcement plan"
            )

        try:
            enforcement_plan.assert_planning_only()
        except ValueError as exc:
            raise BootstrapContractError(
                "launch handoff requires a planning-only enforcement plan"
            ) from exc

        if enforcement_plan.has_failed_requirements():
            raise BootstrapContractError(
                "launch handoff cannot contain failed enforcement requirements"
            )

        plan_payload = _canonical_plan(enforcement_plan)
        plan_items = tuple(
            sorted(
                plan_payload.items(),
                key=lambda item: item[0],
            )
        )

        payload = cls._unsigned_payload(
            execution_id=execution_id,
            request_id=request_id,
            backend_id=backend_id,
            policy_version=policy_version,
            authorization_reference=authorization_reference,
            argv=launch_spec.argv,
            cwd=str(launch_spec.cwd),
            environment=environment,
            timeout_seconds=launch_spec.timeout_seconds,
            max_output_bytes=launch_spec.max_output_bytes,
            enforcement_plan=plan_items,
        )

        digest = _sha256(payload)

        return cls(
            execution_id=execution_id,
            request_id=request_id,
            backend_id=backend_id,
            policy_version=policy_version,
            authorization_reference=authorization_reference,
            argv=launch_spec.argv,
            cwd=str(launch_spec.cwd),
            environment=environment,
            timeout_seconds=launch_spec.timeout_seconds,
            max_output_bytes=launch_spec.max_output_bytes,
            enforcement_plan=plan_items,
            integrity_sha256=digest,
        )

    def compute_integrity_sha256(self) -> str:
        """Compute the digest covering all security-relevant fields."""
        return _sha256(
            self._unsigned_payload(
                execution_id=self.execution_id,
                request_id=self.request_id,
                backend_id=self.backend_id,
                policy_version=self.policy_version,
                authorization_reference=self.authorization_reference,
                argv=self.argv,
                cwd=self.cwd,
                environment=self.environment,
                timeout_seconds=self.timeout_seconds,
                max_output_bytes=self.max_output_bytes,
                enforcement_plan=self.enforcement_plan,
            )
        )

    def verify_integrity(self) -> None:
        """Fail closed when the handoff digest does not match."""
        expected = self.compute_integrity_sha256()

        if not hmac.compare_digest(
            expected,
            self.integrity_sha256,
        ):
            raise BootstrapContractError(
                "launch handoff integrity verification failed"
            )

    @staticmethod
    def _unsigned_payload(
        *,
        execution_id: str,
        request_id: str,
        backend_id: str,
        policy_version: str,
        authorization_reference: str,
        argv: tuple[str, ...],
        cwd: str,
        environment: tuple[tuple[str, str], ...],
        timeout_seconds: float,
        max_output_bytes: int,
        enforcement_plan: tuple[tuple[str, Any], ...],
    ) -> dict[str, Any]:
        """Build the canonical payload covered by the digest."""
        return {
            "execution_id": execution_id,
            "request_id": request_id,
            "backend_id": backend_id,
            "policy_version": policy_version,
            "authorization_reference": authorization_reference,
            "argv": list(argv),
            "cwd": cwd,
            "environment": [
                [key, value]
                for key, value in environment
            ],
            "timeout_seconds": timeout_seconds,
            "max_output_bytes": max_output_bytes,
            "enforcement_plan": {
                key: value
                for key, value in enforcement_plan
            },
        }


_BOOTSTRAP_ORDER: tuple[BootstrapState, ...] = (
    BootstrapState.CREATED,
    BootstrapState.IDENTITY_BOUND,
    BootstrapState.HANDOFF_VALIDATED,
    BootstrapState.RESOURCES_PREPARED,
    BootstrapState.NAMESPACES_PREPARED,
    BootstrapState.FILESYSTEM_NETWORK_PREPARED,
    BootstrapState.NO_NEW_PRIVS_APPLIED,
    BootstrapState.CAPABILITIES_REDUCED,
    BootstrapState.LANDLOCK_APPLIED,
    BootstrapState.SECCOMP_APPLIED,
    BootstrapState.ENFORCEMENT_VERIFIED,
    BootstrapState.EXEC_READY,
    BootstrapState.EXEC_STARTED,
)


class BootstrapStateMachine:
    """Strict state machine for child-bootstrap lifecycle control."""

    def __init__(self, execution_id: str) -> None:
        if not execution_id.strip():
            raise BootstrapContractError(
                "execution_id must not be empty"
            )

        self._execution_id = execution_id
        self._state = BootstrapState.CREATED

    @property
    def execution_id(self) -> str:
        """Return the execution identity."""
        return self._execution_id

    @property
    def state(self) -> BootstrapState:
        """Return the current bootstrap state."""
        return self._state

    def transition(
        self,
        target: BootstrapState,
    ) -> None:
        """Permit exactly one forward transition or terminal failure."""
        if target is BootstrapState.FAILED:
            if self._state is BootstrapState.FAILED:
                raise BootstrapContractError(
                    "failed bootstrap cannot transition again"
                )

            self._state = BootstrapState.FAILED
            return

        if self._state is BootstrapState.FAILED:
            raise BootstrapContractError(
                "failed bootstrap cannot transition"
            )

        try:
            current_index = _BOOTSTRAP_ORDER.index(self._state)
            target_index = _BOOTSTRAP_ORDER.index(target)
        except ValueError as exc:
            raise BootstrapContractError(
                f"unsupported bootstrap state: {target.value}"
            ) from exc

        if target_index != current_index + 1:
            raise BootstrapContractError(
                "invalid bootstrap transition: "
                f"{self._state.value} -> {target.value}"
            )

        self._state = target

    def require(self, expected: BootstrapState) -> None:
        """Require an exact current state."""
        if self._state is not expected:
            raise BootstrapContractError(
                "bootstrap state mismatch: "
                f"expected {expected.value}, "
                f"observed {self._state.value}"
            )


def _canonical_plan(
    plan: LinuxEnforcementPlan,
) -> dict[str, Any]:
    """Convert an immutable enforcement plan to JSON-compatible data."""
    payload = plan.model_dump(mode="json")

    if not isinstance(payload, dict):
        raise BootstrapContractError(
            "enforcement plan did not produce an object payload"
        )

    return payload


def _sha256(payload: dict[str, Any]) -> str:
    """Compute SHA-256 over canonical JSON."""
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "BootstrapContractError",
    "BootstrapState",
    "BootstrapStateMachine",
    "LaunchHandoff",
]
