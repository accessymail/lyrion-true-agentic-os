"""Adversarial tests for the sandbox boundary."""

import pytest
from pydantic import ValidationError

from lyrion.core.types import ExecutionTarget
from lyrion.execution.contracts import ResourceLimits
from lyrion.execution.sandbox import (
    EnvironmentMode,
    FilesystemMode,
    IsolationLevel,
    NetworkMode,
    SandboxConfig,
    SandboxPath,
    SandboxPolicy,
    SandboxPolicyEvaluator,
    default_sandbox_policy,
)


def make_limits(**overrides: object) -> ResourceLimits:
    """Create baseline resource limits."""
    values: dict[str, object] = {
        "max_runtime_seconds": 30.0,
        "max_memory_mb": 512,
        "max_output_bytes": 1_048_576,
        "max_cpu_seconds": 30.0,
    }

    values.update(overrides)

    return ResourceLimits(**values)


def make_config(**overrides: object) -> SandboxConfig:
    """Create a valid baseline sandbox configuration."""
    values: dict[str, object] = {
        "execution_target": ExecutionTarget.REMOTE_SANDBOX,
        "filesystem_mode": FilesystemMode.ISOLATED,
        "network_mode": NetworkMode.DISABLED,
        "environment_mode": EnvironmentMode.EMPTY,
        "isolation_level": IsolationLevel.STRICT,
        "writable_paths": (),
        "read_only_paths": (),
        "allowed_environment_keys": (),
        "resource_limits": make_limits(),
        "allow_process_creation": False,
        "allow_privileged_operations": False,
    }

    values.update(overrides)

    return SandboxConfig(**values)


def test_default_sandbox_policy_is_conservative() -> None:
    """The default sandbox policy must remain restrictive."""
    policy = default_sandbox_policy()

    assert ExecutionTarget.REMOTE_SANDBOX in policy.allowed_targets
    assert ExecutionTarget.CLOUD_GPU not in policy.allowed_targets
    assert NetworkMode.ENABLED not in policy.allowed_network_modes
    assert EnvironmentMode.INHERITED not in (
        policy.allowed_environment_modes
    )
    assert policy.allow_process_creation is False
    assert policy.allow_privileged_operations is False


def test_sandbox_path_requires_absolute_path() -> None:
    """Sandbox paths must be absolute."""
    with pytest.raises(ValidationError):
        SandboxPath(path="relative/path")


def test_sandbox_path_normalizes_whitespace() -> None:
    """Sandbox path surrounding whitespace should be removed."""
    path = SandboxPath(
        path="  /workspace  ",
    )

    assert path.path == "/workspace"


def test_sandbox_path_is_immutable() -> None:
    """Sandbox paths must be immutable."""
    path = SandboxPath(
        path="/workspace",
    )

    with pytest.raises(ValidationError):
        path.path = "/changed"


def test_valid_sandbox_configuration_is_accepted() -> None:
    """A conservative sandbox configuration should be accepted."""
    config = make_config()

    assert config.execution_target is ExecutionTarget.REMOTE_SANDBOX
    assert config.filesystem_mode is FilesystemMode.ISOLATED
    assert config.network_mode is NetworkMode.DISABLED
    assert config.isolation_level is IsolationLevel.STRICT


def test_sandbox_configuration_is_immutable() -> None:
    """Sandbox configurations must be immutable."""
    config = make_config()

    with pytest.raises(ValidationError):
        config.network_mode = NetworkMode.ENABLED


def test_overlapping_paths_are_rejected() -> None:
    """A path cannot simultaneously be writable and read-only."""
    with pytest.raises(ValidationError):
        make_config(
            writable_paths=(
                SandboxPath(path="/workspace"),
            ),
            read_only_paths=(
                SandboxPath(path="/workspace"),
            ),
        )


def test_allowlist_environment_requires_keys() -> None:
    """ALLOWLIST mode must contain explicit environment keys."""
    with pytest.raises(ValidationError):
        make_config(
            environment_mode=EnvironmentMode.ALLOWLIST,
            allowed_environment_keys=(),
        )


def test_environment_keys_require_allowlist_mode() -> None:
    """Environment keys must not be supplied in EMPTY mode."""
    with pytest.raises(ValidationError):
        make_config(
            environment_mode=EnvironmentMode.EMPTY,
            allowed_environment_keys=("PATH",),
        )


def test_strict_isolation_rejects_enabled_network() -> None:
    """Strict isolation cannot allow unrestricted networking."""
    with pytest.raises(ValidationError):
        make_config(
            isolation_level=IsolationLevel.STRICT,
            network_mode=NetworkMode.ENABLED,
        )


def test_privileged_operations_are_rejected() -> None:
    """Privileged operations must remain unavailable."""
    with pytest.raises(ValidationError):
        make_config(
            allow_privileged_operations=True,
        )


def test_default_configuration_is_allowed() -> None:
    """The baseline sandbox configuration should satisfy policy."""
    config = make_config()
    policy = default_sandbox_policy()

    assert SandboxPolicyEvaluator().is_allowed(
        config,
        policy,
    )


