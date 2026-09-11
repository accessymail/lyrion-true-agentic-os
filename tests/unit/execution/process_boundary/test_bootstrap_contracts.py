from __future__ import annotations

from pathlib import Path

import pytest

from lyrion.core.types import ExecutionTarget
from lyrion.execution.backends.linux.enforcement.contracts import (
    EnforcementPlanStatus,
    LinuxEnforcementPlan,
)
from lyrion.execution.backends.linux.enforcement.planner import (
    LinuxEnforcementPlanner,
)
from lyrion.execution.contracts import ResourceLimits
from lyrion.execution.process_boundary.bootstrap_contracts import (
    BootstrapContractError,
    BootstrapState,
    BootstrapStateMachine,
    LaunchHandoff,
)
from lyrion.execution.process_boundary.supervisor import ProcessLaunchSpec
from lyrion.execution.sandbox import (
    FilesystemMode,
    NetworkMode,
    SandboxConfig,
)


def _plan() -> LinuxEnforcementPlan:
    return LinuxEnforcementPlanner().plan(
        SandboxConfig(
            execution_target=ExecutionTarget.LOCAL_CPU,
            filesystem_mode=FilesystemMode.NONE,
            network_mode=NetworkMode.DISABLED,
            resource_limits=ResourceLimits(
                max_runtime_seconds=30.0,
                max_memory_mb=256,
                max_output_bytes=65536,
                max_cpu_seconds=30.0,
            ),
        )
    )


def _handoff(tmp_path: Path) -> LaunchHandoff:
    launch = ProcessLaunchSpec(
        execution_id="exec-001",
        argv=("python3", "-c", "print('ok')"),
        cwd=tmp_path,
        environment={"PATH": "/usr/bin"},
        timeout_seconds=10.0,
        max_output_bytes=4096,
    )

    return LaunchHandoff.from_components(
        execution_id="exec-001",
        request_id="req-001",
        backend_id="linux-native",
        policy_version="policy-v1",
        authorization_reference="auth-001",
        launch_spec=launch,
        enforcement_plan=_plan(),
    )


def test_handoff_is_integrity_bound(tmp_path: Path) -> None:
    handoff = _handoff(tmp_path)

    assert len(handoff.integrity_sha256) == 64
    assert (
        handoff.compute_integrity_sha256()
        == handoff.integrity_sha256
    )


def test_handoff_rejects_tampered_digest(tmp_path: Path) -> None:
    handoff = _handoff(tmp_path)

    tampered = handoff.model_copy(
        update={"integrity_sha256": "0" * 64}
    )

    with pytest.raises(BootstrapContractError):
        tampered.verify_integrity()


def test_state_machine_requires_order() -> None:
    machine = BootstrapStateMachine("exec-001")

    with pytest.raises(BootstrapContractError):
        machine.transition(
            BootstrapState.HANDOFF_VALIDATED,
        )


def test_state_machine_allows_valid_transition() -> None:
    machine = BootstrapStateMachine("exec-001")

    machine.transition(BootstrapState.IDENTITY_BOUND)
    machine.transition(BootstrapState.HANDOFF_VALIDATED)

    assert machine.state is BootstrapState.HANDOFF_VALIDATED


def test_failed_state_is_terminal() -> None:
    machine = BootstrapStateMachine("exec-001")

    machine.transition(BootstrapState.FAILED)

    with pytest.raises(BootstrapContractError):
        machine.transition(BootstrapState.IDENTITY_BOUND)


def test_plan_remains_planning_only() -> None:
    plan = _plan()

    assert plan.status is EnforcementPlanStatus.READY
    plan.assert_planning_only()


@pytest.mark.parametrize(
    "target",
    [
        BootstrapState.HANDOFF_VALIDATED,
        BootstrapState.RESOURCES_PREPARED,
        BootstrapState.ENFORCEMENT_VERIFIED,
        BootstrapState.EXEC_READY,
    ],
)
def test_state_machine_rejects_forward_state_skipping(
    target: BootstrapState,
) -> None:
    machine = BootstrapStateMachine("exec-adversarial")

    with pytest.raises(BootstrapContractError):
        machine.transition(target)

    assert machine.state is BootstrapState.CREATED


