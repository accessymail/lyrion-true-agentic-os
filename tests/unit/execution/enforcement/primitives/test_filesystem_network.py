"""Unit tests for filesystem and network isolation adapters."""

from __future__ import annotations

from datetime import UTC, datetime

from lyrion.execution.backends.linux.enforcement.application import (
    EnforcementApplicationContext,
)
from lyrion.execution.backends.linux.enforcement.contracts import (
    EnforcementPrimitive,
    EnforcementState,
)
from lyrion.execution.backends.linux.enforcement.planner import (
    LinuxEnforcementPlanner,
)
from lyrion.execution.backends.linux.enforcement.primitives.filesystem_network import (
    FilesystemIsolationAdapter,
    FilesystemIsolationState,
    NetworkIsolationAdapter,
    NetworkIsolationState,
)
from lyrion.execution.sandbox import (
    ExecutionTarget,
    FilesystemMode,
    IsolationLevel,
    NetworkMode,
    ResourceLimits,
    SandboxConfig,
    SandboxPath,
)


class FakeFilesystemOperations:
    """Deterministic filesystem operation boundary."""

    def __init__(
        self,
        *,
        mode: FilesystemMode = FilesystemMode.ISOLATED,
        writable_paths: tuple[str, ...] = (),
        read_only_paths: tuple[str, ...] = (),
    ) -> None:
        self.state = FilesystemIsolationState(
            mode=mode,
            writable_paths=writable_paths,
            read_only_paths=read_only_paths,
        )
        self.prepare_calls = 0
        self.mode_calls: list[FilesystemMode] = []
        self.writable_calls: list[tuple[str, ...]] = []
        self.read_only_calls: list[tuple[str, ...]] = []

    def prepare_mount_namespace(self) -> None:
        self.prepare_calls += 1

    def apply_filesystem_mode(self, mode: FilesystemMode) -> None:
        self.mode_calls.append(mode)
        self.state = FilesystemIsolationState(
            mode=mode,
            writable_paths=self.state.writable_paths,
            read_only_paths=self.state.read_only_paths,
        )

    def apply_writable_paths(self, paths: tuple[str, ...]) -> None:
        self.writable_calls.append(paths)
        self.state = FilesystemIsolationState(
            mode=self.state.mode,
            writable_paths=paths,
            read_only_paths=self.state.read_only_paths,
        )

    def apply_read_only_paths(self, paths: tuple[str, ...]) -> None:
        self.read_only_calls.append(paths)
        self.state = FilesystemIsolationState(
            mode=self.state.mode,
            writable_paths=self.state.writable_paths,
            read_only_paths=paths,
        )

    def get_filesystem_state(self) -> FilesystemIsolationState:
        return self.state


class FakeNetworkOperations:
    """Deterministic network operation boundary."""

    def __init__(
        self,
        *,
        mode: NetworkMode = NetworkMode.DISABLED,
        network_access_allowed: bool = False,
    ) -> None:
        self.state = NetworkIsolationState(
            mode=mode,
            network_access_allowed=network_access_allowed,
        )
        self.prepare_calls = 0
        self.apply_calls: list[tuple[NetworkMode, bool]] = []

    def prepare_network_namespace(self) -> None:
        self.prepare_calls += 1

    def apply_network_mode(
        self,
        mode: NetworkMode,
        network_access_allowed: bool,
    ) -> None:
        self.apply_calls.append((mode, network_access_allowed))
        self.state = NetworkIsolationState(
            mode=mode,
            network_access_allowed=network_access_allowed,
        )

    def get_network_state(self) -> NetworkIsolationState:
        return self.state


def _context() -> EnforcementApplicationContext:
    return EnforcementApplicationContext.create(
        execution_id="test-filesystem-network",
        backend_id="linux-native",
        started_at=datetime.now(UTC),
    )