def test_cloud_gpu_target_is_denied() -> None:
    """Unapproved execution targets must fail closed."""
    config = make_config(
        execution_target=ExecutionTarget.CLOUD_GPU,
    )

    reasons = SandboxPolicyEvaluator().failure_reasons(
        config,
        default_sandbox_policy(),
    )

    assert "SANDBOX_TARGET_NOT_PERMITTED" in reasons


def test_network_enabled_is_denied_by_default() -> None:
    """Default policy must deny unrestricted network access."""
    config = make_config(
        isolation_level=IsolationLevel.STANDARD,
        network_mode=NetworkMode.ENABLED,
    )

    reasons = SandboxPolicyEvaluator().failure_reasons(
        config,
        default_sandbox_policy(),
    )

    assert "SANDBOX_NETWORK_MODE_NOT_PERMITTED" in reasons


def test_restricted_network_can_be_permitted_by_policy() -> None:
    """Restricted networking may be enabled explicitly."""
    config = make_config(
        isolation_level=IsolationLevel.STANDARD,
        network_mode=NetworkMode.RESTRICTED,
    )

    assert SandboxPolicyEvaluator().is_allowed(
        config,
        default_sandbox_policy(),
    )


def test_inherited_environment_is_denied() -> None:
    """Inherited environment access must fail closed."""
    config = make_config(
        environment_mode=EnvironmentMode.INHERITED,
    )

    reasons = SandboxPolicyEvaluator().failure_reasons(
        config,
        default_sandbox_policy(),
    )

    assert "SANDBOX_ENVIRONMENT_MODE_NOT_PERMITTED" in reasons


def test_allowlisted_environment_can_be_represented() -> None:
    """Explicit environment allowlists should be supported."""
    config = make_config(
        environment_mode=EnvironmentMode.ALLOWLIST,
        allowed_environment_keys=("PATH",),
    )

    assert SandboxPolicyEvaluator().is_allowed(
        config,
        default_sandbox_policy(),
    )


def test_process_creation_is_denied_by_default() -> None:
    """Process creation must remain disabled."""
    config = make_config(
        allow_process_creation=True,
    )

    reasons = SandboxPolicyEvaluator().failure_reasons(
        config,
        default_sandbox_policy(),
    )

    assert "PROCESS_CREATION_NOT_PERMITTED" in reasons


def test_policy_can_explicitly_allow_process_creation() -> None:
    """A future execution policy may explicitly permit process creation."""
    config = make_config(
        allow_process_creation=True,
    )

    policy = SandboxPolicy(
        allow_process_creation=True,
    )

    assert SandboxPolicyEvaluator().is_allowed(
        config,
        policy,
    )


def test_filesystem_mode_is_policy_controlled() -> None:
    """Filesystem isolation must be controlled by platform policy."""
    config = make_config(
        filesystem_mode=FilesystemMode.NONE,
    )

    policy = SandboxPolicy(
        allowed_filesystem_modes=frozenset(
            {
                FilesystemMode.NONE,
            }
        )
    )

    assert SandboxPolicyEvaluator().is_allowed(
        config,
        policy,
    )


def test_non_permitted_filesystem_mode_is_rejected() -> None:
    """A filesystem mode outside policy must be denied."""
    config = make_config(
        filesystem_mode=FilesystemMode.NONE,
    )

    reasons = SandboxPolicyEvaluator().failure_reasons(
        config,
        default_sandbox_policy(),
    )

    assert "SANDBOX_FILESYSTEM_MODE_NOT_PERMITTED" in reasons


def test_failure_reasons_are_deterministic() -> None:
    """Equivalent sandbox inputs should produce identical violations."""
    config = make_config(
        execution_target=ExecutionTarget.CLOUD_GPU,
        network_mode=NetworkMode.ENABLED,
        environment_mode=EnvironmentMode.INHERITED,
        isolation_level=IsolationLevel.STANDARD,
        allow_process_creation=True,
    )

    evaluator = SandboxPolicyEvaluator()
    policy = default_sandbox_policy()

    first = evaluator.failure_reasons(
        config,
        policy,
    )
    second = evaluator.failure_reasons(
        config,
        policy,
    )

    assert first == second


def test_require_allowed_fails_closed() -> None:
    """Sandbox policy violations must raise PermissionError."""
    config = make_config(
        execution_target=ExecutionTarget.CLOUD_GPU,
    )

    with pytest.raises(
        PermissionError,
        match="sandbox policy rejected",
    ):
        SandboxPolicyEvaluator().require_allowed(
            config,
            default_sandbox_policy(),
        )


def test_policy_does_not_modify_configuration() -> None:
    """Policy evaluation must not mutate the sandbox configuration."""
    config = make_config()
    policy = default_sandbox_policy()

    before = config.model_dump(mode="json")

    SandboxPolicyEvaluator().is_allowed(
        config,
        policy,
    )

    assert config.model_dump(mode="json") == before


def test_sandbox_policy_is_immutable() -> None:
    """Sandbox policies must be immutable."""
    policy = SandboxPolicy()

    with pytest.raises(ValidationError):
        policy.allow_process_creation = True


def test_empty_filesystem_mode_has_no_implicit_write_access() -> None:
    """NONE filesystem mode should contain no writable paths."""
    config = make_config(
        filesystem_mode=FilesystemMode.NONE,
        writable_paths=(),
        read_only_paths=(),
    )

    assert config.writable_paths == ()
    assert config.read_only_paths == ()