def test_state_machine_rejects_backward_transition() -> None:
    machine = BootstrapStateMachine("exec-adversarial")

    machine.transition(BootstrapState.IDENTITY_BOUND)
    machine.transition(BootstrapState.HANDOFF_VALIDATED)

    with pytest.raises(BootstrapContractError):
        machine.transition(BootstrapState.IDENTITY_BOUND)

    assert machine.state is BootstrapState.HANDOFF_VALIDATED


def test_state_machine_rejects_exec_started_before_exec_ready() -> None:
    machine = BootstrapStateMachine("exec-adversarial")

    with pytest.raises(BootstrapContractError):
        machine.transition(BootstrapState.EXEC_STARTED)

    assert machine.state is BootstrapState.CREATED


def test_failed_bootstrap_cannot_be_resurrected() -> None:
    machine = BootstrapStateMachine("exec-adversarial")

    machine.transition(BootstrapState.FAILED)

    with pytest.raises(BootstrapContractError):
        machine.transition(BootstrapState.IDENTITY_BOUND)

    assert machine.state is BootstrapState.FAILED


def test_handoff_rejects_rejected_enforcement_plan(
    tmp_path: Path,
) -> None:
    sandbox = SandboxConfig(
        execution_target=ExecutionTarget.LOCAL_CPU,
        filesystem_mode=FilesystemMode.NONE,
        network_mode=NetworkMode.DISABLED,
        resource_limits=ResourceLimits(
            max_runtime_seconds=30.0,
            max_memory_mb=256,
            max_output_bytes=65536,
            max_cpu_seconds=30.0,
        ),
    )

    rejected = LinuxEnforcementPlan.rejected(
        sandbox,
        "adversarial rejection",
    )

    launch = ProcessLaunchSpec(
        execution_id="exec-001",
        argv=("python3", "-c", "print('ok')"),
        cwd=tmp_path,
        environment={"PATH": "/usr/bin"},
        timeout_seconds=10.0,
        max_output_bytes=4096,
    )

    with pytest.raises(BootstrapContractError):
        LaunchHandoff.from_components(
            execution_id="exec-001",
            request_id="req-001",
            backend_id="linux-native",
            policy_version="policy-v1",
            authorization_reference="auth-001",
            launch_spec=launch,
            enforcement_plan=rejected,
        )


def test_handoff_rejects_failed_requirement_payload(
    tmp_path: Path,
) -> None:
    handoff = _handoff(tmp_path)

    payload = dict(handoff.enforcement_plan)
    requirements = list(payload["requirements"])

    requirement = dict(requirements[0])
    requirement["state"] = "failed"
    requirements[0] = requirement
    payload["requirements"] = requirements

    with pytest.raises(ValueError):
        LaunchHandoff.model_validate(
            {
                **handoff.model_dump(),
                "enforcement_plan": tuple(
                    sorted(payload.items(), key=lambda item: item[0])
                ),
            }
        )


def test_handoff_rejects_applied_requirement_payload(
    tmp_path: Path,
) -> None:
    handoff = _handoff(tmp_path)

    payload = dict(handoff.enforcement_plan)
    requirements = list(payload["requirements"])

    requirement = dict(requirements[0])
    requirement["state"] = "applied"
    requirements[0] = requirement
    payload["requirements"] = requirements

    with pytest.raises(ValueError):
        LaunchHandoff.model_validate(
            {
                **handoff.model_dump(),
                "enforcement_plan": tuple(
                    sorted(payload.items(), key=lambda item: item[0])
                ),
            }
        )


def test_handoff_rejects_verified_requirement_payload(
    tmp_path: Path,
) -> None:
    handoff = _handoff(tmp_path)

    payload = dict(handoff.enforcement_plan)
    requirements = list(payload["requirements"])

    requirement = dict(requirements[0])
    requirement["state"] = "verified"
    requirements[0] = requirement
    payload["requirements"] = requirements

    with pytest.raises(ValueError):
        LaunchHandoff.model_validate(
            {
                **handoff.model_dump(),
                "enforcement_plan": tuple(
                    sorted(payload.items(), key=lambda item: item[0])
                ),
            }
        )


def test_handoff_requires_ready_plan_payload(
    tmp_path: Path,
) -> None:
    handoff = _handoff(tmp_path)

    payload = dict(handoff.enforcement_plan)
    payload["status"] = "rejected"

    with pytest.raises(ValueError):
        LaunchHandoff.model_validate(
            {
                **handoff.model_dump(),
                "enforcement_plan": tuple(
                    sorted(payload.items(), key=lambda item: item[0])
                ),
            }
        )