def _sandbox(
    *,
    filesystem_mode: FilesystemMode = FilesystemMode.ISOLATED,
    network_mode: NetworkMode = NetworkMode.DISABLED,
    writable_paths: tuple[SandboxPath, ...] = (),
    read_only_paths: tuple[SandboxPath, ...] = (),
) -> SandboxConfig:
    return SandboxConfig(
        execution_target=ExecutionTarget.LOCAL_CPU,
        isolation_level=IsolationLevel.STRICT,
        filesystem_mode=filesystem_mode,
        network_mode=network_mode,
        writable_paths=writable_paths,
        read_only_paths=read_only_paths,
        resource_limits=ResourceLimits(
            max_runtime_seconds=30.0,
            max_memory_mb=256,
            max_output_bytes=65536,
            max_cpu_seconds=30.0,
        ),
    )


def _plan(
    *,
    filesystem_mode: FilesystemMode = FilesystemMode.ISOLATED,
    network_mode: NetworkMode = NetworkMode.DISABLED,
    writable_paths: tuple[SandboxPath, ...] = (),
    read_only_paths: tuple[SandboxPath, ...] = (),
):
    return LinuxEnforcementPlanner().plan(
        _sandbox(
            filesystem_mode=filesystem_mode,
            network_mode=network_mode,
            writable_paths=writable_paths,
            read_only_paths=read_only_paths,
        )
    )


def test_filesystem_validate_accepts_authoritative_requirement() -> None:
    adapter = FilesystemIsolationAdapter(FakeFilesystemOperations())

    result = adapter.validate(_plan())

    assert result.primitive is EnforcementPrimitive.FILESYSTEM
    assert result.required is True
    assert result.success is True
    assert result.state is EnforcementState.SUPPORTED


def test_filesystem_apply_configures_mode_and_paths() -> None:
    operations = FakeFilesystemOperations()
    adapter = FilesystemIsolationAdapter(operations)

    plan = _plan(
        writable_paths=(SandboxPath(path="/workspace"),),
        read_only_paths=(SandboxPath(path="/usr"),),
    )

    result = adapter.apply(_context(), plan)

    assert result.state is EnforcementState.APPLIED
    assert result.success is True
    assert operations.prepare_calls == 1
    assert operations.mode_calls == [FilesystemMode.ISOLATED]
    assert operations.writable_calls == [("/workspace",)]
    assert operations.read_only_calls == [("/usr",)]


def test_filesystem_verify_independently_confirms_state() -> None:
    operations = FakeFilesystemOperations(
        mode=FilesystemMode.ISOLATED,
        writable_paths=("/workspace",),
        read_only_paths=("/usr",),
    )
    adapter = FilesystemIsolationAdapter(operations)

    plan = _plan(
        writable_paths=(SandboxPath(path="/workspace"),),
        read_only_paths=(SandboxPath(path="/usr"),),
    )

    result = adapter.verify(_context(), plan)

    assert result.state is EnforcementState.VERIFIED
    assert result.success is True
    assert len(result.evidence) == 1
    assert result.evidence[0].evidence_type == "filesystem_state"


