"""Tests for the controlled real-process boundary."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from lyrion.execution.process_boundary import (
    ProcessBoundary,
    ProcessBoundaryError,
    ProcessLaunchRejected,
    ProcessLaunchSpec,
)


def make_spec(
    *,
    execution_id: str = "execution:test:001",
    argv: tuple[str, ...] | None = None,
    timeout_seconds: float = 2.0,
) -> ProcessLaunchSpec:
    return ProcessLaunchSpec(
        execution_id=execution_id,
        argv=argv
        or (
            sys.executable,
            "-c",
            "print('lyrion-process-boundary')",
        ),
        cwd=Path.cwd(),
        environment={"PATH": "/usr/bin:/bin"},
        timeout_seconds=timeout_seconds,
    )


def test_successful_process_has_real_pid_and_process_group() -> None:
    result = ProcessBoundary().run(make_spec())

    assert result.pid > 0
    assert result.pgid > 0
    assert result.pid != 0
    assert result.execution_id == "execution:test:001"
    assert result.exit_code == 0
    assert result.completed_successfully
    assert b"lyrion-process-boundary" in result.stdout


def test_output_is_bounded() -> None:
    result = ProcessBoundary().run(
        ProcessLaunchSpec(
            execution_id="execution:test:output-bound",
            argv=(
                sys.executable,
                "-c",
                "import sys; sys.stdout.write('x' * 10000); "
                "sys.stderr.write('y' * 10000)",
            ),
            cwd=Path.cwd(),
            environment={"PATH": "/usr/bin:/bin"},
            timeout_seconds=2.0,
            max_output_bytes=1024,
        )
    )

    assert len(result.stdout) <= 1024
    assert len(result.stderr) <= 1024


def test_shell_execution_is_not_used() -> None:
    result = ProcessBoundary().run(
        make_spec(
            argv=(
                sys.executable,
                "-c",
                "import os; print(os.environ.get('LYRION_TEST', 'missing'))",
            )
        )
    )

    assert result.exit_code == 0
    assert b"missing" in result.stdout


def test_environment_is_explicitly_controlled() -> None:
    result = ProcessBoundary().run(
        make_spec(
            argv=(
                sys.executable,
                "-c",
                "import os; print(os.environ.get('LYRION_BOUNDARY_ONLY', 'missing'))",
            )
        )
    )

    assert result.exit_code == 0
    assert b"missing" in result.stdout


def test_timeout_terminates_workload() -> None:
    result = ProcessBoundary(termination_grace_seconds=0.2).run(
        make_spec(
            timeout_seconds=0.2,
            argv=(
                sys.executable,
                "-c",
                "import time; time.sleep(30)",
            ),
        )
    )

    assert result.timed_out
    assert result.exit_code is not None
    assert not result.completed_successfully


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"execution_id": ""}, "execution_id"),
        ({"argv": ()}, "argv"),
        ({"timeout_seconds": 0}, "timeout_seconds"),
        ({"max_output_bytes": 0}, "max_output_bytes"),
    ],
)
def test_invalid_launch_spec_is_rejected(
    kwargs: dict[str, object],
    message: str,
) -> None:
    base = {
        "execution_id": "execution:test:invalid",
        "argv": (sys.executable, "-c", "pass"),
        "cwd": Path.cwd(),
        "environment": {"PATH": "/usr/bin:/bin"},
        "timeout_seconds": 2.0,
        "max_output_bytes": 1024,
    }
    base.update(kwargs)

    with pytest.raises(ProcessLaunchRejected, match=message):
        ProcessLaunchSpec(**base)  # type: ignore[arg-type]


def test_relative_working_directory_is_rejected() -> None:
    with pytest.raises(ProcessLaunchRejected, match="absolute"):
        make_spec().__class__(
            execution_id="execution:test:relative",
            argv=(sys.executable, "-c", "pass"),
            cwd=Path("."),
            environment={"PATH": "/usr/bin:/bin"},
            timeout_seconds=2.0,
        )


def test_missing_working_directory_is_rejected_at_launch(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    spec = ProcessLaunchSpec(
        execution_id="execution:test:missing-cwd",
        argv=(sys.executable, "-c", "pass"),
        cwd=missing,
        environment={"PATH": "/usr/bin:/bin"},
        timeout_seconds=2.0,
    )

    with pytest.raises(ProcessLaunchRejected, match="does not exist"):
        ProcessBoundary().run(spec)


@pytest.mark.parametrize(
    ("argv", "environment"),
    [
        (
            (sys.executable, "-c", "pass\x00"),
            {"PATH": "/usr/bin:/bin"},
        ),
        (
            (sys.executable, "-c", "pass"),
            {"BAD\x00KEY": "value"},
        ),
        (
            (sys.executable, "-c", "pass"),
            {"BAD": "value\x00"},
        ),
    ],
)
def test_nul_characters_are_rejected(
    argv: tuple[str, ...],
    environment: dict[str, str],
) -> None:
    with pytest.raises(ProcessLaunchRejected, match="NUL"):
        ProcessLaunchSpec(
            execution_id="execution:test:nul",
            argv=argv,
            cwd=Path.cwd(),
            environment=environment,
            timeout_seconds=2.0,
        )


def test_large_simultaneous_output_does_not_deadlock() -> None:
    result = ProcessBoundary().run(
        ProcessLaunchSpec(
            execution_id="execution:test:large-output",
            argv=(
                sys.executable,
                "-c",
                "import sys; "
                "sys.stdout.write('x' * 8_000_000); "
                "sys.stderr.write('y' * 8_000_000)",
            ),
            cwd=Path.cwd(),
            environment={"PATH": "/usr/bin:/bin"},
            timeout_seconds=5.0,
            max_output_bytes=4096,
        )
    )

    assert result.exit_code == 0
    assert len(result.stdout) == 4096
    assert len(result.stderr) == 4096


def test_nonzero_exit_is_preserved() -> None:
    result = ProcessBoundary().run(
        make_spec(
            argv=(
                sys.executable,
                "-c",
                "raise SystemExit(23)",
            )
        )
    )

    assert result.exit_code == 23
    assert not result.completed_successfully


def test_missing_executable_fails_closed(tmp_path: Path) -> None:
    spec = ProcessLaunchSpec(
        execution_id="execution:test:missing-executable",
        argv=(str(tmp_path / "does-not-exist"),),
        cwd=tmp_path,
        environment={"PATH": "/usr/bin:/bin"},
        timeout_seconds=2.0,
    )

    with pytest.raises(ProcessBoundaryError, match="launch failed"):
        ProcessBoundary().run(spec)


def test_timeout_escalates_when_workload_ignores_sigterm() -> None:
    result = ProcessBoundary(termination_grace_seconds=0.1).run(
        make_spec(
            timeout_seconds=0.1,
            argv=(
                sys.executable,
                "-c",
                "import signal, time; "
                "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                "time.sleep(30)",
            ),
        )
    )

    assert result.timed_out
    assert result.exit_code is not None
    assert not result.completed_successfully
