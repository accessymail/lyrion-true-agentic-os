"""Sandbox boundary contracts and policy validation for Lyrion."""

from __future__ import annotations

from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from lyrion.core.types import ExecutionTarget
from lyrion.execution.contracts import ResourceLimits


class FilesystemMode(StrEnum):
    """Filesystem isolation modes."""

    NONE = "NONE"
    READ_ONLY = "READ_ONLY"
    WORKSPACE = "WORKSPACE"
    ISOLATED = "ISOLATED"


class NetworkMode(StrEnum):
    """Network isolation modes."""

    DISABLED = "DISABLED"
    RESTRICTED = "RESTRICTED"
    ENABLED = "ENABLED"


class EnvironmentMode(StrEnum):
    """Environment-variable exposure modes."""

    EMPTY = "EMPTY"
    ALLOWLIST = "ALLOWLIST"
    INHERITED = "INHERITED"


class IsolationLevel(StrEnum):
    """Strength of the requested execution isolation."""

    MINIMAL = "MINIMAL"
    STANDARD = "STANDARD"
    STRICT = "STRICT"


class SandboxPath(BaseModel):
    """A path exposed inside a sandbox."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    path: str = Field(
        min_length=1,
        max_length=1000,
    )
    read_only: bool = True

    @field_validator("path")
    @classmethod
    def normalize_path(cls, value: str) -> str:
        """Normalize a sandbox path representation."""
        normalized = value.strip()

        if not normalized:
            raise ValueError("sandbox path must not be empty")

        if not normalized.startswith("/"):
            raise ValueError("sandbox path must be absolute")

        return normalized


class SandboxConfig(BaseModel):
    """Immutable description of one sandbox environment."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    execution_target: ExecutionTarget

    filesystem_mode: FilesystemMode = FilesystemMode.ISOLATED
    network_mode: NetworkMode = NetworkMode.DISABLED
    environment_mode: EnvironmentMode = EnvironmentMode.EMPTY
    isolation_level: IsolationLevel = IsolationLevel.STRICT

    writable_paths: tuple[SandboxPath, ...] = ()
    read_only_paths: tuple[SandboxPath, ...] = ()

    allowed_environment_keys: tuple[str, ...] = ()

    resource_limits: ResourceLimits

    allow_process_creation: bool = False
    allow_privileged_operations: bool = False

    @model_validator(mode="after")
    def validate_configuration(self) -> SandboxConfig:
        """Ensure sandbox configuration does not weaken isolation."""
        writable = {
            path.path
            for path in self.writable_paths
        }
        read_only = {
            path.path
            for path in self.read_only_paths
        }

        overlap = writable.intersection(read_only)

        if overlap:
            raise ValueError(
                "sandbox paths cannot be both writable and read-only: "
                + ", ".join(sorted(overlap))
            )

        if self.network_mode is NetworkMode.ENABLED:
            if self.isolation_level is IsolationLevel.STRICT:
                raise ValueError(
                    "STRICT isolation cannot use unrestricted network"
                )

        if self.environment_mode is EnvironmentMode.ALLOWLIST:
            if not self.allowed_environment_keys:
                raise ValueError(
                    "ALLOWLIST environment mode requires environment keys"
                )

        if self.environment_mode is not EnvironmentMode.ALLOWLIST:
            if self.allowed_environment_keys:
                raise ValueError(
                    "environment keys require ALLOWLIST mode"
                )

        if self.allow_privileged_operations:
            raise ValueError(
                "privileged operations are not permitted"
            )

        return self


class SandboxPolicy(BaseModel):
    """Immutable platform policy defining the sandbox ceiling."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    allowed_targets: frozenset[ExecutionTarget] = frozenset(
        {
            ExecutionTarget.LOCAL_CPU,
            ExecutionTarget.REMOTE_SANDBOX,
        }
    )

    max_isolation_level: IsolationLevel = IsolationLevel.STRICT

    allowed_filesystem_modes: frozenset[FilesystemMode] = frozenset(
        {
            FilesystemMode.READ_ONLY,
            FilesystemMode.WORKSPACE,
            FilesystemMode.ISOLATED,
        }
    )

    allowed_network_modes: frozenset[NetworkMode] = frozenset(
        {
            NetworkMode.DISABLED,
            NetworkMode.RESTRICTED,
        }
    )

    allowed_environment_modes: frozenset[EnvironmentMode] = frozenset(
        {
            EnvironmentMode.EMPTY,
            EnvironmentMode.ALLOWLIST,
        }
    )

    allow_process_creation: bool = False
    allow_privileged_operations: bool = False


class SandboxPolicyEvaluator:
    """Evaluate sandbox configurations against platform policy."""

    _isolation_order: dict[IsolationLevel, int] = {
        IsolationLevel.MINIMAL: 0,
        IsolationLevel.STANDARD: 1,
        IsolationLevel.STRICT: 2,
    }

    def failure_reasons(
        self,
        config: SandboxConfig,
        policy: SandboxPolicy,
    ) -> tuple[str, ...]:
        """Return deterministic sandbox policy violations."""
        reasons: list[str] = []

        if config.execution_target not in policy.allowed_targets:
            reasons.append("SANDBOX_TARGET_NOT_PERMITTED")

        if config.filesystem_mode not in policy.allowed_filesystem_modes:
            reasons.append("SANDBOX_FILESYSTEM_MODE_NOT_PERMITTED")

        if config.network_mode not in policy.allowed_network_modes:
            reasons.append("SANDBOX_NETWORK_MODE_NOT_PERMITTED")

        if (
            config.environment_mode
            not in policy.allowed_environment_modes
        ):
            reasons.append("SANDBOX_ENVIRONMENT_MODE_NOT_PERMITTED")

        if self._isolation_order[config.isolation_level] > (
            self._isolation_order[policy.max_isolation_level]
        ):
            reasons.append("SANDBOX_ISOLATION_LEVEL_INVALID")

        if (
            config.allow_process_creation
            and not policy.allow_process_creation
        ):
            reasons.append("PROCESS_CREATION_NOT_PERMITTED")

        if (
            config.allow_privileged_operations
            and not policy.allow_privileged_operations
        ):
            reasons.append("PRIVILEGED_OPERATIONS_NOT_PERMITTED")

        return tuple(dict.fromkeys(reasons))

    def is_allowed(
        self,
        config: SandboxConfig,
        policy: SandboxPolicy,
    ) -> bool:
        """Return whether a sandbox configuration is permitted."""
        return not self.failure_reasons(
            config,
            policy,
        )

    def require_allowed(
        self,
        config: SandboxConfig,
        policy: SandboxPolicy,
    ) -> None:
        """Raise when a sandbox configuration exceeds policy."""
        reasons = self.failure_reasons(
            config,
            policy,
        )

        if reasons:
            raise PermissionError(
                "sandbox policy rejected configuration: "
                + ", ".join(reasons)
            )


def default_sandbox_policy() -> SandboxPolicy:
    """Return the conservative default sandbox policy."""
    return SandboxPolicy()