def test_filesystem_verify_fails_for_wrong_mode() -> None:
    operations = FakeFilesystemOperations(mode=FilesystemMode.READ_ONLY)
    adapter = FilesystemIsolationAdapter(operations)

    result = adapter.verify(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "filesystem mode" in result.reason


def test_filesystem_verify_fails_for_wrong_paths() -> None:
    operations = FakeFilesystemOperations(
        writable_paths=("/wrong",),
    )
    adapter = FilesystemIsolationAdapter(operations)

    plan = _plan(
        writable_paths=(SandboxPath(path="/workspace"),),
    )

    result = adapter.verify(_context(), plan)

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "writable filesystem paths" in result.reason


def test_filesystem_apply_fails_closed_on_operation_error() -> None:
    class FailingOperations(FakeFilesystemOperations):
        def prepare_mount_namespace(self) -> None:
            raise OSError("mount namespace unavailable")

    adapter = FilesystemIsolationAdapter(FailingOperations())

    result = adapter.apply(_context(), _plan())

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "mount namespace unavailable" in result.reason


def test_network_validate_accepts_disabled_mode() -> None:
    adapter = NetworkIsolationAdapter(FakeNetworkOperations())

    result = adapter.validate(_plan(network_mode=NetworkMode.DISABLED))

    assert result.primitive is EnforcementPrimitive.NETWORK
    assert result.required is True
    assert result.success is True
    assert result.state is EnforcementState.SUPPORTED


def test_network_apply_configures_disabled_network() -> None:
    operations = FakeNetworkOperations()
    adapter = NetworkIsolationAdapter(operations)

    result = adapter.apply(
        _context(),
        _plan(network_mode=NetworkMode.DISABLED),
    )

    assert result.state is EnforcementState.APPLIED
    assert result.success is True
    assert operations.prepare_calls == 1
    assert operations.apply_calls == [
        (NetworkMode.DISABLED, False)
    ]


def test_network_verify_independently_confirms_disabled_network() -> None:
    operations = FakeNetworkOperations(
        mode=NetworkMode.DISABLED,
        network_access_allowed=False,
    )
    adapter = NetworkIsolationAdapter(operations)

    result = adapter.verify(
        _context(),
        _plan(network_mode=NetworkMode.DISABLED),
    )

    assert result.state is EnforcementState.VERIFIED
    assert result.success is True
    assert len(result.evidence) == 1
    assert result.evidence[0].evidence_type == "network_state"


def test_network_verify_fails_when_access_policy_is_wrong() -> None:
    operations = FakeNetworkOperations(
        mode=NetworkMode.DISABLED,
        network_access_allowed=True,
    )
    adapter = NetworkIsolationAdapter(operations)

    result = adapter.verify(
        _context(),
        _plan(network_mode=NetworkMode.DISABLED),
    )

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "network access policy" in result.reason


def test_network_apply_fails_closed_on_operation_error() -> None:
    class FailingOperations(FakeNetworkOperations):
        def apply_network_mode(
            self,
            mode: NetworkMode,
            network_access_allowed: bool,
        ) -> None:
            del mode, network_access_allowed
            raise OSError("network isolation unavailable")

    adapter = NetworkIsolationAdapter(FailingOperations())

    result = adapter.apply(
        _context(),
        _plan(network_mode=NetworkMode.DISABLED),
    )

    assert result.state is EnforcementState.FAILED
    assert result.success is False
    assert "network isolation unavailable" in result.reason


def test_filesystem_evidence_returns_tuple() -> None:
    operations = FakeFilesystemOperations()
    adapter = FilesystemIsolationAdapter(operations)

    evidence = adapter.evidence(_context(), _plan())

    assert isinstance(evidence, tuple)
    assert len(evidence) == 1
    assert evidence[0].primitive is EnforcementPrimitive.FILESYSTEM
    assert evidence[0].observed_state is EnforcementState.VERIFIED


def test_network_evidence_returns_tuple() -> None:
    operations = FakeNetworkOperations()
    adapter = NetworkIsolationAdapter(operations)

    evidence = adapter.evidence(
        _context(),
        _plan(network_mode=NetworkMode.DISABLED),
    )

    assert isinstance(evidence, tuple)
    assert len(evidence) == 1
    assert evidence[0].primitive is EnforcementPrimitive.NETWORK
    assert evidence[0].observed_state is EnforcementState.VERIFIED


def test_native_operations_are_not_used_by_unit_tests() -> None:
    filesystem = FilesystemIsolationAdapter(FakeFilesystemOperations())
    network = NetworkIsolationAdapter(FakeNetworkOperations())

    filesystem_result = filesystem.verify(_context(), _plan())
    network_result = network.verify(
        _context(),
        _plan(network_mode=NetworkMode.DISABLED),
    )

    assert filesystem_result.state is EnforcementState.VERIFIED
    assert network_result.state is EnforcementState.VERIFIED
