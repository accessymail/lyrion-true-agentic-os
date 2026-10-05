"""Security and contract tests for the OS_STATE_READONLY adapter."""

from datetime import UTC, datetime, timedelta

import pytest

from lyrion.execution.backends.linux.host.contracts import (
    LinuxHostAbstractionSnapshot,
    LinuxHostFingerprint,
    LinuxHostIdentity,
)
from lyrion.execution.lhicf import (
    BoundaryStatus,
    LHICFRequest,
)
from lyrion.execution.lhicf.adapters import OSStateReadonlyAdapter

_DEFAULT_ADMISSION = object()


def request(
    *,
    admission=_DEFAULT_ADMISSION,
    adapter_id="os-state",
    operation="READ_STATE",
    scope="HOST",
    expires_delta=timedelta(minutes=5),
    requested_offset=timedelta(0),
) -> LHICFRequest:
    if admission is _DEFAULT_ADMISSION:
        admission = object()

    requested_at = datetime.now(UTC) + requested_offset

    return LHICFRequest(
        request_id="req-os-state-1",
        execution_admission=admission,
        sandbox_context=object(),
        adapter_id=adapter_id,
        operation=operation,
        target_scope=scope,
        correlation_id="corr-os-state-1",
        provenance_context="prov-os-state-1",
        requested_at=requested_at,
        expires_at=requested_at + expires_delta,
    )


def fake_snapshot() -> LinuxHostAbstractionSnapshot:
    identity = LinuxHostIdentity(
        os_name="Ubuntu",
        os_version="24.04",
        kernel="6.8.0-test",
        architecture="x86_64",
        virtualization=None,
        init_system="systemd",
    )

    fingerprint = LinuxHostFingerprint(
        identity=identity,
        primitives=(),
    )

    return LinuxHostAbstractionSnapshot(
        identity=identity,
        fingerprint=fingerprint,
        user_id=1000,
        effective_capabilities=(),
        namespaces=(),
        notes=(),
    )


class FakeDiscovery:
    def __init__(self, snapshot=None, error=None):
        self.snapshot = snapshot or fake_snapshot()
        self.error = error
        self.calls = 0

    def discover(self):
        self.calls += 1

        if self.error is not None:
            raise self.error

        return self.snapshot


def test_registration_is_strictly_read_only():
    registration = OSStateReadonlyAdapter.registration()

    assert registration.adapter_id == "os-state"
    assert registration.supported_operations == frozenset({"READ_STATE"})
    assert registration.supported_target_scopes == frozenset({"HOST"})
    assert registration.security_classification == "READ_ONLY_HOST_STATE"


def test_observation_returns_normalized_host_state():
    discovery = FakeDiscovery()
    adapter = OSStateReadonlyAdapter(discovery=discovery)

    result = adapter.observe(request())

    assert result.boundary_status is BoundaryStatus.ACCEPTED
    assert result.adapter_id == "os-state"
    assert result.operation == "READ_STATE"
    assert result.provenance_reference == "prov-os-state-1"
    assert result.audit_reference == "lhicf-os-state:corr-os-state-1"
    assert result.host_identity_reference.startswith("sha256:")
    assert result.capability_observation_reference.startswith("sha256:")
    assert result.normalized_result["identity"]["os_name"] == "Ubuntu"
    assert discovery.calls == 1


def test_missing_admission_fails_closed():
    discovery = FakeDiscovery()
    adapter = OSStateReadonlyAdapter(discovery=discovery)

    result = adapter.observe(request(admission=None))

    assert result.boundary_status is BoundaryStatus.BLOCKED
    assert discovery.calls == 0


def test_wrong_adapter_identity_fails_closed():
    discovery = FakeDiscovery()
    adapter = OSStateReadonlyAdapter(discovery=discovery)

    result = adapter.observe(
        request(adapter_id="malicious-host-adapter")
    )

    assert result.boundary_status is BoundaryStatus.BLOCKED
    assert discovery.calls == 0


def test_wrong_operation_fails_closed():
    discovery = FakeDiscovery()
    adapter = OSStateReadonlyAdapter(discovery=discovery)

    result = adapter.observe(
        request(operation="DELETE")
    )

    assert result.boundary_status is BoundaryStatus.BLOCKED
    assert discovery.calls == 0


def test_wrong_target_scope_fails_closed():
    discovery = FakeDiscovery()
    adapter = OSStateReadonlyAdapter(discovery=discovery)

    result = adapter.observe(
        request(scope="FILESYSTEM")
    )

    assert result.boundary_status is BoundaryStatus.BLOCKED
    assert discovery.calls == 0


def test_expired_request_fails_closed():
    discovery = FakeDiscovery()
    adapter = OSStateReadonlyAdapter(discovery=discovery)

    result = adapter.observe(
        request(
            requested_offset=timedelta(minutes=-10),
            expires_delta=timedelta(minutes=1),
        )
    )

    assert result.boundary_status is BoundaryStatus.STALE
    assert discovery.calls == 0


def test_discovery_failure_does_not_become_allow():
    discovery = FakeDiscovery(
        error=RuntimeError("simulated discovery failure")
    )
    adapter = OSStateReadonlyAdapter(discovery=discovery)

    result = adapter.observe(request())

    assert result.boundary_status is BoundaryStatus.ADAPTER_ERROR
    assert result.normalized_result is None
    assert result.provenance_reference is None
    assert result.audit_reference is None


def test_reference_generation_is_deterministic():
    discovery = FakeDiscovery()
    adapter = OSStateReadonlyAdapter(discovery=discovery)

    first = adapter.observe(request())
    second = adapter.observe(request())

    assert first.host_identity_reference == second.host_identity_reference
    assert (
        first.capability_observation_reference
        == second.capability_observation_reference
    )


def test_adapter_does_not_create_authority():
    discovery = FakeDiscovery()
    adapter = OSStateReadonlyAdapter(discovery=discovery)

    result = adapter.observe(request())

    assert not hasattr(result, "authorization_decision")
    assert not hasattr(result, "granted_capabilities")
    assert not hasattr(result, "capability_grant")


def test_discovery_is_the_only_execution_dependency():
    discovery = FakeDiscovery()
    adapter = OSStateReadonlyAdapter(discovery=discovery)

    result = adapter.observe(request())

    assert result.boundary_status is BoundaryStatus.ACCEPTED
    assert discovery.calls == 1


def test_registration_is_immutable():
    registration = OSStateReadonlyAdapter.registration()

    with pytest.raises(AttributeError):
        registration.adapter_id = "malicious"


def test_result_is_immutable():
    discovery = FakeDiscovery()
    adapter = OSStateReadonlyAdapter(discovery=discovery)

    result = adapter.observe(request())

    with pytest.raises(AttributeError):
        result.operation = "DELETE"
